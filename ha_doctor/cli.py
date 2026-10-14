"""Command-line diagnostics (no writes to HA, no external packages)."""
import argparse
import getpass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from . import __version__
from .client import HAClient, DoctorConnectionError
from .demo import create_demo
from .diagnose import Snapshot, classify_error_log, diagnose
from .render import html_report, text_report


def parser():
    p = argparse.ArgumentParser(prog="ha-doctor", description="Safe, local Home Assistant health diagnostics")
    p.add_argument("--url", default=os.environ.get("HA_URL"), help="HA base URL (or env HA_URL)")
    p.add_argument("--demo", action="store_true", help="Create a report from synthetic offline data")
    p.add_argument("--observe", type=int, default=0, metavar="SECONDS", help="Observe entity flapping over this many seconds")
    p.add_argument("--interval", type=int, default=10, metavar="SECONDS", help="Polling interval while observing (default: 10)")
    p.add_argument("--stale", action="append", default=[], metavar="GLOB", help="Opt-in staleness check for entity ID glob; repeatable")
    p.add_argument("--stale-hours", type=float, default=24.0, help="Expected reporting interval threshold (default: 24h)")
    p.add_argument("--no-logs", action="store_true", help="Skip the optional error log check")
    p.add_argument("--html", metavar="PATH", help="Write interactive offline HTML report")
    p.add_argument("--json", metavar="PATH", help="Write machine-readable JSON report")
    p.add_argument("--version", action="version", version=f"HA Doctor {__version__}")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    if args.observe < 0 or args.interval < 1 or args.stale_hours <= 0:
        parser().error("--observe must be >= 0, --interval >= 1 and --stale-hours > 0")
    if args.demo:
        snapshots = create_demo()
        cfg = {"version": "demo (synthetic)"}
        categories = {"network": 3, "slow": 1}
        logs_ok = True
    else:
        if not args.url:
            parser().error("Specify --url or HA_URL (or use --demo)")
        token = os.getenv("HA_TOKEN", "")
        if not token and sys.stdin.isatty():
            token = getpass.getpass("Home Assistant access token (input hidden): ")
        if not token:
            parser().error("Set HA_TOKEN or run interactively to enter a token securely")
        try:
            client = HAClient(args.url, token)
            snapshots = [Snapshot(datetime.now(timezone.utc), client.states())]
            print(f"Connected: {len(snapshots[0].states)} entities; observing {args.observe}s", file=sys.stderr)
            start = time.monotonic()
            while args.observe > 0:
                remaining = args.observe - (time.monotonic() - start)
                if remaining <= 0:
                    break
                time.sleep(min(args.interval, remaining))
                snapshots.append(Snapshot(datetime.now(timezone.utc), client.states()))
            try:
                cfg = client.config()
            except DoctorConnectionError:
                cfg = {}
            logs_ok = not args.no_logs
            categories = {}
            if logs_ok:
                try:
                    categories = classify_error_log(client.errors())
                except DoctorConnectionError:
                    logs_ok = False
        except (DoctorConnectionError, ValueError) as err:
            print(f"HA Doctor connection error: {err}", file=sys.stderr)
            return 2
        except KeyboardInterrupt:
            print("Interrupted; no changes made.", file=sys.stderr)
            return 130
    report = diagnose(snapshots, config=cfg, log_counts=categories,
                      log_available=logs_ok, stale_patterns=args.stale, stale_hours=args.stale_hours)
    print(text_report(report))
    if args.html:
        dest = Path(args.html).expanduser()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html_report(report), encoding="utf-8")
        print(f"HTML report: {dest.absolute()}")
    if args.json:
        dest = Path(args.json).expanduser()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(report.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"JSON report: {dest.absolute()}")
    return 1 if any(f.severity == "critical" for f in report.findings) else 0

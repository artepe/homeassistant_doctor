"""Evidence-based heuristics. Avoid pretending that REST states reveal root causes."""

from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from fnmatch import fnmatchcase
import re
from typing import Any


@dataclass
class Snapshot:
    at: datetime
    states: list[dict[str, Any]]


@dataclass
class Finding:
    severity: str
    code: str
    title: str
    detail: str
    action: str
    entities: list[str] = field(default_factory=list)
    count: int = 0


@dataclass
class Report:
    generated_at: str
    version: str
    entity_count: int
    unavailable_count: int
    unknown_count: int
    samples: int
    log_available: bool
    findings: list[Finding]
    observations: list[str]

    def as_dict(self) -> dict:
        return asdict(self)


LOG_RULES = [
    ("recorder", re.compile(r"database is locked|recorder.*(error|failed)|sqlalchemy.*(error|timeout)", re.I),
     "Recorder/database errors", "Inspect recorder database health, storage capacity and recent shutdowns."),
    ("setup", re.compile(r"error setting up|setup failed|config entry .*not ready|configentrynotready", re.I),
     "Integration setup failures", "Open Settings → Devices & services; check the affected integration and its logs."),
    ("slow", re.compile(r"taking over \d+ seconds|blocking call|slow callback", re.I),
     "Slow or blocking operations", "Identify the custom integration or task in the original HA logs; avoid aggressive polling."),
    ("network", re.compile(r"connection refused|connection reset|failed to connect|cannot connect|connection timeout|timed out", re.I),
     "Connectivity/timeout errors", "Check device reachability, DNS, Wi-Fi stability and request timeouts."),
    ("rate", re.compile(r"rate.?limit|too many requests|http 429", re.I),
     "Rate-limit errors", "Reduce polling frequency and check vendor API limits."),
]


def classify_error_log(raw: str) -> dict[str, int]:
    """Return only predefined categories; never retain/share raw log text."""
    counts: Counter[str] = Counter()
    for line in raw.splitlines():
        for key, rx, _, _ in LOG_RULES:
            if rx.search(line):
                counts[key] += 1
                break
    return dict(counts)


def _dt(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except ValueError:
        return None


def _lookup(snapshot: Snapshot) -> dict[str, dict]:
    return {s["entity_id"]: s for s in snapshot.states
            if isinstance(s, dict) and isinstance(s.get("entity_id"), str)
            and isinstance(s.get("state"), str)}


def diagnose(snapshots: list[Snapshot], *, config: dict | None = None,
             log_counts: dict[str, int] | None = None,
             stale_patterns: list[str] | None = None,
             stale_hours: float = 24.0,
             log_available: bool = True) -> Report:
    if not snapshots:
        raise ValueError("At least one state snapshot is required")
    current = _lookup(snapshots[-1])
    available = set(current)
    unavailable = sorted(k for k, v in current.items() if v["state"] == "unavailable")
    unknown = sorted(k for k, v in current.items() if v["state"] == "unknown")
    findings: list[Finding] = []
    observations: list[str] = []

    if unavailable:
        findings.append(Finding(
            "critical" if len(unavailable) >= 10 else "warning", "unavailable",
            f"{len(unavailable)} unavailable entities",
            "These entities currently report unavailable. A single snapshot cannot identify the root cause.",
            "Check the relevant integration's diagnostics and logs; confirm device, USB or network connectivity.",
            unavailable, len(unavailable),
        ))
    if unknown:
        findings.append(Finding(
            "info", "unknown", f"{len(unknown)} entities have unknown state",
            "The entities exist but have no current value. Some helpers legitimately start this way.",
            "Check whether these entities are expected to have a value at this time.", unknown, len(unknown),
        ))

    histories = [_lookup(s) for s in snapshots]
    if len(histories) > 1:
        flaps = []
        for key in available:
            values = [h.get(key, {}).get("state") for h in histories]
            # Count recoveries too: restored entities should not silently disappear from the report.
            transitions = sum(a != b and "unavailable" in (a, b)
                              for a, b in zip(values, values[1:]) if a is not None and b is not None)
            if transitions >= 2:
                flaps.append(key)
        if flaps:
            flaps.sort()
            findings.append(Finding(
                "warning", "flapping", f"{len(flaps)} entities toggled unavailable and back",
                "At least two transitions involving unavailable were observed within this monitoring session.",
                "Inspect shared connectivity, integration update coordination, polling rate and HA logs.",
                flaps, len(flaps),
            ))
        mass = []
        for idx in range(1, len(histories)):
            before, after = histories[idx - 1], histories[idx]
            dropped = sorted(key for key, value in after.items()
                             if value["state"] == "unavailable" and
                             key in before and before[key]["state"] not in {"unavailable", "unknown"})
            if len(dropped) >= 3:
                mass.append((idx, dropped))
        if mass:
            idx, biggest = max(mass, key=lambda x: len(x[1]))
            findings.append(Finding(
                "critical", "simultaneous_outage", f"{len(biggest)} entities became unavailable together",
                f"These entities dropped in the same polling interval (sample {idx + 1}). "
                "This correlation is evidence of a shared problem, not proof of its cause.",
                "Inspect common integration/device dependencies, USB bus, API rate limits and logs at that time.",
                biggest, len(biggest),
            ))

    if stale_patterns:
        stale = []
        missing_timestamp = []
        for key, value in current.items():
            if value["state"] in {"unavailable", "unknown"}:
                continue
            if not any(fnmatchcase(key, pat) for pat in stale_patterns):
                continue
            # Only last_reported represents a write by the integration, not a change in value.
            reported = _dt(value.get("last_reported"))
            if reported is None:
                missing_timestamp.append(key)
            elif (snapshots[-1].at - reported).total_seconds() > stale_hours * 3600:
                stale.append(key)
        if stale:
            findings.append(Finding(
                "warning", "stale", f"{len(stale)} selected entities have not reported recently",
                f"Their last_reported timestamp is older than {stale_hours:g} hours.",
                "Verify the expected update cadence; check integration scheduling and whether the device reports unchanged values.",
                sorted(stale), len(stale),
            ))
        if missing_timestamp:
            observations.append(f"Staleness not assessed for {len(missing_timestamp)} matching entities without last_reported.")

    if log_counts:
        for key, _, title, action in LOG_RULES:
            count = log_counts.get(key, 0)
            if count:
                findings.append(Finding(
                    "warning", "log_" + key, title,
                    f"Found {count} matching log lines in the current HA session. This is a pattern count, not unique incidents.",
                    action, [], count,
                ))
    if not log_available:
        observations.append("Error log unavailable; entity checks still completed.")
    observations.append("REST state data cannot directly determine the owning integration, physical device or exact root cause.")
    observations.append("No settings, entity states or service calls were changed.")
    sev = {"critical": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda f: (sev[f.severity], f.code))
    cfg = config or {}
    return Report(
        generated_at=snapshots[-1].at.isoformat(timespec="seconds"),
        version=str(cfg.get("version") or "unknown"),
        entity_count=len(current), unavailable_count=len(unavailable), unknown_count=len(unknown),
        samples=len(snapshots), log_available=log_available,
        findings=findings, observations=observations,
    )

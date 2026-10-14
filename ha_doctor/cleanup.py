"""Opt-in sensor registry cleanup: inventory, independent review, and explicit deletion."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from secrets import token_hex

from .client import DoctorConnectionError

SENSOR_DOMAINS = frozenset({"sensor", "binary_sensor"})


@dataclass(frozen=True)
class Candidate:
    entity_id: str
    reason: str
    state: str | None
    platform: str
    name: str
    unique_id: str | None
    device_id: str | None
    config_entry_id: str | None

    @property
    def fingerprint(self):
        return (self.entity_id, self.platform, self.unique_id, self.device_id, self.config_entry_id)


def find_candidates(registry, states):
    """Find potentially broken sensor entries. This NEVER declares one safe to remove."""
    if not isinstance(registry, list) or not isinstance(states, list):
        raise DoctorConnectionError("Home Assistant returned invalid registry/state data")
    state_map = {s.get("entity_id"): s for s in states if isinstance(s, dict)}
    candidates = []
    for entry in registry:
        if not isinstance(entry, dict):
            continue
        entity_id = entry.get("entity_id")
        if not isinstance(entity_id, str) or entity_id.partition(".")[0] not in SENSOR_DOMAINS:
            continue
        if entry.get("disabled_by") is not None:
            continue  # Intentionally disabled entities usually have no runtime state.
        state_record = state_map.get(entity_id)
        state = state_record.get("state") if state_record is not None else None
        if state_record is None:
            reason = "missing"  # registry entry exists but no live state (could be temporary)
        elif state is None or (isinstance(state, str) and state.strip().lower() in {"", "none", "null"}):
            reason = "empty"
        elif state == "unavailable":
            reason = "unavailable"
        elif state == "unknown":
            reason = "unknown"
        else:
            continue
        candidates.append(Candidate(
            entity_id=entity_id, reason=reason, state=state if isinstance(state, str) else None,
            platform=str(entry.get("platform") or "unknown"),
            name=str(entry.get("name") or entry.get("original_name") or entity_id),
            unique_id=entry.get("unique_id"), device_id=entry.get("device_id"),
            config_entry_id=entry.get("config_entry_id"),
        ))
    return sorted(candidates, key=lambda c: (c.reason, c.entity_id))


def choose_still_problematic(selected, refreshed):
    """Revalidate current state AND immutable registry identity immediately before edits."""
    lookup = {item.entity_id: item for item in refreshed}
    safe, skipped = [], []
    for earlier in selected:
        current = lookup.get(earlier.entity_id)
        if current is None or current.fingerprint != earlier.fingerprint:
            skipped.append(earlier.entity_id)
        else:
            safe.append(current)
    return safe, skipped


def backup_selection(candidates, *, directory=None):
    """Restricted audit snapshot of registry metadata; not a restorable HA backup."""
    folder = Path(directory or (Path.home() / ".ha-doctor" / "cleanup-backups")).expanduser()
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    payload = {
        "warning": "Metadata audit only, NOT an importable Home Assistant restore. Take an HA backup before deletion.",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "count": len(candidates), "entities": [asdict(c) for c in candidates],
    }
    for _ in range(5):
        path = folder / ("sensor-cleanup-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + token_hex(4) + ".json")
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, indent=2, ensure_ascii=False)
            return path
        except FileExistsError:
            continue
    raise OSError("Could not create a unique cleanup audit snapshot")

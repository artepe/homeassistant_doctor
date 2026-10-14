"""Synthetic snapshots for safe offline demos and smoke tests."""
from datetime import datetime, timedelta, timezone
from .diagnose import Snapshot


def create_demo():
    now = datetime.now(timezone.utc)
    def state(name, value, age=2):
        return {"entity_id": name, "state": value,
                "last_reported": (now - timedelta(minutes=age)).isoformat(), "attributes": {}}
    base = [state("sensor.living_room_temp", "21.4"),
            state("sensor.ouman_supply_temp", "37"),
            state("sensor.ouman_outdoor_temp", "6"),
            state("sensor.ouman_valve", "49"),
            state("sensor.garage_co2", "610", age=200),
            state("binary_sensor.entry_door", "off"),
            state("sensor.plug_energy", "unknown")]
    def snapshot(changes, when):
        return Snapshot(when, [{**s, "state": changes.get(s["entity_id"], s["state"])} for s in base])
    names = ("sensor.ouman_supply_temp", "sensor.ouman_outdoor_temp", "sensor.ouman_valve")
    return [snapshot({}, now - timedelta(seconds=20)),
            snapshot(dict.fromkeys(names, "unavailable"), now - timedelta(seconds=10)),
            snapshot({}, now)]

import unittest
from datetime import datetime, timedelta, timezone
from ha_doctor.demo import create_demo
from ha_doctor.diagnose import Snapshot, classify_error_log, diagnose
from ha_doctor.render import html_report, text_report


NOW = datetime(2026, 10, 14, 14, 0, tzinfo=timezone.utc)


def snap(items, at=NOW):
    return Snapshot(at, [dict(entity_id=k, state=v, last_reported=at.isoformat(), attributes={}) for k,v in items.items()])


class DiagnosisTests(unittest.TestCase):
    def test_demo_detects_simultaneous_outage_and_flapping(self):
        result = diagnose(create_demo())
        codes = {f.code for f in result.findings}
        self.assertIn("simultaneous_outage", codes)
        self.assertIn("flapping", codes)
        self.assertEqual(result.unavailable_count, 0)

    def test_no_false_flap_from_constant_values(self):
        result = diagnose([snap({"sensor.a": "20"}), snap({"sensor.a": "20"})])
        self.assertEqual(result.findings, [])

    def test_unavailable_and_unknown(self):
        result = diagnose([snap({"sensor.bad": "unavailable", "sensor.some": "unknown"})])
        self.assertEqual(result.unavailable_count, 1)
        self.assertEqual(result.unknown_count, 1)
        self.assertEqual({f.code for f in result.findings}, {"unavailable", "unknown"})

    def test_stale_opt_in_and_last_reported_not_last_changed(self):
        entry = {"entity_id": "sensor.temp", "state": "21.0", "last_reported": (NOW-timedelta(minutes=1)).isoformat(),
                 "last_changed": (NOW-timedelta(days=90)).isoformat()}
        r = diagnose([Snapshot(NOW, [entry])], stale_patterns=["sensor.*"], stale_hours=1)
        self.assertNotIn("stale", [f.code for f in r.findings])
        entry["last_reported"] = (NOW-timedelta(hours=3)).isoformat()
        r = diagnose([Snapshot(NOW, [entry])], stale_patterns=["sensor.*"], stale_hours=1)
        self.assertIn("stale", [f.code for f in r.findings])

    def test_missing_timestamp_is_not_falsely_stale(self):
        r = diagnose([Snapshot(NOW, [{"entity_id": "sensor.t", "state": "21"}])], stale_patterns=["sensor.*"])
        self.assertNotIn("stale", [f.code for f in r.findings])
        self.assertTrue(any("not assessed" in s for s in r.observations))

    def test_grouped_outage_needs_three_entities(self):
        r = diagnose([snap({"sensor.a": "on", "sensor.b": "on"}),
                      snap({"sensor.a": "unavailable", "sensor.b": "unavailable"})])
        self.assertNotIn("simultaneous_outage", [f.code for f in r.findings])

    def test_log_classifier_does_not_expose_raw_logs(self):
        lines = "secret_password=password123: Connection refused\nrecorder: database is locked\nConnection refused"
        types = classify_error_log(lines)
        self.assertEqual(types, {"network": 2, "recorder": 1})
        result = diagnose([snap({"sensor.a": "3"})], log_counts=types)
        txt = text_report(result)
        page = html_report(result)
        self.assertNotIn("secret_password", txt + page)
        self.assertNotIn("password123", txt + page)

    def test_html_escapes_entity_names_and_json_script(self):
        malicious = "sensor.x</script><script>alert(1)</script>"
        r = diagnose([snap({malicious: "unavailable"})])
        page = html_report(r)
        self.assertNotIn(malicious, page)
        self.assertIn("&lt;/script&gt;", page)
        self.assertNotIn("<script>alert", page)

    def test_html_contains_severity_filter(self):
        page = html_report(diagnose(create_demo()))
        self.assertIn('data-filter="critical"', page)
        self.assertIn('data-filter="warning"', page)

if __name__ == "__main__":
    unittest.main()

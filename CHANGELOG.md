# Changelog

## v0.3.0 — System Lab & HACS sidebar

- Native HACS-installable HA Doctor integration and sidebar panel.
- Auto-detected CPU, RAM, disk, CPU temperature, optional GPU, swap, uptime, and network telemetry.
- Current-state sensor health and administrator-only confirmed bulk registry cleanup with JSON metadata export and revalidation.
- No additional credentials or cloud service required by the sidebar.

## v0.2.0 (2026-10-14)

- Opt-in localhost Sensor Cleanup browser UI with search, individual checkboxes, and "Select all visible"
- Find empty, unknown, unavailable and state-less registered `sensor` / `binary_sensor` entities
- Safeguards: no preselected items, preview, exact typed DELETE N confirmation, 10-minute single-use plan, anti-CSRF checks
- Revalidate entity IDs, registry identity and live problem state immediately before deletion; skip recovered entries
- Audit metadata JSON saved as a 0600 file before first registry removal (not a restorable HA backup)
- Uses admin-only Home Assistant entity registry WebSocket remove command, without direct `.storage` edits
- Separate `cleanup` optional dependency; regular diagnostics remain dependency-free and read-only

## v0.1.0 (2026-10-14)

Initial runnable MVP:
- Read-only REST API client with strict authentication and redirects disabled
- Unavailable/unknown state diagnostics
- Multi-snapshot flapping and simultaneous-outage detection
- Opt-in `last_reported` staleness rules
- Safe error-log category counting (without saving raw logs)
- Offline HTML dashboard, text and JSON outputs
- Synthetic demo, unit tests and CI

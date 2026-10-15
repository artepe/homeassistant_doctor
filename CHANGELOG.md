# Changelog

## v0.4.1 - Cleanup verification and disable mode

- Differentiate registry deletion from persistent disabling (`disabled_by: user`).
- Verify actual registry state after every batch; report re-created, skipped, failed and unverified entities separately.
- Prevent edits if a sensor recovered or its registry identity changed.
- Add nine frontend unit tests for cleanup behavior.

## 0.4.0
- Guided metric source dropdowns with live values and registry-backed System monitor recommendations, including disabled sensors.
- Explicit activation of selected System monitor sensors, integration setup link and registry refresh.
- Preserve unsaved metric selections during HA updates; do not silently replace missing explicit sources.
- Cache-bust the frontend helper module on upgrade.

# Changelog

## v0.3.1 — Delete reliability patch (2026-10-14)
- Preserve DELETE N input during background Home Assistant updates.
- Explain denied permissions; verify registry identity to prevent deleting replacements.
- Refresh registry after removal and report entities that immediately reappear.

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

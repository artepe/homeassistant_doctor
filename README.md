<div align="center">

# 🩺 HA Doctor

**Because “unavailable” is not a diagnosis.**

**Local diagnostics + optional, deliberately confirmed sensor cleanup.**

[Quick start](#quick-start) · [Sensor Cleanup](#sensor-cleanup--bulk-removal) · [Security](#security) · [Roadmap](#roadmap)

</div>

---

![HA Doctor example dashboard with synthetic data](assets/preview.png)

**HA Doctor** helps Home Assistant users diagnose state outages without manually scrolling through thousands of entities or digging through the entire error log.

- 🔴 **Unavailable entity scan:** See the exact list of entities affected.
- ⚡ **Simultaneous outages:** Catch three or more entities going unavailable in the **same polling interval** — useful when an integration briefly loses connectivity.
- 🔁 **Flapping detection:** Observe entities going unavailable and recovering while the doctor watches.
- ⏱ **Stale data checks:** Opt in to expected reporting intervals for specific entities. Uses **`last_reported`**, not `last_changed`.
- 🧠 **Guided next steps:** Recommendations for common log patterns (integration setup, blocked event loop, rate limits, recorder, networking).
- 🌐 **Interactive offline HTML report:** Open in any browser. No cloud dashboard, external scripts, trackers or external libraries.
- 🔒 **Diagnostics remain read-only:** The separate Sensor Cleanup interface allows registry deletions only after review and typed confirmation.
- 🪶 **Runs anywhere with Python 3.10+:** macOS, Linux, Windows, a Raspberry Pi or a machine that can reach Home Assistant.

> **v0.2.0 / MVP:** This is an **external CLI**, not a HACS integration or a native Home Assistant dashboard. It reports symptoms and plausible next steps, **not guaranteed root causes**. Home Assistant already has per-integration diagnostics downloads; HA Doctor complements rather than replaces them.

## Quick start

### 1. Get Python 3.10 or newer

Download/extract this repository and open a terminal inside the folder. You can run directly without installing dependencies:

```bash
python3 -m ha_doctor --demo --html demo.html
```

Open `demo.html` for a completely offline preview with **synthetic example data**.

### 2. Generate a Home Assistant access token

Open your Home Assistant **Profile** → **Long-Lived Access Tokens** → Create token. Store it privately. **Do not post the token in a GitHub issue, screenshot or chat.**

### 3. Connect to your own Home Assistant

macOS / Linux:

```bash
export HA_URL="http://homeassistant.local:8123"
python3 -m ha_doctor --html report.html
```

Windows PowerShell:

```powershell
$env:HA_URL = 'http://homeassistant.local:8123'
py -m ha_doctor --html report.html
```

When prompted, enter your access token (the input is hidden). For unattended jobs, you can instead set `HA_TOKEN` as an environment variable. Open the generated **`report.html`** in your browser. The tool uses the same address and access method as your browser (local network, VPN, etc.). If mDNS doesn't work, use your HA IP address or your configured HTTPS hostname.

You can alternatively install the command (`pip install .`) and run `ha-doctor` instead of `python3 -m ha_doctor`.

## Sensor Cleanup — bulk removal

**v0.2.0** adds a separate, **opt-in localhost browser interface** to review and delete multiple suspected broken or empty sensor registry entries in one operation. **Normal diagnostics are unchanged and read-only.** This feature is not part of the offline diagnostics HTML report; it runs a local web server so the Home Assistant token never goes to the page.

### macOS copy/paste installation

With [Python 3.10+](https://www.python.org/downloads/) installed, open macOS **Terminal**:

```bash
cd ~/Downloads
git clone https://github.com/artepe/homeassistant_doctor.git
cd homeassistant_doctor
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[cleanup]'
.venv/bin/python -m ha_doctor --cleanup --url http://homeassistant.local:8123
```

If the repository already exists on your Mac, open its folder and run `git pull` instead of cloning a second time. Use the Home Assistant LAN IP instead of `homeassistant.local` when mDNS does not resolve. On Windows, activate a venv or use `py -m pip install -e '.[cleanup]'` followed by `py -m ha_doctor --cleanup --url ...`.

The terminal prompts for a **Home Assistant administrator long-lived access token** (hidden input). Your browser automatically opens an address such as `http://127.0.0.1:52341/`; copy the printed URL if it does not. The UI listens **only on your Mac's loopback interface**, not on your LAN. Keep the Terminal running while using it. Press Ctrl+C to stop.

### What you can review and remove

- **Missing:** Registry entry exists, but there is no corresponding live entity state. Could be a disconnected or temporarily unavailable integration.
- **Empty:** Live state is blank, `null`, or `None`.
- **Unknown:** Current HA state is `unknown`.
- **Unavailable:** Current HA state is `unavailable`.
- **Domain restriction:** Only `sensor.*` and `binary_sensor.*` from the *entity registry*. Disabled entities are intentionally excluded; `0`, `on`, `off`, and other healthy values are not considered empty.

Use search to filter by integration, ID, or reason; choose **Select all visible** or mark individual sensors. Every checkbox starts unchecked. Click **Preview selected for removal** to review. To commit you must **type `DELETE N`**, where `N` is the number of selected candidates, and click the final deletion button. Without that exact confirmation, **nothing is removed**.

Immediately before the edit, HA Doctor re-reads states and entity registry data and **skips entities that recovered or were replaced**. It writes a restricted-permission JSON metadata **audit file** under `~/.ha-doctor/cleanup-backups/` *before* the first deletion. If it cannot write the audit file, deletion is aborted. The log is **not a restorable Home Assistant backup**.

**Important safety limitations:** `unknown`, `unavailable`, empty, and missing are *symptoms*, **not evidence that an entity is obsolete**. A reboot, network outage, device sleep, or an integration initialization can create these states temporarily. Removing an active entity can break automations and dashboards, and the owning integration may recreate it. **Create a full Home Assistant backup in Settings → System → Backups before proceeding.** The removal only affects entity registry entries; it does not purge recorder history, delete devices or uninstall integrations. It is not possible to delete registry-less YAML entities this way. This bulk action needs admin credentials and cannot automatically undo deletion.

Technical implementation: the UI connects with the [Home Assistant WebSocket API](https://developers.home-assistant.io/docs/api/websocket/) using `config/entity_registry/list` and `config/entity_registry/remove`. Its optional dependency is `websocket-client`. Local form requests use an unpredictable anti-CSRF token, localhost-only binding and a second unique confirmation token.

## The useful checks

### Catch entities that flicker unavailable

```bash
python3 -m ha_doctor --observe 60 --interval 5 --html report.html
```

Takes one initial snapshot, then polls for 60 seconds. HA Doctor can report simultaneous failures and recoveries, including devices that **look fine** when you open the States screen after the incident.

**Limitations:** Polling can miss outages shorter than the polling interval. The tool does not claim that all entities going offline together share the same integration; an internet outage could affect several integrations at once.

### Find sensors that stopped updating

```bash
python3 -m ha_doctor \
  --stale 'sensor.ouman_*' \
  --stale 'sensor.heatpump_*' \
  --stale-hours 1 \
  --html report.html
```

The staleness check is **opt in** because not all sensors are expected to report periodically. `last_changed` means the value changed. It is *not* evidence that a sensor is dead. `last_reported` means HA received a state write, although device/reporting semantics can vary. If the timestamp is not available from the API, the tool says so and does not speculate.

### Machine-readable report and privacy controls

```bash
python3 -m ha_doctor --json diagnostics.json --html diagnostics.html
python3 -m ha_doctor --no-logs --html entities-only.html
```

The JSON output is suitable for scripts and recurring external checks. Error logs are categorized **in memory** by predefined patterns; raw log text is **not copied into HTML or JSON**.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Scan ran successfully, no critical findings (warnings may exist) |
| `1` | Scan ran successfully and detected at least one critical finding |
| `2` | Could not connect or parse API data |
| `130` | Interrupted with Ctrl+C |

An exit code of `0` **does not guarantee** that Home Assistant has no problems.

## Security

- **Diagnostic mode** uses only authenticated GET endpoints: `/api/states`, `/api/config` and optional `/api/error_log`. **Cleanup mode** additionally uses authenticated WebSocket registry list/remove (with explicit confirmation).
- Does not send telemetry, analytics or reports to anyone.
- Does not follow HTTP redirects with an access token.
- Verifies HTTPS certificates by default; **does not include an insecure TLS bypass option**.
- Never embeds the token into the report or local cleanup HTML; accepts credentials via hidden Terminal prompt or environment variable.
- Does not persist the raw log. Nevertheless, **entity IDs and version information in reports can be personal**. Review before posting a report publicly.
- A Home Assistant long-lived access token may have broader permissions than this program needs. Treat it as a secret and revoke it if compromised.
- Run only against a Home Assistant server you administer or are authorized to access.

No automatic destructive repair: HA Doctor never automatically deletes registry entries, resets devices, modifies automations or purges history. Sensor Cleanup requires manual selection plus explicit typed confirmation.

## How it works

Home Assistant's documented [REST API](https://developers.home-assistant.io/docs/api/rest/) exposes state objects and current-session errors. HA Doctor samples those states, compares entity availability across samples, then creates a human-readable report. The [Home Assistant state docs](https://www.home-assistant.io/docs/configuration/state_object/) describe the difference between `last_changed`, `last_updated` and `last_reported`.

The diagnostic report does not map each entity to its integration. The **separate Sensor Cleanup tool** uses WebSocket registry metadata, including `platform`, to show which integration created a registered entity.

## Roadmap

- [ ] Home Assistant custom integration/HACS installation with repairs and native dashboard sensors
- [x] Separate WebSocket-powered sensor registry inventory and deliberately confirmed bulk cleanup
- [ ] WebSocket-assisted mapping of *diagnostic outages* by integration/config entry
- [ ] Continuous historical event recording with a bounded local database
- [ ] Configurable rules for safe alerts and suggested fixes
- [ ] Recorder, CPU/memory/storage diagnostics via appropriately authorized APIs/integrations
- [ ] Optional anonymized GitHub issue export after explicit user review
- [ ] Internationalization and screenshot gallery

Feature requests and bug reports welcome — please include the tool version, HA Core version, OS and **sanitized** reproduction steps. Never include raw logs or access tokens.

## Contributing

```bash
python3 -m unittest discover -s tests -v
```

No optional dependency is needed for diagnostics or unit tests; the cleanup UI needs `websocket-client` installed via `pip install -e ".[cleanup]"`. See `CONTRIBUTING.md`.

MIT licensed © 2026 artepe.

# Contributing to HA Doctor

Thanks for helping make Home Assistant diagnostics safer and more useful.

1. File a descriptive issue (what you expected, what happened, sanitized reproduction).
2. Implement heuristics in `ha_doctor/diagnose.py`, with corresponding `unittest` tests.
3. Keep diagnostics strictly **read-only**. HTTP POST, write APIs or automatic restarts must never be silently added.
4. Never request a user's token. Never upload reports, logs, network captures or entity IDs to online services.
5. Remember that a numeric state staying constant is not by itself evidence of stale data.
6. Run `python3 -m unittest discover -s tests -v` before proposing a change.

Pull requests with documentation improvements and reproducible bug fixes are especially welcome.

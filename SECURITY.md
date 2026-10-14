# Security policy

Please do not publish security vulnerabilities as public issues. Reach the repository owner through a private GitHub security advisory if the repository supports it.

## Threat model

A Home Assistant token provides access to the home. HA Doctor only uses authenticated GET requests, and deliberately rejects redirects so that an Authorization header is never forwarded to another origin. Standard TLS certificate checking remains on. HA Doctor does not save the token or raw logs to disk.

`report.html` and the optional JSON output do include entity IDs, which could reveal details of a home. Review and sanitize any reports before sharing. This tool is diagnostic aid, not an authoritative security scanner.

## Sensor Cleanup (v0.2.0)

The separate `--cleanup` mode **can delete entity-registry entries** after explicit selection and typed confirmation. No entities are selected by default. It never edits Home Assistant's `.storage` files or purges recorder data. The local UI binds to `127.0.0.1`, validates `Host` and `Origin`, requires anti-CSRF tokens and rechecks entity state and identity before deletion. A 0600 metadata audit is created before writes. **This audit is not a system backup or undo**; obtain a real HA backup before cleanup. Use an administrator token only with trusted systems.

The running process holds the access token in memory. Never expose the cleanup browser through a reverse proxy or port-forward; this tool is meant for localhost on your own computer.

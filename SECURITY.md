# Security policy

Please do not publish security vulnerabilities as public issues. Reach the repository owner through a private GitHub security advisory if the repository supports it.

## Threat model

A Home Assistant token provides access to the home. HA Doctor only uses authenticated GET requests, and deliberately rejects redirects so that an Authorization header is never forwarded to another origin. Standard TLS certificate checking remains on. HA Doctor does not save the token or raw logs to disk.

`report.html` and the optional JSON output do include entity IDs, which could reveal details of a home. Review and sanitize any reports before sharing. This tool is diagnostic aid, not an authoritative security scanner.

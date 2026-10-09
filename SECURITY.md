# Security Policy

## Supported Versions

Only the latest release is actively supported with security fixes.

| Version | Supported |
|---------|-----------|
| latest  | ✅ |
| older   | ❌ |

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Report vulnerabilities privately via [GitHub Security Advisories](https://github.com/geertmeersman/ha-fleet-monitor/security/advisories/new).

Include as much detail as possible:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (optional)

You can expect an initial response within **72 hours**. If the vulnerability is confirmed, a fix will be prioritized and a new release will be published as soon as possible.

## Security Considerations

When self-hosting HA Fleet Monitor, keep the following in mind:

- **Secret key** — Generated automatically on first run and stored in the database. No manual configuration needed.
- **Admin account** — Use a strong password. The password is stored as a bcrypt hash in the database.
- **SMTP credentials** — Configured via the admin panel and stored in the SQLite database. Restrict access to the `./data` volume on the host.
- **Long-lived access tokens** — HA tokens are stored in the SQLite database. Restrict access to the `./data` volume on the host.
- **Network exposure** — Do not expose the dashboard directly to the internet without a reverse proxy with HTTPS.
- **2FA** — Enable TOTP-based two-factor authentication for additional protection.

## Scope

The following are considered in scope for security reports:

- Authentication bypass
- Privilege escalation
- Sensitive data exposure (tokens, credentials, passwords)
- Remote code execution
- SQL injection or other injection attacks
- CSRF / XSS vulnerabilities

The following are out of scope:

- Vulnerabilities in the underlying host OS or Docker daemon
- Issues requiring physical access to the host
- Self-inflicted misconfiguration (e.g. exposing the container without a reverse proxy)

# Security Policy

## Reporting a Vulnerability

Do not open a public issue. Instead:

1. Go to the repository's **Security** tab and click **Report a vulnerability**
2. Or email the maintainer directly (contact on GitHub profile)

Include: description, reproduction steps, potential impact, and a suggested fix if you have one.

We aim to acknowledge within 48 hours and provide an initial assessment within 7 days. We will not disclose publicly until a fix is available and will credit reporters unless they prefer anonymity.

## Security Practices

When using this tool:

- **API keys**: Store in macOS Keychain via `bluesound-controller keychain set` (not plaintext config)
- **Config files**: Never commit `config.json` to version control
- **Network scope**: All communication is local network only (no external API calls except optional UniFi)
- **Permissions**: Only requires read/write to `~/.config/bluesound-controller`; no sudo needed

## Security Measures

**Input validation** — all external inputs (IPs, hostnames, volumes, timeouts, config values) are validated at boundaries with type checking, length limits, format validation, and shell metacharacter rejection.

**XML parsing** — protected against XML bombs and DoS: size limits (1MB), depth limits (20 levels), element count limits (10K), attribute limits, entity expansion prevention (XXE).

**Subprocess calls** — all calls use `shell=False` with list arguments, explicit timeouts (2–10s), and input validation before execution. No user input is passed to a shell.

**File security** — config files set to `0600`, cache directory to `0700`. Writes are atomic to prevent corruption.

## Known Considerations

- **SSL verification disabled** for local Bluesound device communication. These are local IoT devices without valid certificates. This is intentional and documented.

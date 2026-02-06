# Production Readiness

## Architecture

- **Pure Python** — standard library only, no runtime dependencies
- **macOS native** — uses `dns-sd` and `dscacheutil` for device discovery
- **Local network** — communicates with Bluesound devices over HTTP (BluOS API on port 11000)
- **UniFi integration** — optional HTTPS calls to UniFi Controller for network stats

## Security

| Area | Implementation |
|------|---------------|
| Input validation | IP, hostname, volume, timeout, config values validated at boundaries |
| XML parsing | Size limits (1MB), depth limits (20), element count limits (10K), XXE prevention |
| Subprocess calls | `shell=False`, list arguments, timeouts, metacharacter rejection |
| Secrets | macOS Keychain for API keys; config files set to `0600`, cache to `0700` |
| Network | URL scheme validation, response size limits, retry with backoff |
| SSL | Verification disabled for local IoT devices (documented, intentional) |

## Reliability

- **Retry logic** — exponential backoff on transient network errors (3 retries, max 10s delay)
- **Rate limiting** — per-device throttling to prevent overwhelming devices
- **Graceful degradation** — UniFi sync and discovery each fail independently without crashing
- **Discovery fallback** — mDNS -> LSDP -> cache, each layer independent
- **Atomic writes** — cache and config files written atomically to prevent corruption

## Testing

- 258 tests, ~80%+ coverage
- Unit, integration, and security tests
- All network I/O mocked in tests
- CI runs on Python 3.8–3.12

## Known Limitations

- **macOS only** — depends on `dns-sd` and `dscacheutil`
- **SSL not verified** — local IoT devices don't have valid certificates; could be made configurable
- **No async** — uses `ThreadPoolExecutor` for concurrency, not `asyncio`
- **Single-user** — no authentication or multi-user support (CLI tool)

## Future Considerations

- Homebrew formula for easier installation
- Cross-platform support via `zeroconf` library
- Optional SSL verification for UniFi API calls
- Custom exception types instead of string status codes

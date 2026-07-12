# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

From 1.1.1 onward this file is maintained automatically by
[release-please](https://github.com/googleapis/release-please) based on
[Conventional Commits](https://www.conventionalcommits.org). See [RELEASING.md](RELEASING.md).

## [1.1.4](https://github.com/tbaur/bluesound-controller/compare/v1.1.3...v1.1.4) (2026-07-12)


### Bug Fixes

* **sync:** prefer SyncStatus volume over Status for grouped players ([#28](https://github.com/tbaur/bluesound-controller/issues/28)) ([6f34cb9](https://github.com/tbaur/bluesound-controller/commit/6f34cb99386565420a5e98a492ca1afc009e4044))

## [1.1.3](https://github.com/tbaur/bluesound-controller/compare/v1.1.2...v1.1.3) (2026-07-12)


### Bug Fixes

* **security:** isolate UniFi API key from Config.get ([#26](https://github.com/tbaur/bluesound-controller/issues/26)) ([dfdaa94](https://github.com/tbaur/bluesound-controller/commit/dfdaa948836e448cfc72e3763b725791caa393ad))

## [1.1.2](https://github.com/tbaur/bluesound-controller/compare/v1.1.1...v1.1.2) (2026-07-12)


### Bug Fixes

* **sync:** parse SyncStatus and improve grouped status output ([#24](https://github.com/tbaur/bluesound-controller/issues/24)) ([47e0800](https://github.com/tbaur/bluesound-controller/commit/47e08001234b4996941fec8c578e98ada740186e))

## [1.1.1](https://github.com/tbaur/bluesound-controller/compare/v1.1.0...v1.1.1) (2026-07-12)


### Bug Fixes

* **license:** restore canonical Apache 2.0 LICENSE text ([418aa25](https://github.com/tbaur/bluesound-controller/commit/418aa250a6b9910bbdddfc6d92c24b54e078db27))

## [1.1.0] - 2026-06-24

### Changed

- Minimum Python version raised to 3.10 (required for patched pytest 9.0.3+ in dev/test tooling)
- CI test matrix now runs on Python 3.10–3.13
- Packaging metadata and docs aligned with supported Python versions
- Bumped test dependencies: `pytest` 9.0.3+, `pytest-cov` 7.1+, `pytest-mock` 3.15+, `coverage` 7.10+
- Updated GitHub Actions to current major versions (`checkout@v7`, `setup-python@v6`, `codecov-action@v7`)

### Fixed

- Correct setuptools build backend in `pyproject.toml`
- Declare flat-layout modules for wheel/sdist builds
- Stop printing partial API key output in `keychain get` (CodeQL alert #2)
- Resolve pytest CVE-2025-71176 by requiring pytest >= 9.0.3
- Use `files` instead of deprecated `file` input in Codecov upload step

## [1.0.0] - 2026-01-02

### Initial Release

Production-ready command-line controller for Bluesound devices on macOS.

### Features

#### Device Discovery
- **Dual Discovery Protocol Support**: mDNS (Bonjour) and LSDP (Lenbrook Service Discovery Protocol)
- **Hybrid Mode**: Configure `DISCOVERY_METHOD=both` to try mDNS first, fallback to LSDP
- Automatic device discovery with configurable timeout
- Intelligent caching with TTL to reduce network traffic
- Support for BluOS Players, Servers, Hubs, and secondary zones

#### Status Monitoring
- Comprehensive device information (name, model, brand, firmware)
- Current playback state, volume, and mute status
- Track information (title, artist, album)
- Sync group information (master/slave relationships)
- JSON output mode for scripting

#### Volume Control
- Set absolute volume (0-100%)
- Increment/decrement volume (+/- values)
- Mute/unmute individual or all devices
- Reset to configurable safe volume level
- Multi-device support with pattern matching

#### Playback Control
- Play, pause, stop, skip, previous, toggle
- All commands support all devices, specific devices, or pattern matching
- Concurrent execution for fast multi-device control

#### Queue Management
- View current playback queue with track information
- Clear queue on all or selected devices
- Reorder tracks by moving items within queue

#### Input Source Selection
- List all available audio inputs
- Switch between inputs (Bluetooth, Optical, USB, Network, etc.)
- Display currently selected input

#### Bluetooth Mode Control
- Manual, Automatic, Guest, and Disabled modes
- Get and set Bluetooth modes per device

#### Preset Management
- List all available presets
- Play presets by ID

#### Sync Group Management
- Create sync groups with master/slave relationships
- Add multiple slave devices to a master
- Break sync groups
- List all sync groups

#### Device Diagnostics
- IP address and MAC address
- System uptime
- Raw XML endpoint responses for troubleshooting

#### macOS Keychain Integration
- Secure API key storage in macOS Keychain
- Keychain values take precedence over config.json
- CLI commands: `keychain set/get/delete`

### Security

- **Input Validation**: Comprehensive validation for IP addresses, hostnames, volumes, timeouts
- **XML Parsing Security**: Protection against XML bombs and DoS attacks
  - Size limits (1MB), depth limits (20 levels), element count limits (10,000)
  - Attribute limits, text node limits, entity expansion protection
- **Subprocess Security**: All calls use `shell=False`, input validation, timeouts
- **File Security**: Secure file permissions (600 for config, 700 for cache)

### Production Features

- **Retry Logic**: Automatic retry with exponential backoff for network failures
- **Rate Limiting**: Per-device rate limiting to prevent overwhelming devices
- **Structured Logging**: JSON-formatted logs via `BLUESOUND_STRUCTURED_LOG=1`
- **Error Recovery**: Graceful degradation when optional services fail
- **UniFi Integration**: Optional network statistics from UniFi Controller

### Documentation

- Comprehensive README with quick start guide
- Detailed documentation in `docs/README-DETAILED.md`
- Security policy in `SECURITY.md`
- Contributing guidelines in `CONTRIBUTING.md`
- Code of Conduct in `CODE_OF_CONDUCT.md`

### Testing

- 258 tests with 80%+ code coverage
- 20 test files covering all functionality
- Security, integration, and edge case tests

### Requirements

- Python 3.10+ (standard library only)
- macOS 10.15+ (uses `dns-sd` and `dscacheutil`)

[Unreleased]: https://github.com/tbaur/bluesound-controller/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/tbaur/bluesound-controller/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/tbaur/bluesound-controller/releases/tag/v1.0.0

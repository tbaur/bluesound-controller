# Bluesound Controller

[![Tests](https://github.com/tbaur/bluesound-controller/actions/workflows/test.yml/badge.svg)](https://github.com/tbaur/bluesound-controller/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![macOS](https://img.shields.io/badge/macOS-10.15%2B-lightgrey.svg)](https://www.apple.com/macos/)

Command-line controller for Bluesound devices on macOS. Pure Python standard library — no external dependencies.

## Quick Start

```bash
cd ~/github/bluesound-controller
./install.sh
```

This installs to `~/.config/bluesound-controller` and creates a symlink at `~/local/bin/bluesound-controller`.

```bash
bluesound-controller discover          # Find devices
bluesound-controller status            # Show all device status
bluesound-controller volume 25         # Set volume
bluesound-controller play "Kitchen"    # Play on specific device
bluesound-controller --help            # Full command reference
```

## Features

- **Discovery** — mDNS and/or LSDP, with caching
- **Playback** — play, pause, stop, skip, previous, toggle
- **Volume** — absolute, relative (+/-), mute/unmute, reset to safe level
- **Queue** — view, clear, reorder
- **Inputs** — list and switch audio sources
- **Bluetooth** — get/set mode (manual, auto, guest, disable)
- **Presets** — list and play
- **Sync Groups** — create, break, list multi-room groups
- **Diagnostics** — device info, uptime, network stats
- **UniFi Integration** — optional network statistics from UniFi Controller
- **Keychain** — store API keys securely in macOS Keychain

All commands support targeting all devices (default), a specific device by name, or pattern matching.

## Configuration

Stored in `~/.config/bluesound-controller/config.json`:

```json
{
  "BLUOS_SERVICE": "_musc._tcp",
  "DISCOVERY_METHOD": "mdns",
  "DISCOVERY_TIMEOUT": "5",
  "CACHE_TTL": "300",
  "DEFAULT_SAFE_VOL": "14",
  "UNIFI_ENABLED": "false",
  "UNIFI_CONTROLLER": "",
  "UNIFI_API_KEY": "",
  "UNIFI_SITE": "default"
}
```

Discovery methods: `mdns` (default), `lsdp`, or `both` (mDNS first, LSDP fallback).

### API Key Storage

For UniFi integration, store your API key in macOS Keychain instead of plaintext config:

```bash
bluesound-controller keychain set      # Store key
bluesound-controller keychain get      # Check status
bluesound-controller keychain delete   # Remove key
```

Keychain values take precedence over `config.json`.

## Requirements

- Python 3.8+ (standard library only)
- macOS 10.15+ (uses `dns-sd` and `dscacheutil` for discovery)

## Uninstall

```bash
rm -rf ~/.config/bluesound-controller
rm ~/local/bin/bluesound-controller
```

## Documentation

- [Detailed Documentation](docs/README-DETAILED.md) — full usage guide, troubleshooting, development
- [API Verification](docs/API_VERIFICATION.md) — BluOS API compatibility notes
- [Production Readiness](docs/PRODUCTION_READINESS.md) — architecture and security overview
- [CHANGELOG](CHANGELOG.md) — version history
- [CONTRIBUTING](CONTRIBUTING.md) — contribution guidelines
- [SECURITY](SECURITY.md) — security policy

## License

Copyright 2026 tbaur. Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE).

# Bluesound Controller

[![Tests](https://github.com/tbaur/bluesound-controller/actions/workflows/test.yml/badge.svg)](https://github.com/tbaur/bluesound-controller/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![macOS](https://img.shields.io/badge/macOS-10.15%2B-lightgrey.svg)](https://www.apple.com/macos/)

A unified command-line controller for Bluesound devices on macOS.

v1.0.0 - Production-ready with retry logic, rate limiting, structured logging, and comprehensive error recovery.

## Quick Start

### Installation

```bash
cd ~/github/bluesound-controller
./install.sh
```

The script will set up the controller in `~/.config/bluesound-controller` and create a symlink at `~/local/bin/bluesound-controller`.

### Basic Usage

```bash
# Discover devices
bluesound-controller discover

# Show status for all devices
bluesound-controller status

# Control volume
bluesound-controller volume 25
bluesound-controller volume +5 "Living Room"

# Playback control
bluesound-controller play
bluesound-controller pause "Kitchen"
bluesound-controller skip

# Get help
bluesound-controller --help
```

## Safe & Isolated Installation

**100% Safe to Try** - This tool is completely isolated and won't affect your system:

- ✅ **No Global Installation**: Uses only Python standard library - no pip packages, no system-wide changes
- ✅ **User Directory Only**: All files are stored in `~/.config/bluesound-controller` (your home directory)
- ✅ **No System Python Changes**: Doesn't modify system Python, doesn't require admin privileges
- ✅ **Easy to Remove**: Delete one directory to completely uninstall
- ✅ **No Dependencies**: Pure Python standard library - nothing to break or conflict

### Complete Removal

If you want to completely remove the controller:

```bash
# Remove the installation directory
rm -rf ~/.config/bluesound-controller

# Remove the symlink (if you added it to PATH)
rm ~/local/bin/bluesound-controller
```

That's it! No system files touched, no Python packages to uninstall, no traces left behind.

### Reset Configuration

To start fresh with default settings:

```bash
# Remove just the config (keeps the installation)
rm ~/.config/bluesound-controller/config.json

# Or remove cache only
rm -rf ~/.config/bluesound-controller/cache/*
```

The controller will automatically recreate default configuration on next run.

## Features

- **Device Discovery**: Automatic discovery via mDNS or LSDP
- **Status Monitoring**: Comprehensive device and network statistics
- **Volume Control**: Set, adjust, mute/unmute with multi-device support
- **Playback Control**: Play, pause, stop, skip, previous, toggle
- **Queue Management**: View, clear, and reorder playback queue
- **Input Selection**: List and switch audio inputs
- **Bluetooth Control**: Configure Bluetooth modes
- **Preset Management**: List and play device presets
- **Sync Groups**: Create and manage multi-room sync groups
- **Device Diagnostics**: Detailed device information and troubleshooting
- **UniFi Integration**: Optional network statistics from UniFi Controller
- **Secure Keychain Storage**: Store API keys securely in macOS Keychain (macOS only)

All commands support operating on all devices (default), specific devices by name, or pattern matching.

## Configuration

Configuration is stored in `~/.config/bluesound-controller/config.json`:

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

**Discovery Methods:**
- `mdns` - mDNS/Bonjour discovery (default)
- `lsdp` - LSDP protocol (more reliable on networks with multicast issues)
- `both` - Try mDNS first, fallback to LSDP

### Secure API Key Storage (macOS)

For enhanced security, you can store your UniFi API key in macOS Keychain instead of plaintext in `config.json`:

```bash
# Store API key in Keychain
bluesound-controller keychain set

# Check API key status
bluesound-controller keychain get

# Remove API key from Keychain
bluesound-controller keychain delete
```

**Benefits:**
- ✅ API key stored securely in macOS Keychain (encrypted)
- ✅ Keychain values take precedence over `config.json`
- ✅ No plaintext API keys in config files
- ✅ Backward compatible: existing `config.json` entries still work

## Requirements

- **Python**: 3.8+ (standard library only - no external dependencies)
- **macOS**: See supported versions below
- **Network**: Access to Bluesound devices on local network

### Supported macOS Versions

**Validated & Confirmed:**
- ✅ **macOS 26.2** - Tested and confirmed working

**Should Work On:**
- ✅ **macOS 15.x** (Sequoia) - `dns-sd` and `dscacheutil` available
- ✅ **macOS 14.x** (Sonoma) - `dns-sd` and `dscacheutil` available
- ✅ **macOS 13.x** (Ventura) - `dns-sd` and `dscacheutil` available
- ✅ **macOS 12.x** (Monterey) - `dns-sd` and `dscacheutil` available
- ✅ **macOS 11.x** (Big Sur) - `dns-sd` and `dscacheutil` available
- ✅ **macOS 10.15** (Catalina) - `dns-sd` and `dscacheutil` available
- ⚠️ **macOS 10.14 and earlier** - Should work, but not tested. `dns-sd` available since 10.2, `dscacheutil` since 10.5.

**Note**: This tool uses only macOS native commands (`dns-sd` for mDNS discovery and `dscacheutil` for hostname resolution) that have been part of macOS for over 15 years. If your macOS version includes these commands, the tool should work.

### Windows & Linux Support

Currently, this tool is **macOS-only** due to its use of native macOS commands (`dns-sd` and `dscacheutil`). However, we're open to exploring support for other platforms!

**Interested in Windows or Linux support?**
- 🐛 **Open an issue** on GitHub to discuss requirements and implementation approaches
- 💡 We can explore alternatives like:
  - Cross-platform mDNS libraries (e.g., `zeroconf` for Python)
  - Platform-specific discovery methods
  - Conditional compilation or platform detection
- 🤝 **Contributions welcome!** If you'd like to help implement cross-platform support, we'd love to collaborate.

Let's explore together! Open an issue and let's discuss how we can make this work on your platform.

## Documentation

📖 **[View Detailed Documentation](docs/README-DETAILED.md)** - Complete feature documentation, usage examples, troubleshooting, and development guide.

### Additional Documentation

- [CHANGELOG.md](CHANGELOG.md) - Version history and changes
- [SECURITY.md](SECURITY.md) - Security policy and reporting
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) - Code of conduct
- [docs/PRODUCTION_READINESS.md](docs/PRODUCTION_READINESS.md) - Production readiness assessment
- [docs/TESTING_SUMMARY.md](docs/TESTING_SUMMARY.md) - Testing documentation

## Statistics

- **263 tests** with **82% code coverage**
- **~4,200 lines** of code (excluding tests)
- **16 CLI commands** with multi-device support
- **50+ features** across device management, playback control, and network integration

## License

Copyright 2026 tbaur

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) file for details.

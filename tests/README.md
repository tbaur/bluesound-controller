# Test Suite

258 tests covering validators, config, network, controller, CLI, LSDP discovery, keychain, and integration flows.

## Running Tests

```bash
pip install -r requirements-test.txt

pytest tests/ -v                         # all tests
pytest tests/test_validators.py -v       # single file
pytest tests/ --cov=. --cov-report=html  # with coverage report
```

## Test Files

| File | Scope |
|------|-------|
| `test_validators.py` | IP, hostname, volume, timeout, config value validation |
| `test_config.py` | JSON config loading, defaults, INI fallback, Keychain priority |
| `test_keychain.py` | macOS Keychain set/get/delete, error handling, non-macOS fallback |
| `test_utils_comprehensive.py` | Format functions, atomic file operations |
| `test_utils_retry.py` | Retry decorator, rate limiter |
| `test_network.py` | HTTP requests, error handling, URL validation, size limits |
| `test_controller.py` | Device info, cache management, XML parsing |
| `test_controller_coverage.py` | Additional controller edge cases |
| `test_controller_discovery.py` | Discovery methods (mDNS, LSDP, hybrid) |
| `test_controller_new_features.py` | Playback, queue, presets, sync, Bluetooth, inputs, reboot |
| `test_controller_xml.py` | XML bomb protection, depth/size/entity limits |
| `test_cli_commands.py` | CLI command dispatch and output |
| `test_cli_coverage.py` | CLI edge cases and error paths |
| `test_cli_multi_device.py` | Multi-device targeting and filtering |
| `test_lsdp.py` | LSDP packet parsing and discovery |
| `test_lsdp_comprehensive.py` | LSDP device classes, filtering, edge cases |
| `test_main.py` | Entry point and argument parsing |
| `test_main_coverage.py` | Main module edge cases |
| `test_integration.py` | End-to-end discovery and status flows |

## Fixtures

Defined in `conftest.py`:

- `temp_config_dir` — temporary directory for test files
- `mock_config` — mock configuration object
- `sample_config_file` — sample `config.json`
- `sample_cache_file` — sample cache file

## Conventions

- All network I/O and subprocess calls are mocked
- Temporary directories used for file operations (no pollution of real config)
- `pytest-timeout` enforces a 30s limit per test

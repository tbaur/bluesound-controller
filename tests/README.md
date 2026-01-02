# Test Suite

Comprehensive test suite for Bluesound Controller.

## Test Files

- **test_validators.py**: Tests for input validation and sanitization
  - IP address validation
  - Hostname validation
  - Volume/timeout validation
  - Config value validation

- **test_config.py**: Tests for configuration management
  - JSON config loading
  - Config value validation
  - Default config creation
  - INI fallback
  - Keychain integration (API key retrieval priority)

- **test_keychain.py**: Tests for macOS Keychain integration
  - API key storage and retrieval
  - Keychain existence checks
  - Error handling and edge cases
  - Non-macOS platform handling

- **test_utils.py**: Tests for utility functions
  - Format functions (bytes, rate, uptime)
  - Atomic file operations

- **test_network.py**: Tests for network operations
  - HTTP requests
  - Error handling
  - URL validation
  - Size limits

- **test_controller.py**: Tests for core controller logic
  - Device discovery
  - Cache management
  - XML parsing (with bomb protection)
  - UniFi integration
  - Device info retrieval

- **test_integration.py**: Integration tests
  - Full discovery flow
  - Status command flow
  - End-to-end validation

## Running Tests

### Install Dependencies

```bash
pip install -r requirements-test.txt
```

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test File

```bash
pytest tests/test_validators.py -v
```

### Run with Coverage

```bash
pytest tests/ --cov=. --cov-report=html
```

### Run Specific Test Class

```bash
pytest tests/test_validators.py::TestValidateIP -v
```

## Test Coverage

The test suite covers:

- ✅ Input validation (IPs, hostnames, volumes, timeouts)
  - Type checking, length limits, shell metacharacter rejection
  - Null byte and newline rejection
  - Edge cases and invalid inputs
- ✅ Configuration loading and validation
- ✅ Network operations and error handling
- ✅ XML parsing with comprehensive security protections
  - Size limits, depth limits, element count limits
  - Attribute limits, text node limits
  - Recursion error handling, whitespace validation
- ✅ Device discovery and caching
- ✅ UniFi integration
- ✅ macOS Keychain integration (API key storage)
- ✅ Subprocess security (timeouts, input validation, shell injection prevention)
- ✅ Error handling and edge cases
- ✅ Integration flows

## Fixtures

- `temp_config_dir`: Temporary directory for test files
- `mock_config`: Mock configuration object
- `sample_config_file`: Sample config.json file
- `sample_cache_file`: Sample cache file

## Notes

- All tests use temporary directories to avoid polluting the actual config
- Network operations are mocked to avoid actual network calls
- Subprocess calls are mocked for testing
- Tests validate security features (IP validation, XML protection, etc.)


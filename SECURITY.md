# Security Policy

## Supported Versions

We actively support and provide security updates for the main branch. All security updates are applied to the main branch and will be clearly marked in the CHANGELOG.

## Reporting a Vulnerability

If you discover a security vulnerability, please **do not** open a public issue. Instead, please report it privately:

1. **Email**: Open a security advisory on GitHub (preferred)
   - Go to the repository's "Security" tab
   - Click "Report a vulnerability"
   - Fill out the security advisory form

2. **Alternative**: If you cannot use GitHub's security advisory system, you can email the maintainer directly (contact information available on GitHub profile).

### What to Include

When reporting a vulnerability, please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)
- Your contact information

### Response Time

We aim to:
- Acknowledge receipt within 48 hours
- Provide an initial assessment within 7 days
- Keep you updated on progress every 7-14 days

### Disclosure Policy

- We will work with you to understand and resolve the issue quickly
- We will not disclose the vulnerability publicly until a fix is available
- We will credit you in the security advisory (unless you prefer to remain anonymous)

## Security Best Practices

When using this tool:

1. **Configuration Files**: Never commit `config.json` or `config.ini` to version control
2. **API Keys**: Store UniFi API keys securely using macOS Keychain (recommended)
   - Use `bluesound-controller keychain set` to store API keys securely
   - Keychain provides encrypted, system-managed storage
   - Avoid storing API keys in plaintext `config.json` files
3. **Network**: This tool communicates with local network devices only
4. **Permissions**: The tool only requires read/write access to `~/.config/bluesound-controller`
5. **No Admin Rights**: The tool does not require sudo/administrator privileges
6. **Keychain Access**: Keychain operations require user authentication (macOS security feature)

## Known Security Considerations

- **SSL Verification Disabled**: SSL verification is intentionally disabled for local IoT device communication. This is documented in the code and is appropriate for local network use.

### XML Parsing Security ✅ Enhanced
XML parsing includes comprehensive protection against XML bombs and DoS attacks:
- **Size Limits**: Maximum XML size of 1MB (prevents memory exhaustion)
- **Depth Limits**: Maximum nesting depth of 20 levels (prevents stack overflow)
- **Element Count Limits**: Maximum 10,000 total elements (prevents processing DoS)
- **Attribute Limits**: Maximum 100 attributes per element (prevents attribute flooding)
- **Text Node Limits**: Maximum 10% of total size per text node (prevents text flooding)
- **Entity Expansion Protection**: ElementTree parser prevents external entity expansion (XXE protection)
- **Recursion Protection**: Handles recursion errors gracefully
- **Whitespace Validation**: Rejects empty or whitespace-only XML

### Input Validation Security ✅ Enhanced
All user inputs are comprehensively validated and sanitized:
- **IP Address Validation**: 
  - Type checking (prevents type confusion)
  - Format validation (IPv4 only)
  - Range validation (rejects private/reserved addresses)
  - Length limits (max 15 characters)
  - Null byte and newline rejection
  - Shell metacharacter rejection
- **Hostname Validation**:
  - RFC 1035 compliant format validation
  - Length limits (max 253 characters)
  - Shell metacharacter rejection (prevents command injection)
  - Null byte and newline rejection
  - Type checking
- **Volume Validation**:
  - Type validation (handles int, float, string)
  - Range clamping (0-100)
  - Safe conversion with error handling
- **Timeout Validation**:
  - Range clamping (1-60 seconds default)
  - Custom range support
  - Type validation

### Subprocess Security ✅ Enhanced
All subprocess calls include comprehensive security protections:
- **Timeout Protection**: All subprocess calls have explicit timeouts
  - Keychain operations: 5 seconds
  - DNS resolution: 5 seconds (SUBPROCESS_TIMEOUT)
  - ARP lookups: 2 seconds
  - Test execution: 10 minutes (development only)
- **Input Validation**: All inputs validated before subprocess execution
  - Hostnames validated before `dscacheutil` calls
  - Service names validated before `dns-sd` calls
  - Keychain service/account names validated
  - IP addresses validated before `arp` calls
- **Shell Injection Prevention**: 
  - All subprocess calls use `shell=False` (explicit)
  - Arguments passed as lists (not strings)
  - Shell metacharacter validation before execution
  - No user input passed directly to shell
- **Output Size Limits**: Subprocess output size validated to prevent memory exhaustion
- **Error Handling**: Comprehensive exception handling for all subprocess failures

## Security Updates

Security updates will be applied to the main branch and will be clearly marked in the CHANGELOG.


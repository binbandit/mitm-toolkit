# Security Policy

## ⚠️ Important Security Notice

**MITM Toolkit is a powerful traffic interception tool. Use responsibly and legally.**

### Legal and Ethical Use Only

This tool is intended for:
- Testing and debugging your own applications
- Analyzing APIs you have permission to access
- Creating local development environments
- Educational and research purposes with proper authorization

### Prohibited Uses

DO NOT use this tool for:
- Intercepting traffic without authorization
- Bypassing security measures
- Accessing systems you don't own or have permission to test
- Any illegal or unethical activities

## Security Considerations

### 1. Captured Data

**WARNING**: Captured traffic may contain sensitive information including:
- Authentication tokens and API keys
- Passwords and credentials
- Personal identifiable information (PII)
- Proprietary business data

**Best Practices**:
- Store captures securely (encrypted storage recommended)
- Never commit `captures.db` to version control
- Regularly clean old captures: `rm captures.db`
- Use the SensitiveDataMasker plugin to automatically mask sensitive data

### 2. Certificate Installation

Installing the mitmproxy certificate allows decryption of HTTPS traffic:
- Only install on devices you own
- Remove the certificate when not in use
- Be aware this bypasses certificate pinning

### 3. Network Security

When running the proxy:
- Use on trusted networks only
- Bind to localhost unless necessary: `--host 127.0.0.1`
- Use firewall rules to restrict access
- Disable when not actively using

### 4. AI Features

When using AI analysis:
- Sensitive data may be sent to local Ollama instance
- Ensure Ollama is running locally, not exposed to network
- Review data before AI analysis
- Use data masking plugins

## Reporting Security Issues

If you discover a security vulnerability in MITM Toolkit:

1. **DO NOT** create a public GitHub issue
2. Report security issues via GitHub Security Advisories (private)
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## Data Protection

### Storage Security

```bash
# Encrypt captures database
openssl enc -aes-256-cbc -salt -in captures.db -out captures.db.enc

# Decrypt when needed
openssl enc -aes-256-cbc -d -in captures.db.enc -out captures.db
```

### Automatic Data Masking

Enable built-in security plugins:

```yaml
# ~/.mitm-toolkit/plugins/plugins.yaml
plugins:
  - name: SensitiveDataMasker
    enabled: true
    config:
      mask_passwords: true
      mask_tokens: true
      mask_api_keys: true
```

## Compliance

Users are responsible for ensuring compliance with:
- Local laws and regulations
- GDPR, CCPA, and other privacy laws
- Company security policies
- Terms of service of intercepted services

## Disclaimer

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND. The authors and contributors are not responsible for any misuse or damage caused by this tool. Users assume all responsibility for their use of MITM Toolkit.

By using this tool, you agree to use it legally and ethically, respecting the privacy and security of others.
# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in Aegis, please report it responsibly.

**Do NOT create a public GitHub issue for security vulnerabilities.**

Instead, please email: **security@aegis-devsecops.dev**

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Impact assessment
- Suggested fix (if any)

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Assessment**: Within 1 week
- **Fix**: Depending on severity, typically within 2 weeks for critical issues

### Disclosure Policy

- We will coordinate disclosure with you
- We will credit reporters in the security advisory (unless you prefer anonymity)
- We follow responsible disclosure practices

## Security Practices

Aegis follows security best practices:

- All dependencies are audited via `npm audit` and Trivy
- Container images are scanned for CVEs in CI
- Secrets are never stored in code — use environment variables or secret managers
- Authentication uses JWT + OIDC with configurable providers
- RBAC is enforced at the API layer
- AI tool execution requires explicit approval for write operations

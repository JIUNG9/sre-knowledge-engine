# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in Aegis, please report it responsibly.

**Do NOT create a public GitHub issue for security vulnerabilities.**

Instead, report it privately through GitHub:
[**Report a vulnerability**](https://github.com/JIUNG9/sre-knowledge-engine/security/advisories/new)

That opens an advisory visible only to you and the maintainer, and nothing is public
until there's a fix.

> This previously said to email `security@aegis-devsecops.dev`. That domain doesn't
> resolve — no MX, no A record — so any report sent there bounced. A dead reporting
> channel is worse than none, because a researcher tries it, gets nothing, and either
> gives up or discloses publicly.
>
> **Maintainer note:** the advisory link requires *Private vulnerability reporting*
> switched on under **Settings → Advanced Security**. One checkbox, free on public
> repos. Until it's on, that URL 404s for outside reporters.

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

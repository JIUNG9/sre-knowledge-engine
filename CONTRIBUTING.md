# Contributing to Aegis

Thank you for your interest in contributing to Aegis! This document provides guidelines and information to help you get started.

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How to Contribute

### Reporting Bugs

1. Check existing [issues](https://github.com/junegu/aegis/issues) to avoid duplicates
2. Use the bug report template when creating a new issue
3. Include reproduction steps, expected behavior, and actual behavior
4. Add screenshots or logs if applicable

### Suggesting Features

1. Check existing issues and discussions for similar proposals
2. Use the feature request template
3. Describe the problem you're solving, not just the solution
4. Include use cases and examples

### Submitting Code

1. Fork the repository
2. Create a feature branch from `main`: `git checkout -b feat/your-feature`
3. Make your changes following the conventions below
4. Write tests for new functionality
5. Run the full test suite: `pnpm test`
6. Submit a pull request using the PR template

## Development Setup

### Prerequisites

- Node.js >= 20.0.0
- pnpm >= 9.0.0
- Go >= 1.22
- Python >= 3.12
- Docker & Docker Compose

### Getting Started

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/aegis.git
cd aegis

# Install dependencies
pnpm install

# Start development services
docker compose up -d postgres redis clickhouse

# Start all apps
pnpm dev
```

## Conventions

### Branch Naming

| Prefix | Use |
|--------|-----|
| `feat/` | New features |
| `fix/` | Bug fixes |
| `docs/` | Documentation only |
| `refactor/` | Code refactoring |
| `perf/` | Performance improvements |
| `test/` | Test additions/fixes |
| `ci/` | CI/CD changes |
| `chore/` | Maintenance tasks |

### Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(log-explorer): add full-text search with ClickHouse
fix(slo): correct error budget calculation for 30-day windows
docs: add architecture decision record for ClickHouse
ci: add GitHub Actions workflow for Go API tests
```

### Code Style

- **TypeScript/React**: ESLint + Prettier (auto-formatted)
- **Go**: `gofmt` + `golangci-lint`
- **Python**: `ruff` format + lint

### Pull Request Guidelines

- Keep PRs focused — one feature or fix per PR
- Update tests and documentation
- Add screenshots for UI changes
- Reference related issues
- Ensure CI passes before requesting review

## Project Structure

```
aegis/
├── apps/
│   ├── web/          # Next.js frontend
│   ├── api/          # Go API gateway
│   ├── ai-engine/    # Python AI service
│   └── docs/         # Documentation site
├── packages/
│   ├── ui/           # Shared UI components
│   ├── integrations/ # Integration plugins
│   ├── types/        # Shared TypeScript types
│   └── config-*/     # Shared configurations
└── deploy/           # Docker, Helm, Terraform
```

## Need Help?

- Join our [Discord](https://discord.gg/aegis)
- Open a [Discussion](https://github.com/junegu/aegis/discussions)
- Read the [Documentation](https://aegis-devsecops.dev/docs)

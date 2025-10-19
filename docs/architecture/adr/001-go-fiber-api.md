# ADR-001: Use Go + Fiber for API Layer

## Status

Accepted

## Context

Aegis needs a performant API gateway that handles REST endpoints, WebSocket connections for real-time log streaming, and webhook ingestion from multiple monitoring tools (SigNoz, Datadog, Prometheus). The API must handle concurrent connections efficiently with low memory overhead.

We considered three options:
1. **Go + Fiber** — Industry standard for DevOps/SRE tooling (Kubernetes, Terraform, Prometheus are all Go)
2. **Node.js + TypeScript** — Unified stack with the frontend, easier initial development
3. **Python + FastAPI** — Single backend language with the AI engine

## Decision

We chose **Go + Fiber** for the API layer.

Rationale:
- **Performance**: Go's goroutines handle concurrent WebSocket connections and webhook ingestion efficiently. Fiber is built on fasthttp, one of the fastest HTTP implementations available.
- **Memory**: Go services typically use 10-50MB vs 100-300MB for Node.js. Important for container density in Kubernetes.
- **DevOps ecosystem alignment**: The DevOps/SRE community recognizes Go as the standard. Tools like kubectl, Terraform, Prometheus, and ArgoCD are all Go. This matters for community contribution and hiring.
- **Type safety**: Go's static typing prevents a class of runtime errors common in Node.js/Python APIs.
- **WebSocket**: Fiber has excellent WebSocket support via `gofiber/contrib/websocket`.

## Consequences

### Positive

- Excellent performance for concurrent connections
- Low memory footprint for container deployment
- Strong type safety reduces runtime errors
- Aligns with DevOps/SRE industry standards
- Easy to cross-compile for multiple platforms

### Negative

- Two languages in the codebase (Go + TypeScript) increases cognitive overhead
- Go's error handling is verbose compared to try/catch
- Fewer ORM options compared to TypeScript (Prisma) or Python (SQLAlchemy)

### Neutral

- The AI engine remains in Python (better ML/AI ecosystem), so we have a polyglot architecture regardless

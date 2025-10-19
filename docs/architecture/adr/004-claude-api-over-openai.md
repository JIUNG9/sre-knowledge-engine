# ADR-004: Use Claude API (Anthropic) Over OpenAI for Incident Analysis

## Status

Accepted

## Context

Aegis needs an LLM for incident investigation, root cause analysis, and remediation proposal generation. The AI agent must use tools (MCP) to query infrastructure, analyze logs, and propose fixes. We evaluated:

1. **Claude API (Anthropic)** — Claude Sonnet 4.6 / Opus 4.6
2. **OpenAI GPT-4o** — GPT-4o / GPT-4o-mini
3. **AWS Bedrock** — Managed access to multiple models
4. **Self-hosted (Ollama)** — Local models for cost elimination

## Decision

We chose **Claude API** as the primary LLM provider.

Rationale:
- **Tool use quality**: Claude's tool use (function calling) is consistently ranked highest for complex multi-step tool orchestration. Critical for MCP-based incident investigation.
- **MCP native support**: Anthropic created the MCP (Model Context Protocol) standard. Claude has the best MCP integration.
- **Reasoning depth**: For root cause analysis, we need deep reasoning over logs, metrics, and infrastructure state. Claude excels at multi-step logical reasoning.
- **Cost efficiency**: Claude Sonnet 4.6 at $3/$15 per million tokens offers excellent reasoning-per-dollar. With prompt caching (90% off) and batch API (50% off), costs drop further.
- **Safety**: Claude's constitutional AI approach aligns with our security-first philosophy. Important when the AI has tools to modify infrastructure.

## Consequences

### Positive

- Best-in-class tool use for MCP integration
- Strong reasoning for root cause analysis
- Cost-effective with caching and batch optimizations
- Safety-conscious approach for infrastructure actions

### Negative

- Vendor dependency on Anthropic (mitigated by abstracting the LLM interface)
- No self-hosted option (unlike Ollama/vLLM with open models)
- Rate limits may be a concern at scale

### Neutral

- The AI engine abstraction layer allows swapping to other providers (OpenAI, Bedrock) if needed
- Users can configure their own API key and preferred model

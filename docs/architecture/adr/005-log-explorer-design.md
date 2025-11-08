# ADR-005: Log Explorer Architecture — ClickHouse Full-Text + WebSocket Streaming

## Status

Accepted

## Context

The Log Explorer needs to support:
1. Full-text search across millions of log entries
2. Sub-second query responses for time-range and service filtering
3. Real-time log tailing via WebSocket
4. Security-focused log views (auth failures, privilege escalation)
5. AI-powered log summarization and anomaly detection

We need a storage and query architecture that handles both historical queries and real-time ingestion.

## Decision

### Storage: ClickHouse with tokenbf_v1 Index

We use ClickHouse's `tokenbf_v1` bloom filter index on the message column for full-text search. This provides approximate matching with very low false-positive rates, at a fraction of the cost of a dedicated search engine like Elasticsearch.

Table partitioned by month (`toYYYYMM(timestamp)`) and ordered by `(service, level, timestamp)` for optimal query patterns:
- Filter by service → uses primary key prefix
- Filter by level → uses primary key
- Time range → uses partition pruning
- Full-text → uses bloom filter index

### Real-time: WebSocket + Redis Pub/Sub

Live tail uses WebSocket connections from the frontend. The API subscribes to a Redis pub/sub channel where new log entries are published by the ingestion pipeline. This decouples ingestion from streaming and supports multiple concurrent viewers.

### AI Analysis: Batch Summarization via Claude API

Log summarization runs as a batch operation — the user selects a time range, and the AI engine fetches the relevant logs and calls Claude for analysis. This avoids continuous token burn while providing on-demand intelligence.

Natural language → ClickHouse query translation uses Claude's SQL generation capability, constrained to the known log table schema for safety.

## Consequences

### Positive
- ClickHouse tokenbf_v1 provides "good enough" full-text search without Elasticsearch overhead
- Partition pruning makes time-range queries extremely fast
- WebSocket + Redis pub/sub scales to many concurrent viewers
- AI analysis is on-demand, not continuous, keeping costs low

### Negative
- Full-text search quality is lower than Elasticsearch (no relevance scoring, no fuzzy matching)
- Redis pub/sub doesn't persist messages — if a viewer disconnects briefly, they miss entries
- AI summarization requires batching enough logs to be useful (min ~50 entries)

### Neutral
- Can add Elasticsearch/Meilisearch later as an optional secondary index if needed

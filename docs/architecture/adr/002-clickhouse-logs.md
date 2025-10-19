# ADR-002: Use ClickHouse for Log and Metric Storage

## Status

Accepted

## Context

Aegis needs to store and query large volumes of logs, metrics, and traces. The Log Explorer requires full-text search, time-range filtering, and real-time tail functionality. We need a solution that scales to petabytes while keeping query latency under 1 second for most operations.

We considered:
1. **ClickHouse** — Column-oriented OLAP database, open source
2. **Elasticsearch/OpenSearch** — Full-text search engine, widely used for logs
3. **Loki** — Grafana's log aggregation system
4. **SigNoz's ClickHouse** — Reuse the existing SigNoz ClickHouse instance

## Decision

We chose **ClickHouse** as the primary log/metric storage engine.

Key factors:
- **SigNoz compatibility**: SigNoz (our primary monitoring tool at acme-corp) uses ClickHouse internally. We can either share the same cluster or use a compatible schema, enabling zero-duplication data ingestion.
- **Performance**: ClickHouse processes billions of rows per second for analytical queries. 10-100x faster than Elasticsearch for time-series aggregations.
- **Compression**: ClickHouse achieves 10-20x compression ratios, significantly reducing storage costs.
- **SQL interface**: Standard SQL queries (with extensions) are easier to learn than Elasticsearch's DSL.
- **Cost**: Self-hosted ClickHouse is significantly cheaper than Elasticsearch at scale.

## Consequences

### Positive

- Excellent query performance for time-series log data
- Compatible with SigNoz's internal storage
- Lower storage costs due to superior compression
- SQL interface is familiar to most engineers
- Handles petabyte-scale data

### Negative

- Not as strong for full-text search as Elasticsearch (mitigated by tokenized columns + bloom filter indexes)
- Fewer managed cloud offerings compared to Elasticsearch
- Less mature ecosystem for log management specifically

### Neutral

- We still support ingesting from Elasticsearch/Loki via OpenTelemetry, so users aren't locked in

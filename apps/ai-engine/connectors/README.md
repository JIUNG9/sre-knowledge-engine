# connectors — SigNoz (Layer 2A)

Async Python client for the [SigNoz](https://signoz.io) query-service REST
API. This module is Aegis's default telemetry backend adapter: every
analyzer, investigator, or wiki synthesiser that needs observability
data goes through these fetchers instead of hitting SigNoz directly.

## Usage

```python
from datetime import datetime, timedelta
from connectors import (
    SigNozClient, SigNozConnectorConfig,
    LogFetcher, MetricFetcher, TraceFetcher, AlertFetcher,
)

cfg = SigNozConnectorConfig()  # reads AEGIS_SIGNOZ_* env vars
async with SigNozClient.from_config(cfg) as client:
    end = datetime.utcnow()
    start = end - timedelta(minutes=15)

    logs    = await LogFetcher(client).search("severity=ERROR", start, end)
    metrics = await MetricFetcher(client).query_range(
        'rate(http_requests_total[1m])', start, end, step_seconds=30,
    )
    traces  = await TraceFetcher(client).search(
        service="gateway", operation=None, min_duration_ms=200,
        start=start, end=end,
    )
    firing  = await AlertFetcher(client).list_alerts(state="firing")
```

## Endpoints covered

| Method   | Path                              | Fetcher         |
| -------- | --------------------------------- | --------------- |
| `GET`    | `/api/v1/logs`                    | `LogFetcher`    |
| `GET`    | `/api/v1/query_range`             | `MetricFetcher` |
| `GET`    | `/api/v1/traces`                  | `TraceFetcher`  |
| `GET`    | `/api/v1/traces/{trace_id}`       | `TraceFetcher`  |
| `GET`    | `/api/v1/rules`                   | `AlertFetcher`  |
| `GET`    | `/api/v1/rules/{id}/history`      | `AlertFetcher`  |
| `GET`    | `/api/v1/alerts`                  | `AlertFetcher`  |

## Authentication

When `AEGIS_SIGNOZ_API_KEY` is set, requests carry an
`Authorization: Bearer <token>` header. Without it the client emits no
auth header — matching unauthenticated self-hosted SigNoz stacks.

## Retries & errors

Transient failures (HTTP 429/5xx, timeouts, connection errors) are
retried with exponential backoff up to `AEGIS_SIGNOZ_RETRY_ATTEMPTS`.
All non-2xx responses are normalised into `SigNozError`, which carries
the HTTP status, method, URL, a truncated body, and the per-request
UUID for log correlation. Errors are never silently swallowed.

## Mock mode

Setting `use_mock=True` on `SigNozConnectorConfig` — or in env via
`AEGIS_SIGNOZ_USE_MOCK=true` — installs an in-process
`httpx.MockTransport` that answers every endpoint with canned JSON.
No network sockets are opened; offline CI is fully supported.

## Tests

```bash
cd apps/ai-engine
pip install -e '.[test]'
pytest connectors/tests
```

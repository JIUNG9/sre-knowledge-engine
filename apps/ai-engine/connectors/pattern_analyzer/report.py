"""
Report builder — turn an AnalysisResult into (a) machine-readable JSON and
(b) a compact markdown summary designed to be pasted into a Claude prompt.

Markdown budget target: ~1500 tokens. We stay well under that by:
    * capping lists at sensible top-N
    * one-line-per-finding format
    * skipping sections with no signal

Two outputs are returned from a single call so callers choose their
integration surface.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .analyzer import AnalysisResult

_WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _pct(n: int, total: int) -> str:
    if total == 0:
        return "0%"
    return f"{(n / total) * 100:.1f}%"


def _json_safe(obj: Any) -> Any:
    """Recursively coerce dataclasses / datetimes / sets into JSON-safe types."""
    import datetime as _dt

    if hasattr(obj, "__dataclass_fields__"):
        return {k: _json_safe(v) for k, v in asdict(obj).items()}
    if isinstance(obj, _dt.datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_json_safe(v) for v in obj]
    return obj


def _format_markdown(result: AnalysisResult) -> str:
    lines: list[str] = []
    tp = result.time_pattern
    total = result.total_events

    lines.append(f"# Pattern Analysis ({total} events)")
    lines.append("")

    # Severity
    if result.severity_counts:
        sev_parts = [
            f"{sev}={n} ({_pct(n, total)})"
            for sev, n in sorted(
                result.severity_counts.items(), key=lambda x: -x[1]
            )
        ]
        lines.append(f"**Severity mix:** {', '.join(sev_parts)}")
        lines.append("")

    # Time headline
    if tp.total_events > 0 and tp.dominant_weekday is not None:
        dow_name = _WEEKDAY_NAMES[tp.dominant_weekday]
        lines.append(
            f"**Time concentration:** {tp.weekday_share * 100:.1f}% of events on "
            f"**{dow_name}**, peak hour **{tp.dominant_hour:02d}:00 UTC** "
            f"({tp.hour_share * 100:.1f}% of all events)."
        )
        if tp.hotspots:
            lines.append("**Top (weekday, hour) hotspots:**")
            for d, h, c in tp.hotspots[:5]:
                lines.append(
                    f"- {_WEEKDAY_NAMES[d]} {h:02d}:00 — {c} events ({_pct(c, total)})"
                )
        lines.append("")

    # Week-over-week
    if result.week_anomalies:
        lines.append("**Week-over-week anomalies:**")
        for a in result.week_anomalies[:5]:
            lines.append(
                f"- Week of {a.week_start.date().isoformat()}: "
                f"{a.direction} — {a.count} events (z={a.z_score:+.2f}, "
                f"baseline μ={a.baseline_mean:.1f})"
            )
        lines.append("")

    # Bursts
    if result.bursts:
        lines.append(f"**Bursts detected:** {len(result.bursts)}")
        for b in result.bursts[:5]:
            lines.append(
                f"- {b.start.isoformat(timespec='seconds')} → "
                f"{b.end.isoformat(timespec='seconds')}: "
                f"{b.count} events (z={b.z_score:+.2f})"
            )
        lines.append("")

    # Message clusters
    if result.message_clusters:
        lines.append("**Top recurring message templates:**")
        for c in result.message_clusters[:8]:
            tmpl = c.template if len(c.template) <= 120 else c.template[:117] + "..."
            lines.append(f"- [{c.count}×] `{tmpl}`")
        lines.append("")

    # Correlation
    cg = result.correlation_graph
    if cg.edges:
        lines.append(
            f"**Service correlations** (window={cg.window_seconds}s, "
            f"top {min(8, len(cg.edges))} of {len(cg.edges)}):"
        )
        for e in cg.top_pairs(8):
            lines.append(
                f"- `{e.source}` → `{e.target}` "
                f"(score={e.score:.2f}, co-fires={e.co_count}, "
                f"src_fires={e.source_count})"
            )
        lines.append("")

    lines.append(f"_Trace coverage: {result.trace_coverage * 100:.1f}%_")
    return "\n".join(lines)


def build_analysis_report(result: AnalysisResult) -> dict:
    """Return `{"json": <serialisable dict>, "markdown": <str>}`.

    The markdown is prompt-ready for Claude; the JSON is for dashboards and
    regression tests.
    """
    return {
        "json": _json_safe(result),
        "markdown": _format_markdown(result),
    }

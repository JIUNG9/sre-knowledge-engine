"""Tests for ``killswitch.gate.killswitch_gate``."""

from __future__ import annotations

import asyncio
from pathlib import Path

import fakeredis
import pytest

from killswitch.config import KillSwitchConfig
from killswitch.gate import KillSwitchTripped, killswitch_gate, set_killswitch
from killswitch.switch import KillSwitch


@pytest.fixture
def switch(tmp_path: Path) -> KillSwitch:
    cfg = KillSwitchConfig(
        backend="redis",
        audit_log_path=tmp_path / "audit.jsonl",
        file_backend_path=tmp_path / "ks.flag",
    )
    client = fakeredis.FakeRedis(decode_responses=True)
    ks = KillSwitch.with_redis_client(client, cfg)
    yield ks
    set_killswitch(None)


def test_sync_gate_allows_when_clear(switch: KillSwitch) -> None:
    @killswitch_gate(switch)
    def tool(x: int) -> int:
        return x * 2

    assert tool(21) == 42


def test_sync_gate_blocks_when_tripped(switch: KillSwitch) -> None:
    @killswitch_gate(switch, tool_name="kubectl_action")
    def tool() -> str:
        return "side effect"

    switch.trip(reason="p0 incident", operator="june.gu")
    with pytest.raises(KillSwitchTripped) as excinfo:
        tool()
    assert excinfo.value.status.active is True
    assert excinfo.value.status.operator == "june.gu"
    assert excinfo.value.status.reason == "p0 incident"
    assert "p0 incident" in str(excinfo.value)


def test_async_gate_blocks_before_await(switch: KillSwitch) -> None:
    executed = {"value": False}

    @killswitch_gate(switch)
    async def tool() -> str:
        executed["value"] = True
        return "ran"

    switch.trip(reason="hold", operator="op")
    with pytest.raises(KillSwitchTripped):
        asyncio.run(tool())
    assert executed["value"] is False, "tool body must NOT run when tripped"


def test_async_gate_allows_when_clear(switch: KillSwitch) -> None:
    @killswitch_gate(switch)
    async def tool(x: int) -> int:
        return x + 1

    result = asyncio.run(tool(1))
    assert result == 2


def test_gate_uses_process_wide_switch_by_default(switch: KillSwitch) -> None:
    set_killswitch(switch)

    @killswitch_gate()  # no explicit switch arg
    def tool() -> str:
        return "ok"

    assert tool() == "ok"
    switch.trip(reason="fleet-wide", operator="pagerduty")
    with pytest.raises(KillSwitchTripped):
        tool()


def test_gate_preserves_wrapped_function_metadata(switch: KillSwitch) -> None:
    @killswitch_gate(switch)
    def query_logs(service: str) -> str:
        """Query logs from SigNoz."""
        return service

    assert query_logs.__name__ == "query_logs"
    assert query_logs.__doc__ == "Query logs from SigNoz."

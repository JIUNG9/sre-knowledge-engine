"""Tests for the ``aegis`` Typer CLI (panic/status/release)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import fakeredis
import pytest
from typer.testing import CliRunner

from cli.main import app
from killswitch import gate as gate_module
from killswitch.config import KillSwitchConfig
from killswitch.switch import KillSwitch


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def cli_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point the CLI's default config at a tmp audit log + flag file."""
    monkeypatch.setenv(
        "AEGIS_KILLSWITCH_AUDIT_LOG_PATH", str(tmp_path / "audit.jsonl")
    )
    monkeypatch.setenv(
        "AEGIS_KILLSWITCH_FILE_BACKEND_PATH", str(tmp_path / "ks.flag")
    )
    monkeypatch.setenv("AEGIS_KILLSWITCH_BACKEND", "redis")
    yield tmp_path
    gate_module.set_killswitch(None)


@pytest.fixture
def fake_switch(cli_env: Path):
    """Patch ``cli.panic._build_switch`` to return a fakeredis-backed switch."""
    cfg = KillSwitchConfig(
        backend="redis",
        audit_log_path=cli_env / "audit.jsonl",
        file_backend_path=cli_env / "ks.flag",
    )
    client = fakeredis.FakeRedis(decode_responses=True)
    switch = KillSwitch.with_redis_client(client, cfg)

    def _factory(redis_url, backend):  # noqa: ARG001
        return switch

    with patch("cli.panic._build_switch", new=_factory):
        yield switch


def test_panic_force_flags_trip_switch(
    runner: CliRunner, fake_switch: KillSwitch
) -> None:
    result = runner.invoke(
        app,
        [
            "panic",
            "--force",
            "--operator",
            "pagerduty",
            "--reason",
            "db-outage-p0",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "KILL SWITCH TRIPPED" in result.output
    assert "pagerduty" in result.output
    assert "db-outage-p0" in result.output
    assert fake_switch.is_active() is True


def test_panic_interactive_confirmation(
    runner: CliRunner, fake_switch: KillSwitch
) -> None:
    # Without --force the CLI prompts for the PANIC confirmation token first,
    # then operator + reason.
    result = runner.invoke(
        app,
        ["panic"],
        input="PANIC\njune.gu\ncompromised key\n",
    )
    assert result.exit_code == 0, result.output
    assert fake_switch.is_active() is True
    status = fake_switch.status()
    assert status.operator == "june.gu"
    assert status.reason == "compromised key"


def test_panic_wrong_confirm_token_aborts(
    runner: CliRunner, fake_switch: KillSwitch
) -> None:
    result = runner.invoke(app, ["panic"], input="nope\n")
    assert result.exit_code == 1
    assert fake_switch.is_active() is False


def test_status_reports_clear(runner: CliRunner, fake_switch: KillSwitch) -> None:
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "CLEAR" in result.output


def test_status_reports_active_with_nonzero_exit(
    runner: CliRunner, fake_switch: KillSwitch
) -> None:
    fake_switch.trip(reason="manual", operator="june.gu")
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 1
    assert "ACTIVE" in result.output
    assert "june.gu" in result.output


def test_status_json_output(runner: CliRunner, fake_switch: KillSwitch) -> None:
    fake_switch.trip(reason="debug", operator="june.gu")
    result = runner.invoke(app, ["status", "--json"])
    assert result.exit_code == 1
    assert '"active": true' in result.output
    assert '"operator": "june.gu"' in result.output


def test_release_requires_confirmation(
    runner: CliRunner, fake_switch: KillSwitch
) -> None:
    fake_switch.trip(reason="test", operator="june.gu")
    # Decline the confirmation -> still active.
    result = runner.invoke(
        app, ["release", "--operator", "june.gu"], input="n\n"
    )
    assert result.exit_code == 1
    assert fake_switch.is_active() is True

    result = runner.invoke(
        app, ["release", "--operator", "june.gu", "--force"]
    )
    assert result.exit_code == 0
    assert "RELEASED" in result.output
    assert fake_switch.is_active() is False


def test_panic_with_revoke_aws_calls_revoker(
    runner: CliRunner, fake_switch: KillSwitch
) -> None:
    with patch("cli.panic.revoke_aws_session") as mock_revoke:
        mock_revoke.return_value = {
            "role_arn": "arn:aws:iam::123456789012:role/aegis-agent",
            "role_name": "aegis-agent",
            "policy_name": "AWSRevokeOlderSessions",
            "issued_before": "2026-04-21T00:00:00+00:00",
            "idempotent": True,
        }
        result = runner.invoke(
            app,
            [
                "panic",
                "--force",
                "--operator",
                "june.gu",
                "--reason",
                "leaked-key",
                "--revoke-aws",
                "--aws-role-arn",
                "arn:aws:iam::123456789012:role/aegis-agent",
            ],
        )
    assert result.exit_code == 0, result.output
    mock_revoke.assert_called_once_with(
        "arn:aws:iam::123456789012:role/aegis-agent"
    )
    assert "AWS session revoked" in result.output


def test_panic_revoke_without_role_arn_warns(
    runner: CliRunner, fake_switch: KillSwitch
) -> None:
    result = runner.invoke(
        app,
        [
            "panic",
            "--force",
            "--operator",
            "june.gu",
            "--reason",
            "no-arn-test",
            "--revoke-aws",
        ],
    )
    # Trip still succeeds; AWS revoke is skipped with a warning.
    assert result.exit_code == 0
    assert "no role ARN configured" in result.output
    assert fake_switch.is_active() is True


def test_aws_revoke_unit_idempotent() -> None:
    """Unit-test the revocation helper with a mock boto3 client."""
    from killswitch.aws_revoke import revoke_aws_session

    calls = []

    class FakeIam:
        def put_role_policy(self, **kwargs):
            calls.append(kwargs)

    role = "arn:aws:iam::123456789012:role/aegis-agent"
    first = revoke_aws_session(role, iam_client=FakeIam())
    second = revoke_aws_session(role, iam_client=FakeIam())

    assert first["role_name"] == "aegis-agent"
    assert first["policy_name"] == "AWSRevokeOlderSessions"
    assert second["idempotent"] is True
    assert len(calls) == 2  # put_role_policy called on each invocation
    assert calls[0]["PolicyName"] == "AWSRevokeOlderSessions"
    assert calls[0]["RoleName"] == "aegis-agent"

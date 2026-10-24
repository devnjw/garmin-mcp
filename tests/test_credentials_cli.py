import json
import os
import subprocess
import sys
from unittest.mock import MagicMock

import pytest

from garmin_mcp import cli
from garmin_mcp.credentials import KEY_ENV, EnvironmentCredentials
from garmin_mcp.errors import Fault
from garmin_mcp.gateway import Gateway
from garmin_mcp.service import Service


def test_environment_key_is_read_without_persistence_and_updates(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    store = EnvironmentCredentials()
    assert store.get() is None
    monkeypatch.setenv(KEY_ENV, "synthetic-first")
    assert store.get() == "synthetic-first"
    monkeypatch.setenv(KEY_ENV, "synthetic-second")
    assert store.get() == "synthetic-second"
    monkeypatch.delenv(KEY_ENV)
    assert store.get() is None
    assert list(tmp_path.iterdir()) == []


def test_dotenv_is_not_implicitly_loaded(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(f"{KEY_ENV}=synthetic-secret\n")
    assert EnvironmentCredentials().get() is None


@pytest.mark.parametrize(
    "key", [" ", "secret\n", "secret\r", "\tsecret", "secret key", "비밀", "x" * 4097, "secret\x7f"]
)
def test_invalid_environment_key_is_rejected_before_authentication(monkeypatch, key):
    monkeypatch.setenv(KEY_ENV, key)
    authenticator = MagicMock()
    gateway = Gateway(authenticator=authenticator)
    with pytest.raises(Fault) as error:
        gateway.call(lambda client: None)
    assert error.value.code == "invalid_api_key"
    assert "secret" not in str(error.value)
    authenticator.obtain_token.assert_not_called()


def test_empty_environment_key_is_missing(monkeypatch):
    monkeypatch.setenv(KEY_ENV, "")
    assert EnvironmentCredentials().get() is None


def test_status_discloses_source_but_not_key(monkeypatch):
    monkeypatch.setenv(KEY_ENV, "synthetic-never-print-this")
    gateway = MagicMock(store=EnvironmentCredentials())
    result = Service(gateway).execute("status")
    assert result["ok"] and result["data"]["key_configured"]
    assert result["data"]["credential_environment_variable"] == KEY_ENV
    assert "synthetic-never-print-this" not in json.dumps(result)
    gateway.call.assert_not_called()


def test_check_without_key_has_safe_actionable_failure(capsys):
    assert cli.check_connection() == 1
    result = json.loads(capsys.readouterr().out)
    assert result["authenticated"] is False
    assert result["error"]["code"] == "not_authenticated"
    assert KEY_ENV in result["error"]["message"]


def test_check_prints_only_statuses_and_counts(monkeypatch, capsys):
    fake = MagicMock()
    fake.execute.side_effect = [
        {"ok": True},
        *[{"ok": True, "status": "partial", "data": [{"private": "never-print"}]}] * 5,
    ]
    monkeypatch.setattr(cli, "Service", lambda: fake)
    assert cli.check_connection() == 0
    output = capsys.readouterr().out
    assert "never-print" not in output
    assert all(v["record_count"] == 1 for v in json.loads(output)["checks"].values())
    fake.gateway.close.assert_called_once()


def test_check_reports_failed_summary_and_closes_gateway(monkeypatch, capsys):
    fake = MagicMock()
    fake.execute.side_effect = [
        {"ok": True},
        *[{"ok": False, "status": "error", "error": {"code": "rate_limited"}}] * 5,
    ]
    monkeypatch.setattr(cli, "Service", lambda: fake)
    assert cli.check_connection() == 1
    assert json.loads(capsys.readouterr().out)["authenticated"]
    fake.gateway.close.assert_called_once()


def test_cli_help_and_missing_key_work_without_interactive_auth():
    env = {k: v for k, v in os.environ.items() if k != KEY_ENV}
    help_result = subprocess.run(
        [sys.executable, "-m", "garmin_mcp.cli", "--help"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "{serve,check}" in help_result.stdout
    result = subprocess.run(
        [sys.executable, "-m", "garmin_mcp.cli", "check"],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 1
    assert json.loads(result.stdout)["error"]["code"] == "not_authenticated"
    assert "Traceback" not in result.stderr

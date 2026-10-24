import hashlib
import io
import json
import stat
import sys
import zipfile

import pytest

from garmin_mcp import downloads
from garmin_mcp.api import ApiService
from garmin_mcp.errors import Fault


def archive():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as output:
        output.writestr("../never-extract.fit", b"synthetic activity")
    return stream.getvalue()


def test_download_endpoint_uses_sdk_and_creates_private_unique_unextracted_archives(
    tmp_path, monkeypatch, make_service
):
    monkeypatch.setattr(downloads, "data_directory", lambda: tmp_path)
    payload = archive()
    service, session, _ = make_service({"/download-service/files/activity/42": payload})
    first = ApiService(service.gateway).execute("download_activity", activity_id=42)
    second = ApiService(service.gateway).execute("download_activity", activity_id=42)
    assert first["ok"] and second["ok"]
    from pathlib import Path

    path = Path(first["data"]["path"])
    assert path != Path(second["data"]["path"])
    assert path.read_bytes() == payload
    if sys.platform != "win32":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    assert first["data"]["sha256"] == hashlib.sha256(payload).hexdigest()
    assert first["data"]["extracted"] is False
    assert not (tmp_path / "never-extract.fit").exists()
    assert len(session.calls) == 2
    assert "synthetic activity" not in json.dumps(first)


def test_download_directory_symlink_is_rejected(tmp_path, monkeypatch):
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (tmp_path / "downloads").symlink_to(outside, target_is_directory=True)
    except OSError:
        if sys.platform == "win32":
            pytest.skip(
                "Creating Windows symlinks requires developer mode or privilege; junction test still runs"
            )
        raise
    monkeypatch.setattr(downloads, "data_directory", lambda: tmp_path)
    with pytest.raises(Fault) as error:
        downloads.save_activity(archive(), 42)
    assert error.value.code == "download_write_failed"
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("content", [b"", b"not a zip", b"<html>private upstream error</html>"])
def test_invalid_download_does_not_create_a_file(tmp_path, monkeypatch, content):
    monkeypatch.setattr(downloads, "data_directory", lambda: tmp_path)
    with pytest.raises(Fault) as error:
        downloads.save_activity(content, 42)
    assert error.value.code == "invalid_download"
    assert not (tmp_path / "downloads").exists()


def test_download_size_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(downloads, "MAX_DOWNLOAD_BYTES", 2)
    monkeypatch.setattr(downloads, "data_directory", lambda: tmp_path)
    with pytest.raises(Fault) as error:
        downloads.save_activity(archive(), 42)
    assert error.value.code == "invalid_download"


def test_failed_download_write_removes_only_created_file(tmp_path, monkeypatch):
    import os
    from pathlib import Path

    monkeypatch.setattr(downloads, "data_directory", lambda: tmp_path)
    original_fdopen = os.fdopen
    original_open = Path.open

    class BrokenWriter:
        def __init__(self, file):
            self.file = file

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.file.close()

        def write(self, content):
            self.file.write(content[:10])
            raise OSError("synthetic private disk error")

    monkeypatch.setattr(os, "fdopen", lambda *a, **k: BrokenWriter(original_fdopen(*a, **k)))
    monkeypatch.setattr(Path, "open", lambda *a, **k: BrokenWriter(original_open(*a, **k)))
    with pytest.raises(Fault) as error:
        downloads.save_activity(archive(), 42)
    assert error.value.code == "download_write_failed"
    assert "private disk error" not in str(error.value)
    assert list((tmp_path / "downloads").iterdir()) == []


@pytest.mark.skipif(sys.platform != "win32", reason="Windows junction and ACL verification")
def test_windows_junction_is_rejected(tmp_path, monkeypatch):
    import subprocess

    outside = tmp_path / "outside"
    outside.mkdir()
    junction = tmp_path / "downloads"
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(outside)], check=True, capture_output=True
    )
    try:
        monkeypatch.setattr(downloads, "data_directory", lambda: tmp_path)
        with pytest.raises(Fault) as error:
            downloads.save_activity(archive(), 42)
        assert error.value.code == "download_write_failed"
        assert list(outside.iterdir()) == []
    finally:
        junction.rmdir()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows ACL verification")
def test_windows_download_has_private_acl_even_in_existing_broad_directory(tmp_path, monkeypatch):
    import os
    import shutil
    import subprocess
    from pathlib import Path

    root = tmp_path / "downloads"
    root.mkdir()
    monkeypatch.setattr(downloads, "data_directory", lambda: tmp_path)
    result = downloads.save_activity(archive(), 42)
    path = Path(result["path"])
    # Inspect real Windows security descriptors, not POSIX mode bits on Windows.
    script = r"""
    $ErrorActionPreference = 'Stop'
    $sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $acl = Get-Acl -LiteralPath $env:GARMIN_TEST_ACL_PATH
    $allowed = @($acl.Access | Where-Object { $_.AccessControlType -eq 'Allow' } |
        ForEach-Object { $_.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value })
    @{ allowed = $allowed; user = $sid; owner = $acl.GetOwner([System.Security.Principal.SecurityIdentifier]).Value } | ConvertTo-Json -Compress
    """
    for target in (path, path.parent):
        checked = subprocess.run(
            [
                shutil.which("pwsh") or "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                script,
            ],
            env={**os.environ, "GARMIN_TEST_ACL_PATH": str(target)},
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        assert checked.returncode == 0, checked.stderr
        acl = json.loads(checked.stdout)
        # CPython may grant OWNER RIGHTS rather than spell out the user's SID.
        # Verify the actual owner before accepting that well-known trustee.
        assert acl["owner"] in {acl["user"], "S-1-5-32-544"}
        assert acl["user"] in acl["allowed"] or "S-1-3-4" in acl["allowed"]
        assert set(acl["allowed"]) <= {acl["user"], "S-1-5-32-544", "S-1-5-18", "S-1-3-4"}

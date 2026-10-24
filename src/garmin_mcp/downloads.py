import hashlib
import io
import os
import sys
import uuid
import zipfile

from .errors import Fault
from .settings import data_directory

MAX_DOWNLOAD_BYTES = 64 * 1024 * 1024


def _save_windows(root, name, content):
    # Python >=3.12.4 implements mkdir(0700) using a protected Windows ACL.
    # Always create a fresh directory: an existing directory may have wider ACLs.
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if root.is_symlink() or root.is_junction():
        raise OSError("Linked download directories are not allowed")
    private = root / uuid.uuid4().hex
    private.mkdir(mode=0o700)
    path = private / name
    created = False
    try:
        with path.open("xb") as output:
            created = True
            output.write(content)
        return path
    except OSError:
        if created:
            path.unlink(missing_ok=True)
        private.rmdir()
        raise


def save_activity(content, activity_id):
    if not isinstance(content, bytes) or not content or len(content) > MAX_DOWNLOAD_BYTES:
        raise Fault(
            "invalid_download", "The activity download is empty or exceeds the 64 MiB limit."
        )
    if not zipfile.is_zipfile(io.BytesIO(content)):
        raise Fault("invalid_download", "Garmin did not return an activity ZIP archive.")
    root = data_directory() / "downloads"
    name = f"activity-{activity_id}-{uuid.uuid4().hex}.zip"
    directory_fd = None
    created = False
    try:
        if sys.platform == "win32":
            path = _save_windows(root, name, content)
        else:
            root.mkdir(parents=True, exist_ok=True, mode=0o700)
            directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            os.fchmod(directory_fd, 0o700)
            fd = os.open(
                name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory_fd,
            )
            created = True
            with os.fdopen(fd, "wb") as output:
                output.write(content)
            path = root / name
        return {
            "path": str(path),
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "media_type": "application/zip",
            "extracted": False,
        }
    except OSError:
        if created:
            try:
                os.unlink(name, dir_fd=directory_fd)
            except OSError:
                pass
        raise Fault(
            "download_write_failed",
            "Could not save the ZIP in the private Garmin MCP downloads directory.",
        ) from None
    finally:
        if directory_fd is not None:
            os.close(directory_fd)

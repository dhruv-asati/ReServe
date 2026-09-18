"""
Low-level file storage backend for ReServe uploads.

This module knows how to store and delete bytes on a backend, and nothing
else — no auth, no ownership checks, no HTTP concerns. That logic lives in
app/services/upload_service.py, which is what app/api/uploads.py calls.
Keeping the two separate means the route layer, the "is this upload
allowed" business rules, and the "where do bytes actually live" mechanics
can each change independently.

Two backends are supported, chosen automatically per call:

- Supabase Storage, used whenever SUPABASE_URL and SUPABASE_KEY are both
  set (see app/core/config.py).
- Local disk, used otherwise. Files are written under LOCAL_UPLOAD_DIR and
  served back via the /static/uploads/ route mounted in app/main.py. This
  is what makes uploads work out of the box in local development with no
  Supabase project configured at all.

Callers never branch on which backend is active themselves — upload_file()
and delete_file() decide that internally, purely from configuration.

Note on switching backends mid-lifecycle: which backend deleted a file is
inferred from the *current* configuration, not from how it was originally
stored. Uploading locally, then adding Supabase credentials and trying to
delete the same file later, won't find it. That's an acceptable trade-off
for a project this size — a production system with real backend migrations
would want to record the storage backend per uploaded file.
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.errors import AppError

logger = logging.getLogger(__name__)

# Extension -> canonical Content-Type, for the image formats this app
# accepts. Keyed by the extension sniff_image_extension() returns.
CONTENT_TYPE_BY_EXTENSION = {
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def sniff_image_extension(data: bytes) -> Optional[str]:
    """
    Identifies an image format from its actual bytes (magic numbers),
    never from the client-supplied Content-Type header or filename —
    both are trivial to spoof (e.g. renaming a script to photo.jpg).
    Returns one of the keys in CONTENT_TYPE_BY_EXTENSION, or None if the
    bytes don't match any accepted image format.
    """
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return None


async def read_limited(file: UploadFile, max_bytes: int) -> bytes:
    """
    Reads an UploadFile in chunks, raising as soon as the total exceeds
    max_bytes instead of buffering an arbitrarily large upload into memory
    first (a client claiming a small Content-Length and then streaming
    gigabytes shouldn't be able to exhaust server memory).
    """
    chunks: list[bytes] = []
    total = 0
    chunk_size = 1024 * 1024

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            await file.close()
            raise AppError(
                status_code=413,
                code="FILE_TOO_LARGE",
                message=f"File exceeds the {max_bytes // (1024 * 1024)}MB upload limit.",
            )
        chunks.append(chunk)

    await file.close()

    if total == 0:
        raise AppError(status_code=422, code="EMPTY_FILE", message="Uploaded file is empty.")

    return b"".join(chunks)


def is_supabase_configured() -> bool:
    settings = get_settings()
    return bool(settings.SUPABASE_URL and settings.SUPABASE_KEY)


@lru_cache
def _get_supabase_client():
    # Imported lazily so an environment that never configures Supabase
    # (local-disk-only) doesn't need a working `supabase` install to boot.
    from supabase import create_client

    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def _local_upload_dir() -> Path:
    path = Path(get_settings().LOCAL_UPLOAD_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def upload_file(file_id: str, content: bytes, content_type: str) -> str:
    """Stores `content` under `file_id` and returns a URL it can be fetched
    from. Picks Supabase Storage if configured, else local disk."""
    if is_supabase_configured():
        return _upload_to_supabase(file_id, content, content_type)
    return _upload_to_local(file_id, content)


def delete_file(file_id: str) -> None:
    """Deletes a previously-stored file. Silently no-ops if it doesn't
    exist on the active backend — deleting something already gone isn't an
    error a client needs to see."""
    if is_supabase_configured():
        _delete_from_supabase(file_id)
    else:
        _delete_from_local(file_id)


def _upload_to_supabase(file_id: str, content: bytes, content_type: str) -> str:
    settings = get_settings()
    bucket = settings.SUPABASE_STORAGE_BUCKET
    client = _get_supabase_client()
    try:
        # Called with explicit keyword arguments (matching Supabase's own
        # Python examples) rather than positionally — storage3's `upload`
        # takes `path` and `file` and different client versions have not
        # been perfectly consistent about which comes first positionally.
        client.storage.from_(bucket).upload(
            path=file_id,
            file=content,
            file_options={"content-type": content_type, "upsert": "false"},
        )
        public_url = client.storage.from_(bucket).get_public_url(file_id)
        # supabase-py has returned either a plain string or a
        # {"publicUrl": "..."} / {"data": {"publicUrl": "..."}}-shaped dict
        # across versions — normalize defensively instead of assuming one.
        if isinstance(public_url, dict):
            public_url = public_url.get("publicUrl") or public_url.get("data", {}).get("publicUrl")
        return public_url
    except Exception:
        logger.exception("Supabase upload failed for %s", file_id)
        raise AppError(
            status_code=502,
            code="STORAGE_UPLOAD_FAILED",
            message="Could not upload the file to storage. Please try again.",
        )


def _delete_from_supabase(file_id: str) -> None:
    settings = get_settings()
    bucket = settings.SUPABASE_STORAGE_BUCKET
    client = _get_supabase_client()
    try:
        client.storage.from_(bucket).remove([file_id])
    except Exception:
        logger.exception("Supabase delete failed for %s", file_id)
        raise AppError(
            status_code=502,
            code="STORAGE_DELETE_FAILED",
            message="Could not delete the file from storage. Please try again.",
        )


def _upload_to_local(file_id: str, content: bytes) -> str:
    settings = get_settings()
    dest = _local_upload_dir() / file_id
    dest.write_bytes(content)
    logger.info("Stored upload locally at %s (Supabase not configured)", dest)
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    return f"{base}/static/uploads/{file_id}"


def _delete_from_local(file_id: str) -> None:
    dest = _local_upload_dir() / file_id
    dest.unlink(missing_ok=True)

"""
Upload service: validation and business rules for POST/DELETE
/api/uploads, kept separate from both the router (HTTP concerns) and
storage_service (raw storage I/O).

Ownership model: rather than a database table tracking every uploaded
file, each file's owner is encoded directly in its file_id
(`<owner_id_hex>__<random_hex>.<ext>`). Deleting a file just means
checking that prefix against the caller's own id (or ADMIN) — no extra
table to keep in sync with the resources that end up referencing the
resulting URL.
"""

import logging
import re
import uuid

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.errors import AppError
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.upload import UploadedFileOut
from app.services import storage_service

logger = logging.getLogger(__name__)

# <32 hex chars>__<32 hex chars>.<ext> — matched strictly before a file_id
# is ever used to build a storage path/key, so a crafted id (e.g. one
# containing "../") can never reach the filesystem or the Supabase API.
_FILE_ID_PATTERN = re.compile(r"^[0-9a-f]{32}__[0-9a-f]{32}(\.jpg|\.png|\.gif|\.webp)$")


def _max_upload_size_bytes() -> int:
    return get_settings().MAX_UPLOAD_FILE_SIZE_MB * 1024 * 1024


async def upload_resource_image(file: UploadFile, current_user: User) -> UploadedFileOut:
    """
    Validates and stores an image for use as a resource's `image_url`.
    Restricted to PROVIDER/ADMIN accounts at the route level, matching who
    is allowed to create resources in the first place.
    """
    content = await storage_service.read_limited(file, _max_upload_size_bytes())

    extension = storage_service.sniff_image_extension(content)
    if extension is None:
        raise AppError(
            status_code=422,
            code="UNSUPPORTED_FILE_TYPE",
            message="Only JPEG, PNG, GIF, and WEBP images are allowed.",
        )

    content_type = storage_service.CONTENT_TYPE_BY_EXTENSION[extension]
    file_id = f"{current_user.id.hex}__{uuid.uuid4().hex}{extension}"

    url = storage_service.upload_file(file_id, content, content_type)

    logger.info("Resource image %s uploaded by user %s", file_id, current_user.id)
    return UploadedFileOut(file_id=file_id, url=url, content_type=content_type, size_bytes=len(content))


def delete_uploaded_file(file_id: str, current_user: User) -> None:
    """
    Deletes a previously-uploaded file. Only the user whose id is encoded
    in file_id (or an ADMIN) may delete it. An unrecognized/malformed
    file_id is reported as 404 rather than 400/422 — it never identified a
    real file, so there's nothing to distinguish from "doesn't exist".
    """
    match = _FILE_ID_PATTERN.match(file_id)
    if not match:
        raise AppError(status_code=404, code="FILE_NOT_FOUND", message="No such file.")

    owner_hex = file_id.split("__", 1)[0]
    if current_user.role != UserRole.ADMIN and owner_hex != current_user.id.hex:
        raise AppError(
            status_code=403,
            code="NOT_FILE_OWNER",
            message="You can only delete files you uploaded.",
        )

    storage_service.delete_file(file_id)
    logger.info("File %s deleted by user %s", file_id, current_user.id)

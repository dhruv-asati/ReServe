"""
Upload endpoints:

    POST   /api/uploads/resource-image
    DELETE /api/uploads/{file_id}

Uploading is restricted to PROVIDER and ADMIN roles, matching who may
create resources in the first place. Deleting is open to any
authenticated user, but the service layer only lets it succeed for the
file's own uploader (or an ADMIN) — see app/services/upload_service.py.

Storage itself (Supabase Storage, or local disk when Supabase isn't
configured) is handled entirely in app/services/storage_service.py; this
module only wires HTTP to the upload_service business logic.
"""

import logging

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.core.deps import get_current_user, require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.upload import UploadedFileOut
from app.services import upload_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/uploads", tags=["Uploads"])


@router.post(
    "/resource-image",
    response_model=SuccessResponse[UploadedFileOut],
    status_code=status.HTTP_201_CREATED,
    summary="Upload a resource image",
    description="Uploads an image (JPEG, PNG, GIF, or WEBP) to use as a resource's `image_url`. "
    "Only PROVIDER and ADMIN accounts may upload. The returned `url` can be passed straight into "
    "`image_url` on POST/PUT /api/resources. Stored in Supabase Storage if configured, otherwise "
    "on local disk for development.",
)
async def upload_resource_image(
    file: UploadFile = File(..., description="Image file. Max size is configurable server-side."),
    current_user: User = Depends(require_roles(UserRole.PROVIDER, UserRole.ADMIN)),
):
    result = await upload_service.upload_resource_image(file, current_user)
    return SuccessResponse(data=result, message="Image uploaded successfully.")


@router.delete(
    "/{file_id}",
    response_model=SuccessResponse[None],
    summary="Delete an uploaded file",
    description="Deletes a previously-uploaded file by its id. Only the user who uploaded it, "
    "or an ADMIN, may delete it. Deleting a file does not automatically clear it from any "
    "resource's `image_url` — update the resource separately if needed.",
)
def delete_uploaded_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
):
    upload_service.delete_uploaded_file(file_id, current_user)
    return SuccessResponse(data=None, message="File deleted successfully.")

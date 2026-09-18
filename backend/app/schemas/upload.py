"""Pydantic schemas for the file-upload endpoints."""

from pydantic import BaseModel


class UploadedFileOut(BaseModel):
    file_id: str
    url: str
    content_type: str
    size_bytes: int

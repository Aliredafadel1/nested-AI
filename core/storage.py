import hashlib
import io
from enum import StrEnum

from fastapi import HTTPException, UploadFile
from minio import Minio
from minio.error import S3Error

from core.config import settings


class Bucket(StrEnum):
    LISTING_PHOTOS = "listing-photos"
    CONTRACTS      = "contracts"
    AUDIO          = "audio"
    AVATARS        = "avatars"
    SFTP_UPLOADS   = "sftp-uploads"


# Max sizes per bucket (bytes)
BUCKET_MAX_SIZE: dict[Bucket, int] = {
    Bucket.LISTING_PHOTOS: 5 * 1024 * 1024,    # 5MB
    Bucket.CONTRACTS:      10 * 1024 * 1024,   # 10MB
    Bucket.AUDIO:          25 * 1024 * 1024,   # 25MB
    Bucket.AVATARS:        2 * 1024 * 1024,    # 2MB
    Bucket.SFTP_UPLOADS:   500 * 1024 * 1024,  # 500MB
}

# Magic bytes: (offset, expected_bytes)
MAGIC_BYTES: dict[str, list[tuple[int, bytes]]] = {
    "image/jpeg": [(0, b"\xff\xd8\xff")],
    "image/png":  [(0, b"\x89PNG\r\n\x1a\n")],
    "image/webp": [(0, b"RIFF"), (8, b"WEBP")],
    "application/pdf": [(0, b"%PDF")],
    "audio/webm": [(0, b"\x1a\x45\xdf\xa3")],
    "audio/mpeg": [(0, b"ID3"), (0, b"\xff\xfb")],
    "audio/wav":  [(0, b"RIFF")],
}

BUCKET_ALLOWED_TYPES: dict[Bucket, list[str]] = {
    Bucket.LISTING_PHOTOS: ["image/jpeg", "image/png", "image/webp"],
    Bucket.CONTRACTS:      ["application/pdf"],
    Bucket.AUDIO:          ["audio/webm", "audio/mpeg", "audio/wav"],
    Bucket.AVATARS:        ["image/jpeg", "image/png"],
    Bucket.SFTP_UPLOADS:   ["text/csv", "application/json", "application/pdf"],
}


def get_minio_client() -> Minio:
    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ROOT_USER,
        secret_key=settings.MINIO_ROOT_PASSWORD,
        secure=settings.MINIO_SECURE,
    )


def validate_magic_bytes(data: bytes, bucket: Bucket) -> str:
    """Validate file magic bytes. Returns detected content type. Raises 400 on failure."""
    allowed = BUCKET_ALLOWED_TYPES[bucket]
    for content_type in allowed:
        signatures = MAGIC_BYTES.get(content_type, [])
        if all(data[off: off + len(sig)] == sig for off, sig in signatures):
            return content_type
    raise HTTPException(status_code=400, detail="Invalid file type — magic bytes do not match allowed types.")


async def upload_file(
    file: UploadFile,
    bucket: Bucket,
    object_name: str,
    owner_id: int | None = None,
) -> str:
    """Validate and upload file to MinIO. Returns the object name (key)."""
    max_size = BUCKET_MAX_SIZE[bucket]
    data = await file.read()

    if len(data) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max {max_size // (1024 * 1024)}MB for this bucket.",
        )

    content_type = validate_magic_bytes(data, bucket)

    client = get_minio_client()
    try:
        client.put_object(
            bucket_name=bucket.value,
            object_name=object_name,
            data=io.BytesIO(data),
            length=len(data),
            content_type=content_type,
            metadata={"owner_id": str(owner_id)} if owner_id else {},
        )
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"Storage error: {e}") from e

    return object_name


def get_presigned_url(bucket: Bucket, object_name: str, expires_seconds: int = 900) -> str:
    """Generate presigned GET URL. Max 15 minutes for private buckets."""
    from datetime import timedelta
    client = get_minio_client()
    return client.presigned_get_object(
        bucket_name=bucket.value,
        object_name=object_name,
        expires=timedelta(seconds=min(expires_seconds, 900)),
    )


def get_public_url(bucket: Bucket, object_name: str) -> str:
    protocol = "https" if settings.MINIO_SECURE else "http"
    return f"{protocol}://{settings.MINIO_ENDPOINT}/{bucket.value}/{object_name}"


def md5_key(user_id: int, filename: str) -> str:
    return hashlib.md5(f"{user_id}:{filename}".encode()).hexdigest()

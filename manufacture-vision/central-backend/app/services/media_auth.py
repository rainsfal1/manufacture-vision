from datetime import timedelta

from minio import Minio

from app.core.config import settings


def generate_presigned_url(key: str) -> str:
    client = Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )
    # Raises S3Error with code "NoSuchKey" if object doesn't exist
    client.stat_object(settings.MINIO_BUCKET, key)
    url = client.presigned_get_object(
        settings.MINIO_BUCKET,
        key,
        expires=timedelta(seconds=settings.MEDIA_URL_EXPIRE_SECONDS),
    )
    
    if settings.MINIO_PUBLIC_ENDPOINT:
        url = url.replace(settings.MINIO_ENDPOINT, settings.MINIO_PUBLIC_ENDPOINT)
        
    return url

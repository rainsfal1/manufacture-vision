import time
from loguru import logger
from minio import Minio
from minio.error import S3Error


class MinIOUploader:
    """
    Uploads clip files to a MinIO bucket using the minio Python SDK.

    Retries up to 3 times with exponential backoff on failure.
    Returns a clip_ref dict on success, or None on permanent failure.
    """

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
    ):
        self.bucket = bucket
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info(f"MinIOUploader: created bucket '{self.bucket}'")
            else:
                logger.info(f"MinIOUploader: bucket '{self.bucket}' ready")
        except S3Error as e:
            logger.error(f"MinIOUploader: could not verify/create bucket: {e}")

    def upload(self, file_path: str, object_key: str) -> dict | None:
        """
        Uploads `file_path` to MinIO at `object_key`.
        Returns {'bucket': str, 'key': str} on success, None on failure.
        """
        for attempt in range(3):
            try:
                self.client.fput_object(self.bucket, object_key, file_path)
                logger.info(f"MinIOUploader: uploaded → {self.bucket}/{object_key}")
                return {"bucket": self.bucket, "key": object_key}
            except S3Error as e:
                logger.warning(f"MinIOUploader: attempt {attempt + 1}/3 failed: {e}")
                if attempt < 2:
                    time.sleep(2 ** attempt)  # 1s then 2s

        logger.error(f"MinIOUploader: permanent failure for {object_key}")
        return None

    def upload_bytes(self, object_key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        """
        Uploads raw bytes to MinIO at `object_key`. Used for snapshots.
        """
        import io
        try:
            self.client.put_object(
                self.bucket,
                object_key,
                io.BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
            logger.info(f"MinIOUploader: uploaded bytes → {self.bucket}/{object_key}")
        except S3Error as e:
            logger.error(f"MinIOUploader: upload_bytes failed for {object_key}: {e}")

from minio import Minio
import os
import io
from app.config import settings
import structlog

logger = structlog.get_logger()


class StorageClient:
    def __init__(self):
        endpoint = settings.minio_endpoint
        if "localhost" in endpoint and os.getenv("RUNNING_IN_DOCKER"):
            endpoint = endpoint.replace("localhost", "minio")

        self.client = Minio(
            endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self._buckets_ready = False

    def ensure_buckets(self):
        """Initialise buckets on first use — called explicitly on startup, not on import."""
        if self._buckets_ready:
            return
        buckets = [
            settings.minio_bucket_blueprints,
            settings.minio_bucket_documents,
            settings.minio_bucket_proposals,
            settings.minio_bucket_photos,
        ]
        for bucket in buckets:
            try:
                if not self.client.bucket_exists(bucket):
                    self.client.make_bucket(bucket)
                    logger.info("minio.bucket_created", bucket=bucket)
            except Exception as e:
                logger.error("minio.bucket_ensure_failed", bucket=bucket, error=str(e))
        self._buckets_ready = True

    def upload_file(self, bucket_name: str, object_name: str, data: io.BytesIO, length: int, content_type: str = "application/octet-stream") -> bool:
        try:
            self.client.put_object(bucket_name, object_name, data, length, content_type=content_type)
            return True
        except Exception as e:
            logger.error("minio.upload_failed", bucket=bucket_name, object=object_name, error=str(e))
            return False

    def delete_file(self, bucket_name: str, object_name: str) -> bool:
        try:
            self.client.remove_object(bucket_name, object_name)
            return True
        except Exception as e:
            logger.error("minio.delete_failed", bucket=bucket_name, object=object_name, error=str(e))
            return False

    def download_file(self, bucket_name: str, object_name: str) -> io.BytesIO | None:
        try:
            response = self.client.get_object(bucket_name, object_name)
            data = io.BytesIO(response.read())
            response.close()
            response.release_stream()
            return data
        except Exception as e:
            logger.error("minio.download_failed", bucket=bucket_name, object=object_name, error=str(e))
            return None


storage_client = StorageClient()

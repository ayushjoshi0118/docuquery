import os
from abc import ABC, abstractmethod
from typing import Optional
import boto3
from botocore.exceptions import ClientError
from docuquery.config import settings


class IStorageService(ABC):
    @abstractmethod
    def put_object(self, key: str, data: bytes, content_type: str = "application/pdf") -> None:
        pass

    @abstractmethod
    def get_object(self, key: str) -> bytes:
        pass

    @abstractmethod
    def delete_object(self, key: str) -> None:
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        pass


class S3StorageService(IStorageService):
    def __init__(self):
        self.endpoint_url = settings.S3_ENDPOINT_URL
        self.bucket = settings.S3_BUCKET_NAME
        self.client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION_NAME,
        )
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            try:
                self.client.create_bucket(Bucket=self.bucket)
            except Exception:
                pass

    def put_object(self, key: str, data: bytes, content_type: str = "application/pdf") -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    def get_object(self, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise FileNotFoundError(f"Storage key {key} not found")
            raise

    def delete_object(self, key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except ClientError:
            pass

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False


class FilesystemStorageService(IStorageService):
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = os.path.abspath(base_dir or settings.STORAGE_LOCAL_DIR)
        os.makedirs(self.base_dir, exist_ok=True)

    def _resolve_path(self, key: str) -> str:
        if not key or "\x00" in key:
            raise ValueError("Invalid storage key: null byte or empty key detected")
        safe_path = os.path.abspath(os.path.join(self.base_dir, key))
        try:
            common = os.path.commonpath([self.base_dir, safe_path])
        except ValueError:
            # Different drive letters or invalid relative root
            raise ValueError("Invalid storage key: path traversal detected")
        if common != self.base_dir:
            raise ValueError("Invalid storage key: path traversal detected")
        return safe_path

    def put_object(self, key: str, data: bytes, content_type: str = "application/pdf") -> None:
        path = self._resolve_path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)

    def get_object(self, key: str) -> bytes:
        path = self._resolve_path(key)
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {key}")
        with open(path, "rb") as f:
            return f.read()

    def delete_object(self, key: str) -> None:
        path = self._resolve_path(key)
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    def exists(self, key: str) -> bool:
        path = self._resolve_path(key)
        return os.path.exists(path)


_storage_instance: Optional[IStorageService] = None


def get_storage_service() -> IStorageService:
    global _storage_instance
    if _storage_instance is None:
        if settings.STORAGE_BACKEND.lower() == "filesystem":
            _storage_instance = FilesystemStorageService()
        else:
            try:
                _storage_instance = S3StorageService()
            except Exception:
                # If S3 is unreachable during local fallback, use filesystem storage
                _storage_instance = FilesystemStorageService()
    return _storage_instance

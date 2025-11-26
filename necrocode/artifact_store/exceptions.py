"""
Exception classes for Artifact Store.

Defines custom exceptions for artifact storage operations.
"""


class ArtifactStoreError(Exception):
    """Artifact Storeの基底例外クラス"""
    pass


class StorageError(ArtifactStoreError):
    """ストレージ操作の一般的なエラー"""
    pass


class ArtifactNotFoundError(ArtifactStoreError):
    """成果物が見つからない場合の例外"""
    
    def __init__(self, uri: str):
        self.uri = uri
        super().__init__(f"Artifact not found: {uri}")


class StorageFullError(ArtifactStoreError):
    """ストレージ容量不足の例外"""
    
    def __init__(self, message: str = "Storage capacity exceeded"):
        super().__init__(message)


class IntegrityError(ArtifactStoreError):
    """成果物の整合性エラー"""
    
    def __init__(self, uri: str, expected_checksum: str, actual_checksum: str):
        self.uri = uri
        self.expected_checksum = expected_checksum
        self.actual_checksum = actual_checksum
        super().__init__(
            f"Integrity check failed for {uri}: "
            f"expected {expected_checksum}, got {actual_checksum}"
        )


class PermissionError(ArtifactStoreError):
    """権限エラー"""
    
    def __init__(self, message: str):
        super().__init__(f"Permission denied: {message}")


class LockTimeoutError(ArtifactStoreError):
    """ロック取得タイムアウトエラー"""
    
    def __init__(self, uri: str, timeout: float):
        self.uri = uri
        self.timeout = timeout
        super().__init__(f"Failed to acquire lock for {uri} within {timeout}s")


class CompressionError(ArtifactStoreError):
    """圧縮/解凍エラー"""
    
    def __init__(self, message: str):
        super().__init__(f"Compression error: {message}")


class BackendError(ArtifactStoreError):
    """ストレージバックエンドエラー"""
    
    def __init__(self, backend_type: str, message: str):
        self.backend_type = backend_type
        super().__init__(f"{backend_type} backend error: {message}")

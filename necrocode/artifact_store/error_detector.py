"""
Error detector for Artifact Store operations.

Detects and classifies storage-related errors.
"""

import logging
from typing import Optional

from necrocode.artifact_store.exceptions import (
    StorageFullError,
    PermissionError as ArtifactPermissionError,
    StorageError,
)

logger = logging.getLogger(__name__)


class ErrorDetector:
    """
    エラー検出器
    
    ストレージ容量不足エラーや権限エラーを検出し、適切な例外を投げます。
    
    Requirements: 15.2, 15.3
    """
    
    # ストレージ容量不足を示すキーワード
    STORAGE_FULL_KEYWORDS = [
        "no space left",
        "disk full",
        "quota exceeded",
        "storage full",
        "insufficient storage",
        "out of space",
        "not enough space",
        "storage capacity",
    ]
    
    # 権限エラーを示すキーワード
    PERMISSION_KEYWORDS = [
        "permission denied",
        "access denied",
        "forbidden",
        "unauthorized",
        "not authorized",
        "insufficient permissions",
        "no permission",
        "access forbidden",
    ]
    
    # boto3のストレージ容量不足エラーコード
    S3_STORAGE_FULL_CODES = [
        "QuotaExceeded",
        "StorageFull",
    ]
    
    # boto3の権限エラーコード
    S3_PERMISSION_CODES = [
        "AccessDenied",
        "Forbidden",
        "InvalidAccessKeyId",
        "SignatureDoesNotMatch",
    ]
    
    # GCSのストレージ容量不足エラーコード
    GCS_STORAGE_FULL_CODES = [
        403,  # Quota exceeded
    ]
    
    # GCSの権限エラーコード
    GCS_PERMISSION_CODES = [
        401,  # Unauthorized
        403,  # Forbidden
    ]
    
    @classmethod
    def detect_storage_full_error(cls, error: Exception) -> bool:
        """
        ストレージ容量不足エラーかどうかを判定
        
        Args:
            error: 判定する例外
            
        Returns:
            ストレージ容量不足エラーの場合はTrue
            
        Requirements: 15.2
        """
        # 既にStorageFullErrorの場合
        if isinstance(error, StorageFullError):
            return True
        
        # エラーメッセージから判定
        error_message = str(error).lower()
        
        for keyword in cls.STORAGE_FULL_KEYWORDS:
            if keyword in error_message:
                logger.debug(f"Detected storage full error by keyword: {keyword}")
                return True
        
        # boto3のエラーコードから判定
        try:
            from botocore.exceptions import ClientError
            if isinstance(error, ClientError):
                error_code = error.response.get("Error", {}).get("Code", "")
                if error_code in cls.S3_STORAGE_FULL_CODES:
                    logger.debug(f"Detected S3 storage full error: {error_code}")
                    return True
        except ImportError:
            pass
        
        # GCSのエラーコードから判定
        try:
            from google.api_core.exceptions import GoogleAPIError
            if isinstance(error, GoogleAPIError):
                # QuotaExceededエラーをチェック
                if "quota" in error_message or "exceeded" in error_message:
                    logger.debug("Detected GCS storage full error")
                    return True
        except ImportError:
            pass
        
        # OSErrorのerrnoから判定 (ENOSPC: No space left on device)
        if isinstance(error, OSError):
            if hasattr(error, 'errno') and error.errno == 28:  # ENOSPC
                logger.debug("Detected filesystem storage full error (ENOSPC)")
                return True
        
        return False
    
    @classmethod
    def detect_permission_error(cls, error: Exception) -> bool:
        """
        権限エラーかどうかを判定
        
        Args:
            error: 判定する例外
            
        Returns:
            権限エラーの場合はTrue
            
        Requirements: 15.3
        """
        # 既にPermissionErrorの場合
        if isinstance(error, (ArtifactPermissionError, PermissionError)):
            return True
        
        # エラーメッセージから判定
        error_message = str(error).lower()
        
        for keyword in cls.PERMISSION_KEYWORDS:
            if keyword in error_message:
                logger.debug(f"Detected permission error by keyword: {keyword}")
                return True
        
        # boto3のエラーコードから判定
        try:
            from botocore.exceptions import ClientError
            if isinstance(error, ClientError):
                error_code = error.response.get("Error", {}).get("Code", "")
                if error_code in cls.S3_PERMISSION_CODES:
                    logger.debug(f"Detected S3 permission error: {error_code}")
                    return True
        except ImportError:
            pass
        
        # GCSのエラーコードから判定
        try:
            from google.api_core.exceptions import PermissionDenied, Forbidden
            if isinstance(error, (PermissionDenied, Forbidden)):
                logger.debug("Detected GCS permission error")
                return True
        except ImportError:
            pass
        
        # OSErrorのerrnoから判定 (EACCES: Permission denied)
        if isinstance(error, OSError):
            if hasattr(error, 'errno') and error.errno in (13, 1):  # EACCES, EPERM
                logger.debug("Detected filesystem permission error")
                return True
        
        return False
    
    @classmethod
    def wrap_storage_error(cls, error: Exception, operation: str, uri: Optional[str] = None) -> Exception:
        """
        ストレージエラーを適切な例外でラップ
        
        Args:
            error: 元の例外
            operation: 操作名 (upload/download/delete)
            uri: 成果物のURI (オプション)
            
        Returns:
            適切な例外
            
        Requirements: 15.2, 15.3
        """
        # ストレージ容量不足エラー
        if cls.detect_storage_full_error(error):
            message = f"Storage capacity exceeded during {operation}"
            if uri:
                message += f" for {uri}"
            message += f": {error}"
            logger.error(message)
            return StorageFullError(message)
        
        # 権限エラー
        if cls.detect_permission_error(error):
            message = f"Permission denied during {operation}"
            if uri:
                message += f" for {uri}"
            message += f": {error}"
            logger.error(message)
            return ArtifactPermissionError(message)
        
        # その他のストレージエラー
        message = f"Storage error during {operation}"
        if uri:
            message += f" for {uri}"
        message += f": {error}"
        logger.error(message)
        return StorageError(message)
    
    @classmethod
    def check_and_raise(cls, error: Exception, operation: str, uri: Optional[str] = None) -> None:
        """
        エラーをチェックして適切な例外を投げる
        
        Args:
            error: 元の例外
            operation: 操作名 (upload/download/delete)
            uri: 成果物のURI (オプション)
            
        Raises:
            StorageFullError: ストレージ容量不足の場合
            PermissionError: 権限エラーの場合
            StorageError: その他のストレージエラーの場合
            
        Requirements: 15.2, 15.3
        """
        wrapped_error = cls.wrap_storage_error(error, operation, uri)
        raise wrapped_error

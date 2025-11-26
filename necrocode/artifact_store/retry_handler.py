"""
Retry handler for Artifact Store operations.

Provides retry logic with exponential backoff for network and transient errors.
"""

import time
import logging
from typing import Callable, TypeVar, Optional, Type, Tuple
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryHandler:
    """
    リトライハンドラー
    
    ネットワークエラーや一時的なエラーに対して、指数バックオフでリトライを実行します。
    
    Requirements: 15.1, 15.4
    """
    
    # ネットワークエラーとして扱う例外のタイプ
    NETWORK_ERRORS = (
        ConnectionError,
        TimeoutError,
        OSError,  # Includes network-related OS errors
    )
    
    # boto3のネットワークエラー (動的にインポート)
    try:
        from botocore.exceptions import (
            ConnectionError as BotoConnectionError,
            EndpointConnectionError,
            ReadTimeoutError,
        )
        BOTO3_NETWORK_ERRORS = (
            BotoConnectionError,
            EndpointConnectionError,
            ReadTimeoutError,
        )
    except ImportError:
        BOTO3_NETWORK_ERRORS = ()
    
    # google-cloud-storageのネットワークエラー (動的にインポート)
    try:
        from google.api_core.exceptions import (
            ServiceUnavailable,
            DeadlineExceeded,
            InternalServerError,
        )
        GCS_NETWORK_ERRORS = (
            ServiceUnavailable,
            DeadlineExceeded,
            InternalServerError,
        )
    except ImportError:
        GCS_NETWORK_ERRORS = ()
    
    @classmethod
    def is_network_error(cls, error: Exception) -> bool:
        """
        ネットワークエラーかどうかを判定
        
        Args:
            error: 判定する例外
            
        Returns:
            ネットワークエラーの場合はTrue
        """
        # 基本的なネットワークエラー
        if isinstance(error, cls.NETWORK_ERRORS):
            return True
        
        # boto3のネットワークエラー
        if cls.BOTO3_NETWORK_ERRORS and isinstance(error, cls.BOTO3_NETWORK_ERRORS):
            return True
        
        # GCSのネットワークエラー
        if cls.GCS_NETWORK_ERRORS and isinstance(error, cls.GCS_NETWORK_ERRORS):
            return True
        
        # エラーメッセージからネットワークエラーを判定
        error_message = str(error).lower()
        network_keywords = [
            "connection",
            "timeout",
            "network",
            "unreachable",
            "unavailable",
            "refused",
            "reset",
        ]
        
        return any(keyword in error_message for keyword in network_keywords)
    
    @classmethod
    def retry_with_backoff(
        cls,
        func: Callable[..., T],
        max_attempts: int = 3,
        backoff_factor: float = 2.0,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
        non_retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    ) -> Callable[..., T]:
        """
        指数バックオフでリトライするデコレーター
        
        Args:
            func: リトライする関数
            max_attempts: 最大試行回数 (デフォルト: 3)
            backoff_factor: バックオフ係数 (デフォルト: 2.0)
            initial_delay: 初回の待機時間 (秒、デフォルト: 1.0)
            max_delay: 最大待機時間 (秒、デフォルト: 60.0)
            retryable_exceptions: リトライ可能な例外のタプル (Noneの場合はネットワークエラーのみ)
            non_retryable_exceptions: リトライ不可能な例外のタプル
            
        Returns:
            リトライロジックでラップされた関数
            
        Requirements: 15.1, 15.4
        """
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_error = None
            delay = initial_delay
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    last_error = e
                    
                    # リトライ不可能な例外の場合は即座に再送出
                    if non_retryable_exceptions and isinstance(e, non_retryable_exceptions):
                        logger.debug(f"Non-retryable exception: {type(e).__name__}: {e}")
                        raise
                    
                    # リトライ可能な例外かチェック
                    should_retry = False
                    
                    if retryable_exceptions:
                        # 明示的にリトライ可能な例外が指定されている場合
                        should_retry = isinstance(e, retryable_exceptions)
                    else:
                        # デフォルト: ネットワークエラーのみリトライ
                        should_retry = cls.is_network_error(e)
                    
                    if not should_retry:
                        logger.debug(f"Non-retryable error: {type(e).__name__}: {e}")
                        raise
                    
                    # 最後の試行の場合はリトライしない
                    if attempt >= max_attempts:
                        logger.error(
                            f"Failed after {max_attempts} attempts: {type(e).__name__}: {e}"
                        )
                        raise
                    
                    # 指数バックオフで待機
                    wait_time = min(delay, max_delay)
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed: {type(e).__name__}: {e}. "
                        f"Retrying in {wait_time:.2f}s..."
                    )
                    
                    time.sleep(wait_time)
                    delay *= backoff_factor
            
            # すべての試行が失敗した場合 (通常はここには到達しない)
            if last_error:
                raise last_error
            
            raise RuntimeError("Retry logic error: no attempts were made")
        
        return wrapper
    
    @classmethod
    def with_retry(
        cls,
        max_attempts: int = 3,
        backoff_factor: float = 2.0,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
        non_retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    ):
        """
        リトライデコレーター
        
        使用例:
            @RetryHandler.with_retry(max_attempts=3, backoff_factor=2.0)
            def upload_to_s3(data):
                # S3へのアップロード処理
                pass
        
        Args:
            max_attempts: 最大試行回数
            backoff_factor: バックオフ係数
            initial_delay: 初回の待機時間 (秒)
            max_delay: 最大待機時間 (秒)
            retryable_exceptions: リトライ可能な例外のタプル
            non_retryable_exceptions: リトライ不可能な例外のタプル
            
        Returns:
            デコレーター関数
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            return cls.retry_with_backoff(
                func,
                max_attempts=max_attempts,
                backoff_factor=backoff_factor,
                initial_delay=initial_delay,
                max_delay=max_delay,
                retryable_exceptions=retryable_exceptions,
                non_retryable_exceptions=non_retryable_exceptions,
            )
        
        return decorator


def retry_on_network_error(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
):
    """
    ネットワークエラーに対してリトライするデコレーター (簡易版)
    
    使用例:
        @retry_on_network_error(max_attempts=3)
        def download_from_s3(uri):
            # S3からのダウンロード処理
            pass
    
    Args:
        max_attempts: 最大試行回数
        backoff_factor: バックオフ係数
        initial_delay: 初回の待機時間 (秒)
        
    Returns:
        デコレーター関数
    """
    return RetryHandler.with_retry(
        max_attempts=max_attempts,
        backoff_factor=backoff_factor,
        initial_delay=initial_delay,
    )

"""
Lock Manager for Task Registry

Provides file-based locking mechanism for concurrent access control.
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional
import time
import logging

try:
    from filelock import FileLock, Timeout as FileLockTimeout
except ImportError:
    raise ImportError(
        "filelock library is required. Install it with: pip install filelock"
    )

from .exceptions import LockTimeoutError


logger = logging.getLogger(__name__)


class LockManager:
    """並行アクセス制御のためのロックマネージャー"""
    
    def __init__(self, locks_dir: Path):
        """
        Args:
            locks_dir: ロックファイルを保存するディレクトリ
        """
        self.locks_dir = Path(locks_dir)
        self.locks_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"LockManager initialized with locks_dir: {self.locks_dir}")
    
    def _get_lock_path(self, spec_name: str) -> Path:
        """
        ロックファイルのパスを取得
        
        Args:
            spec_name: スペック名
            
        Returns:
            ロックファイルのパス
        """
        return self.locks_dir / f"{spec_name}.lock"
    
    @contextmanager
    def acquire_lock(
        self,
        spec_name: str,
        timeout: float = 30.0,
        retry_interval: float = 0.1
    ) -> Generator[None, None, None]:
        """
        ロックを取得（コンテキストマネージャー）
        
        Args:
            spec_name: スペック名
            timeout: タイムアウト時間（秒）
            retry_interval: リトライ間隔（秒）
            
        Yields:
            None
            
        Raises:
            LockTimeoutError: ロック取得がタイムアウトした場合
            
        Example:
            with lock_manager.acquire_lock("my-spec", timeout=10.0):
                # クリティカルセクション
                pass
        """
        lock_path = self._get_lock_path(spec_name)
        lock = FileLock(lock_path)
        
        start_time = time.time()
        logger.debug(
            f"Attempting to acquire lock for '{spec_name}' "
            f"(timeout={timeout}s, retry_interval={retry_interval}s)"
        )
        
        acquired = False
        try:
            lock.acquire(timeout=timeout, poll_interval=retry_interval)
            acquired = True
            elapsed = time.time() - start_time
            logger.info(
                f"Lock acquired for '{spec_name}' ({elapsed:.2f}s)"
            )
            yield
            logger.debug(f"Lock released for '{spec_name}'")
        except FileLockTimeout:
            elapsed = time.time() - start_time
            logger.error(
                f"Lock acquisition timeout for '{spec_name}' ({elapsed:.2f}s)"
            )
            raise LockTimeoutError(spec_name, timeout)
        except Exception as e:
            logger.error(f"Error during lock acquisition for '{spec_name}': {e}")
            raise
        finally:
            if acquired and lock.is_locked:
                lock.release()
    
    def is_locked(self, spec_name: str) -> bool:
        """
        ロック状態を確認
        
        Args:
            spec_name: スペック名
            
        Returns:
            ロックされている場合True、そうでない場合False
        """
        lock_path = self._get_lock_path(spec_name)
        lock = FileLock(lock_path, timeout=0.01)
        
        try:
            # 即座にロックを取得できるか試す
            with lock.acquire(timeout=0.01):
                # ロックを取得できた = ロックされていない
                logger.debug(f"Lock check for '{spec_name}': not locked")
                return False
        except FileLockTimeout:
            # ロックを取得できなかった = ロックされている
            logger.debug(f"Lock check for '{spec_name}': locked")
            return True
    
    def force_unlock(self, spec_name: str) -> None:
        """
        強制的にロックを解除（デッドロック対策）
        
        注意: この操作は危険です。他のプロセスがロックを保持している場合、
        データの整合性が失われる可能性があります。
        
        Args:
            spec_name: スペック名
        """
        lock_path = self._get_lock_path(spec_name)
        
        if lock_path.exists():
            try:
                lock_path.unlink()
                logger.warning(
                    f"Force unlocked '{spec_name}' by removing lock file: {lock_path}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to force unlock '{spec_name}': {e}"
                )
                raise
        else:
            logger.debug(
                f"Force unlock requested for '{spec_name}', but lock file does not exist"
            )

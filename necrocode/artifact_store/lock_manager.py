"""
Lock Manager for Artifact Store

Provides file-based locking mechanism for concurrent artifact access control.
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator
import time
import logging

try:
    from filelock import FileLock, Timeout as FileLockTimeout
except ImportError:
    raise ImportError(
        "filelock library is required. Install it with: pip install filelock"
    )

from necrocode.artifact_store.exceptions import LockTimeoutError


logger = logging.getLogger(__name__)


class ArtifactLockManager:
    """
    Artifact lock manager for concurrent access control.
    
    Provides file-based locking to prevent concurrent writes to the same artifact.
    Read operations do not require locks.
    """
    
    def __init__(
        self,
        locks_dir: Path,
        default_timeout: float = 30.0,
        default_retry_interval: float = 0.1,
    ):
        """
        Initialize lock manager.
        
        Args:
            locks_dir: Directory to store lock files
            default_timeout: Default timeout in seconds for lock acquisition
            default_retry_interval: Default interval between retry attempts in seconds
        """
        self.locks_dir = Path(locks_dir)
        self.locks_dir.mkdir(parents=True, exist_ok=True)
        self.default_timeout = default_timeout
        self.default_retry_interval = default_retry_interval
        logger.debug(
            f"ArtifactLockManager initialized with locks_dir: {self.locks_dir}, "
            f"default_timeout={default_timeout}s, "
            f"default_retry_interval={default_retry_interval}s"
        )
    
    def _get_lock_path(self, uri: str) -> Path:
        """
        Get lock file path for an artifact URI.
        
        Args:
            uri: Artifact URI
            
        Returns:
            Path to lock file
        """
        # Convert URI to safe filename
        safe_name = uri.replace("://", "_").replace("/", "_").replace("\\", "_")
        return self.locks_dir / f"{safe_name}.lock"
    
    @contextmanager
    def acquire_write_lock(
        self,
        uri: str,
        timeout: float = None,
        retry_interval: float = None,
    ) -> Generator[None, None, None]:
        """
        Acquire write lock for an artifact (context manager).
        
        This method provides exclusive write access to an artifact using file-based locking.
        The lock is automatically released when exiting the context.
        
        Implements retry logic with configurable timeout and retry interval.
        
        Args:
            uri: Artifact URI
            timeout: Timeout in seconds (None = use default)
            retry_interval: Interval between retry attempts in seconds (None = use default)
            
        Yields:
            None
            
        Raises:
            LockTimeoutError: If lock acquisition times out
            
        Example:
            with lock_manager.acquire_write_lock(uri, timeout=10.0):
                # Critical section - artifact is locked for writing
                upload_artifact()
        
        Requirements: 11.1, 11.2, 11.3, 11.4
        """
        # Use defaults if not specified
        if timeout is None:
            timeout = self.default_timeout
        if retry_interval is None:
            retry_interval = self.default_retry_interval
        
        lock_path = self._get_lock_path(uri)
        lock = FileLock(lock_path, timeout=timeout)
        
        start_time = time.time()
        logger.debug(
            f"Attempting to acquire write lock for artifact '{uri}' "
            f"(timeout={timeout}s, retry_interval={retry_interval}s)"
        )
        
        acquired = False
        attempt = 0
        
        try:
            # Retry loop with timeout
            while True:
                attempt += 1
                elapsed = time.time() - start_time
                
                # Check if we've exceeded the timeout
                if elapsed >= timeout:
                    logger.error(
                        f"Write lock acquisition timeout for artifact '{uri}' "
                        f"after {attempt} attempts ({elapsed:.2f}s)"
                    )
                    raise LockTimeoutError(uri, timeout)
                
                try:
                    # Calculate remaining timeout
                    remaining_timeout = timeout - elapsed
                    
                    # Try to acquire lock with remaining timeout
                    lock.acquire(timeout=min(retry_interval, remaining_timeout))
                    acquired = True
                    
                    logger.info(
                        f"Write lock acquired for artifact '{uri}' "
                        f"on attempt {attempt} ({elapsed:.2f}s)"
                    )
                    break
                    
                except FileLockTimeout:
                    # Lock not available, retry if time permits
                    if attempt > 1:
                        logger.debug(
                            f"Lock acquisition retry {attempt} for artifact '{uri}' "
                            f"({elapsed:.2f}s elapsed)"
                        )
                    
                    # Sleep before next retry (if we have time)
                    if elapsed + retry_interval < timeout:
                        time.sleep(retry_interval)
                    continue
            
            # Lock acquired, yield control
            yield
            logger.debug(f"Write lock released for artifact '{uri}'")
            
        except LockTimeoutError:
            raise
        except Exception as e:
            logger.error(f"Error during lock acquisition for artifact '{uri}': {e}")
            raise
        finally:
            if acquired and lock.is_locked:
                lock.release()
    
    def is_locked(self, uri: str) -> bool:
        """
        Check if artifact is locked for writing.
        
        Args:
            uri: Artifact URI
            
        Returns:
            True if artifact is locked, False otherwise
            
        Requirements: 11.1, 11.2
        """
        lock_path = self._get_lock_path(uri)
        
        # If lock file doesn't exist, it's not locked
        if not lock_path.exists():
            logger.debug(f"Lock check for artifact '{uri}': not locked (no lock file)")
            return False
        
        lock = FileLock(lock_path, timeout=0.01)
        
        try:
            # Try to acquire lock immediately
            with lock.acquire(timeout=0.01):
                # Successfully acquired = not locked
                logger.debug(f"Lock check for artifact '{uri}': not locked")
                return False
        except FileLockTimeout:
            # Failed to acquire = locked
            logger.debug(f"Lock check for artifact '{uri}': locked")
            return True
    
    def force_unlock(self, uri: str) -> None:
        """
        Force unlock an artifact (deadlock recovery).
        
        WARNING: This operation is dangerous. If another process holds the lock,
        data integrity may be compromised. Use only for deadlock recovery.
        
        Args:
            uri: Artifact URI
            
        Requirements: 11.1, 11.2
        """
        lock_path = self._get_lock_path(uri)
        
        if lock_path.exists():
            try:
                lock_path.unlink()
                logger.warning(
                    f"Force unlocked artifact '{uri}' by removing lock file: {lock_path}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to force unlock artifact '{uri}': {e}"
                )
                raise
        else:
            logger.debug(
                f"Force unlock requested for artifact '{uri}', but lock file does not exist"
            )

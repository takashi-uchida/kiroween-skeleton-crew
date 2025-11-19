"""
Lock Manager for Repo Pool Manager

Provides file-based locking mechanism for slot allocation concurrency control.
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator, List
import time
import logging
from datetime import datetime, timedelta

try:
    from filelock import FileLock, Timeout as FileLockTimeout
except ImportError:
    raise ImportError(
        "filelock library is required. Install it with: pip install filelock"
    )

from .exceptions import LockTimeoutError


logger = logging.getLogger(__name__)


class LockManager:
    """Slot lock manager for concurrent access control."""
    
    def __init__(self, locks_dir: Path):
        """
        Initialize lock manager.
        
        Args:
            locks_dir: Directory to store lock files
        """
        self.locks_dir = Path(locks_dir)
        self.locks_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"LockManager initialized with locks_dir: {self.locks_dir}")
    
    def _get_lock_path(self, slot_id: str) -> Path:
        """
        Get lock file path for a slot.
        
        Args:
            slot_id: Slot identifier
            
        Returns:
            Path to lock file
        """
        return self.locks_dir / f"{slot_id}.lock"
    
    @contextmanager
    def acquire_slot_lock(
        self,
        slot_id: str,
        timeout: float = 30.0
    ) -> Generator[None, None, None]:
        """
        Acquire slot lock (context manager).
        
        This method provides exclusive access to a slot using file-based locking.
        The lock is automatically released when exiting the context.
        
        Args:
            slot_id: Slot identifier
            timeout: Timeout in seconds
            
        Yields:
            None
            
        Raises:
            LockTimeoutError: If lock acquisition times out
            
        Example:
            with lock_manager.acquire_slot_lock("workspace-chat-app-slot1", timeout=10.0):
                # Critical section - slot is locked
                allocate_slot()
        
        Requirements: 4.1
        """
        lock_path = self._get_lock_path(slot_id)
        lock = FileLock(lock_path, timeout=timeout)
        
        start_time = time.time()
        logger.debug(
            f"Attempting to acquire lock for slot '{slot_id}' "
            f"(timeout={timeout}s)"
        )
        
        acquired = False
        try:
            lock.acquire(timeout=timeout)
            acquired = True
            elapsed = time.time() - start_time
            logger.info(
                f"Lock acquired for slot '{slot_id}' ({elapsed:.2f}s)"
            )
            yield
            logger.debug(f"Lock released for slot '{slot_id}'")
        except FileLockTimeout:
            elapsed = time.time() - start_time
            logger.error(
                f"Lock acquisition timeout for slot '{slot_id}' ({elapsed:.2f}s)"
            )
            raise LockTimeoutError(
                f"Failed to acquire lock for slot '{slot_id}' within {timeout}s"
            )
        except Exception as e:
            logger.error(f"Error during lock acquisition for slot '{slot_id}': {e}")
            raise
        finally:
            if acquired and lock.is_locked:
                lock.release()
    
    def is_locked(self, slot_id: str) -> bool:
        """
        Check if slot is locked.
        
        Args:
            slot_id: Slot identifier
            
        Returns:
            True if slot is locked, False otherwise
            
        Requirements: 4.2, 4.5
        """
        lock_path = self._get_lock_path(slot_id)
        
        # If lock file doesn't exist, it's not locked
        if not lock_path.exists():
            logger.debug(f"Lock check for slot '{slot_id}': not locked (no lock file)")
            return False
        
        lock = FileLock(lock_path, timeout=0.01)
        
        try:
            # Try to acquire lock immediately
            with lock.acquire(timeout=0.01):
                # Successfully acquired = not locked
                logger.debug(f"Lock check for slot '{slot_id}': not locked")
                return False
        except FileLockTimeout:
            # Failed to acquire = locked
            logger.debug(f"Lock check for slot '{slot_id}': locked")
            return True
    
    def force_unlock(self, slot_id: str) -> None:
        """
        Force unlock a slot (deadlock recovery).
        
        WARNING: This operation is dangerous. If another process holds the lock,
        data integrity may be compromised. Use only for deadlock recovery.
        
        Args:
            slot_id: Slot identifier
            
        Requirements: 4.2, 4.5
        """
        lock_path = self._get_lock_path(slot_id)
        
        if lock_path.exists():
            try:
                lock_path.unlink()
                logger.warning(
                    f"Force unlocked slot '{slot_id}' by removing lock file: {lock_path}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to force unlock slot '{slot_id}': {e}"
                )
                raise
        else:
            logger.debug(
                f"Force unlock requested for slot '{slot_id}', but lock file does not exist"
            )
    
    def detect_stale_locks(self, max_age_hours: int = 24) -> List[str]:
        """
        Detect stale locks (locks older than max_age_hours).
        
        Stale locks may indicate crashed processes or deadlocks.
        
        Args:
            max_age_hours: Maximum age in hours before a lock is considered stale
            
        Returns:
            List of slot IDs with stale locks
            
        Requirements: 4.4, 9.4
        """
        stale_locks = []
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        logger.debug(
            f"Detecting stale locks older than {max_age_hours} hours "
            f"(cutoff: {cutoff_time})"
        )
        
        if not self.locks_dir.exists():
            logger.debug("Locks directory does not exist, no stale locks")
            return stale_locks
        
        for lock_file in self.locks_dir.glob("*.lock"):
            try:
                # Get file modification time
                mtime = datetime.fromtimestamp(lock_file.stat().st_mtime)
                
                if mtime < cutoff_time:
                    # Extract slot_id from lock file name
                    slot_id = lock_file.stem
                    stale_locks.append(slot_id)
                    logger.info(
                        f"Detected stale lock for slot '{slot_id}' "
                        f"(age: {datetime.now() - mtime})"
                    )
            except Exception as e:
                logger.error(f"Error checking lock file {lock_file}: {e}")
        
        logger.info(f"Found {len(stale_locks)} stale lock(s)")
        return stale_locks
    
    def cleanup_stale_locks(self, max_age_hours: int = 24) -> int:
        """
        Clean up stale locks (remove locks older than max_age_hours).
        
        This method detects and removes stale locks to prevent deadlocks
        from crashed processes.
        
        Args:
            max_age_hours: Maximum age in hours before a lock is considered stale
            
        Returns:
            Number of stale locks cleaned up
            
        Requirements: 4.4, 9.4
        """
        stale_locks = self.detect_stale_locks(max_age_hours)
        cleaned_count = 0
        
        logger.info(f"Cleaning up {len(stale_locks)} stale lock(s)")
        
        for slot_id in stale_locks:
            try:
                self.force_unlock(slot_id)
                cleaned_count += 1
            except Exception as e:
                logger.error(f"Failed to clean up stale lock for slot '{slot_id}': {e}")
        
        logger.info(f"Successfully cleaned up {cleaned_count} stale lock(s)")
        return cleaned_count

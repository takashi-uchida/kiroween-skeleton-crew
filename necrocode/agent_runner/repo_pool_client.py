"""
Repo Pool Client for Agent Runner

Handles communication with Repo Pool Manager service for slot allocation
and release operations.
"""

import logging
import time
from pathlib import Path
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from necrocode.agent_runner.exceptions import RunnerError
from necrocode.agent_runner.models import SlotAllocation

logger = logging.getLogger(__name__)


class RepoPoolClient:
    """Repo Pool Managerとの通信クライアント"""
    
    def __init__(self, base_url: str, timeout: int = 30):
        """
        Args:
            base_url: Repo Pool ManagerのベースURL
            timeout: リクエストタイムアウト（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """リトライ機能付きのセッションを作成"""
        session = requests.Session()
        
        # リトライ戦略を設定
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def allocate_slot(
        self,
        repo_url: str,
        required_by: str,
        timeout_seconds: Optional[int] = None
    ) -> SlotAllocation:
        """
        スロットを割り当て
        
        Args:
            repo_url: リポジトリURL
            required_by: 要求者（タスクID等）
            timeout_seconds: 割り当てタイムアウト（秒）
            
        Returns:
            SlotAllocation: スロット割り当て情報
            
        Raises:
            RunnerError: 割り当てに失敗した場合
        """
        url = f"{self.base_url}/slots/allocate"
        payload = {
            "repo_url": repo_url,
            "required_by": required_by
        }
        
        if timeout_seconds:
            payload["timeout_seconds"] = timeout_seconds
        
        logger.info(
            "Allocating slot from Repo Pool Manager",
            extra={
                "service": "repo_pool",
                "operation": "allocate_slot",
                "repo_url": repo_url,
                "required_by": required_by
            }
        )
        
        start_time = time.time()
        try:
            response = self.session.post(
                url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            slot_allocation = SlotAllocation(
                slot_id=data["slot_id"],
                slot_path=Path(data["slot_path"])
            )
            
            duration = time.time() - start_time
            logger.info(
                "Slot allocated successfully",
                extra={
                    "service": "repo_pool",
                    "operation": "allocate_slot",
                    "slot_id": slot_allocation.slot_id,
                    "slot_path": str(slot_allocation.slot_path),
                    "duration_seconds": duration
                }
            )
            
            return slot_allocation
        except requests.exceptions.RequestException as e:
            duration = time.time() - start_time
            logger.error(
                "Failed to allocate slot",
                extra={
                    "service": "repo_pool",
                    "operation": "allocate_slot",
                    "repo_url": repo_url,
                    "duration_seconds": duration,
                    "error": str(e)
                }
            )
            raise RunnerError(f"Failed to allocate slot: {e}")
        except (KeyError, TypeError) as e:
            duration = time.time() - start_time
            logger.error(
                "Invalid slot allocation response",
                extra={
                    "service": "repo_pool",
                    "operation": "allocate_slot",
                    "duration_seconds": duration,
                    "error": str(e)
                }
            )
            raise RunnerError(f"Invalid slot allocation response: {e}")
    
    def release_slot(self, slot_id: str) -> None:
        """
        スロットを返却
        
        Args:
            slot_id: スロットID
            
        Raises:
            RunnerError: 返却に失敗した場合
        """
        url = f"{self.base_url}/slots/{slot_id}/release"
        
        logger.info(
            "Releasing slot to Repo Pool Manager",
            extra={
                "service": "repo_pool",
                "operation": "release_slot",
                "slot_id": slot_id
            }
        )
        
        start_time = time.time()
        try:
            response = self.session.post(url, timeout=self.timeout)
            response.raise_for_status()
            
            duration = time.time() - start_time
            logger.info(
                "Slot released successfully",
                extra={
                    "service": "repo_pool",
                    "operation": "release_slot",
                    "slot_id": slot_id,
                    "duration_seconds": duration
                }
            )
        except requests.exceptions.RequestException as e:
            duration = time.time() - start_time
            logger.error(
                "Failed to release slot",
                extra={
                    "service": "repo_pool",
                    "operation": "release_slot",
                    "slot_id": slot_id,
                    "duration_seconds": duration,
                    "error": str(e)
                }
            )
            raise RunnerError(f"Failed to release slot: {e}")
    
    def get_slot_status(self, slot_id: str) -> dict:
        """
        スロットの状態を取得
        
        Args:
            slot_id: スロットID
            
        Returns:
            スロット状態情報
            
        Raises:
            RunnerError: 取得に失敗した場合
        """
        url = f"{self.base_url}/slots/{slot_id}"
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise RunnerError(f"Failed to get slot status: {e}")
    
    def health_check(self) -> bool:
        """
        Repo Pool Managerのヘルスチェック
        
        Returns:
            サービスが正常な場合True
        """
        url = f"{self.base_url}/health"
        
        try:
            response = self.session.get(url, timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

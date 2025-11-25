"""
Task Registry Client for Agent Runner

Handles communication with Task Registry service for task state updates,
event recording, and artifact registration.
"""

import logging
import time
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from necrocode.agent_runner.exceptions import RunnerError

logger = logging.getLogger(__name__)


class TaskRegistryClient:
    """Task Registryとの通信クライアント"""
    
    def __init__(self, base_url: str, timeout: int = 30):
        """
        Args:
            base_url: Task RegistryのベースURL
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
    
    def update_task_status(
        self,
        task_id: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        タスクの状態を更新
        
        Args:
            task_id: タスクID
            status: 新しい状態（"in_progress", "done", "failed"等）
            metadata: 追加のメタデータ
            
        Raises:
            RunnerError: 更新に失敗した場合
        """
        url = f"{self.base_url}/tasks/{task_id}/status"
        payload = {
            "status": status,
            "metadata": metadata or {},
            "updated_at": time.time()
        }
        
        logger.info(
            "Updating task status in Task Registry",
            extra={
                "service": "task_registry",
                "operation": "update_task_status",
                "task_id": task_id,
                "status": status,
                "url": url
            }
        )
        
        start_time = time.time()
        try:
            response = self.session.put(
                url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            duration = time.time() - start_time
            logger.info(
                "Task status updated successfully",
                extra={
                    "service": "task_registry",
                    "operation": "update_task_status",
                    "task_id": task_id,
                    "status": status,
                    "duration_seconds": duration,
                    "status_code": response.status_code
                }
            )
        except requests.exceptions.RequestException as e:
            duration = time.time() - start_time
            logger.error(
                "Failed to update task status",
                extra={
                    "service": "task_registry",
                    "operation": "update_task_status",
                    "task_id": task_id,
                    "status": status,
                    "duration_seconds": duration,
                    "error": str(e)
                }
            )
            raise RunnerError(f"Failed to update task status: {e}")
    
    def add_event(
        self,
        task_id: str,
        event_type: str,
        data: Dict[str, Any]
    ) -> None:
        """
        イベントを記録
        
        Args:
            task_id: タスクID
            event_type: イベントタイプ（"TaskStarted", "TaskCompleted"等）
            data: イベントデータ
            
        Raises:
            RunnerError: 記録に失敗した場合
        """
        url = f"{self.base_url}/tasks/{task_id}/events"
        payload = {
            "event_type": event_type,
            "data": data,
            "timestamp": time.time()
        }
        
        logger.debug(
            "Adding event to Task Registry",
            extra={
                "service": "task_registry",
                "operation": "add_event",
                "task_id": task_id,
                "event_type": event_type
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
            
            duration = time.time() - start_time
            logger.debug(
                "Event added successfully",
                extra={
                    "service": "task_registry",
                    "operation": "add_event",
                    "task_id": task_id,
                    "event_type": event_type,
                    "duration_seconds": duration
                }
            )
        except requests.exceptions.RequestException as e:
            duration = time.time() - start_time
            logger.error(
                "Failed to add event",
                extra={
                    "service": "task_registry",
                    "operation": "add_event",
                    "task_id": task_id,
                    "event_type": event_type,
                    "duration_seconds": duration,
                    "error": str(e)
                }
            )
            raise RunnerError(f"Failed to add event: {e}")
    
    def add_artifact(
        self,
        task_id: str,
        artifact_type: str,
        uri: str,
        size_bytes: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        成果物を記録
        
        Args:
            task_id: タスクID
            artifact_type: 成果物タイプ（"diff", "log", "test"等）
            uri: 成果物のURI
            size_bytes: サイズ（バイト）
            metadata: 追加のメタデータ
            
        Raises:
            RunnerError: 記録に失敗した場合
        """
        url = f"{self.base_url}/tasks/{task_id}/artifacts"
        payload = {
            "type": artifact_type,
            "uri": uri,
            "size_bytes": size_bytes,
            "metadata": metadata or {},
            "created_at": time.time()
        }
        
        logger.info(
            "Adding artifact to Task Registry",
            extra={
                "service": "task_registry",
                "operation": "add_artifact",
                "task_id": task_id,
                "artifact_type": artifact_type,
                "size_bytes": size_bytes
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
            
            duration = time.time() - start_time
            logger.info(
                "Artifact added successfully",
                extra={
                    "service": "task_registry",
                    "operation": "add_artifact",
                    "task_id": task_id,
                    "artifact_type": artifact_type,
                    "size_bytes": size_bytes,
                    "duration_seconds": duration
                }
            )
        except requests.exceptions.RequestException as e:
            duration = time.time() - start_time
            logger.error(
                "Failed to add artifact",
                extra={
                    "service": "task_registry",
                    "operation": "add_artifact",
                    "task_id": task_id,
                    "artifact_type": artifact_type,
                    "duration_seconds": duration,
                    "error": str(e)
                }
            )
            raise RunnerError(f"Failed to add artifact: {e}")
    
    def get_task(self, task_id: str) -> Dict[str, Any]:
        """
        タスク情報を取得
        
        Args:
            task_id: タスクID
            
        Returns:
            タスク情報
            
        Raises:
            RunnerError: 取得に失敗した場合
        """
        url = f"{self.base_url}/tasks/{task_id}"
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise RunnerError(f"Failed to get task: {e}")
    
    def health_check(self) -> bool:
        """
        Task Registryのヘルスチェック
        
        Returns:
            サービスが正常な場合True
        """
        url = f"{self.base_url}/health"
        
        try:
            response = self.session.get(url, timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

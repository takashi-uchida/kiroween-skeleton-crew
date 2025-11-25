"""
Artifact Store Client for Agent Runner

Handles communication with Artifact Store service for uploading
artifacts (diffs, logs, test results, etc.).
"""

import json
import logging
import time
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from necrocode.agent_runner.exceptions import RunnerError

logger = logging.getLogger(__name__)


class ArtifactStoreClient:
    """Artifact Storeとの通信クライアント"""
    
    def __init__(self, base_url: str, timeout: int = 60):
        """
        Args:
            base_url: Artifact StoreのベースURL
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
            allowed_methods=["GET", "POST", "PUT"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def upload(
        self,
        artifact_type: str,
        content: bytes,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        成果物をアップロード
        
        Args:
            artifact_type: 成果物タイプ（"diff", "log", "test"等）
            content: 成果物の内容（バイト列）
            metadata: 追加のメタデータ
            
        Returns:
            成果物のURI
            
        Raises:
            RunnerError: アップロードに失敗した場合
        """
        url = f"{self.base_url}/artifacts"
        
        files = {"file": content}
        data = {
            "type": artifact_type,
            "metadata": json.dumps(metadata or {})
        }
        
        logger.info(
            "Uploading artifact to Artifact Store",
            extra={
                "service": "artifact_store",
                "operation": "upload",
                "artifact_type": artifact_type,
                "size_bytes": len(content)
            }
        )
        
        start_time = time.time()
        try:
            response = self.session.post(
                url,
                files=files,
                data=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            uri = result["uri"]
            
            duration = time.time() - start_time
            logger.info(
                "Artifact uploaded successfully",
                extra={
                    "service": "artifact_store",
                    "operation": "upload",
                    "artifact_type": artifact_type,
                    "size_bytes": len(content),
                    "uri": uri,
                    "duration_seconds": duration
                }
            )
            
            return uri
        except requests.exceptions.RequestException as e:
            duration = time.time() - start_time
            logger.error(
                "Failed to upload artifact",
                extra={
                    "service": "artifact_store",
                    "operation": "upload",
                    "artifact_type": artifact_type,
                    "size_bytes": len(content),
                    "duration_seconds": duration,
                    "error": str(e)
                }
            )
            raise RunnerError(f"Failed to upload artifact: {e}")
        except (KeyError, TypeError) as e:
            duration = time.time() - start_time
            logger.error(
                "Invalid artifact upload response",
                extra={
                    "service": "artifact_store",
                    "operation": "upload",
                    "artifact_type": artifact_type,
                    "duration_seconds": duration,
                    "error": str(e)
                }
            )
            raise RunnerError(f"Invalid artifact upload response: {e}")
    
    def upload_text(
        self,
        artifact_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        テキスト成果物をアップロード
        
        Args:
            artifact_type: 成果物タイプ
            content: テキスト内容
            metadata: 追加のメタデータ
            
        Returns:
            成果物のURI
            
        Raises:
            RunnerError: アップロードに失敗した場合
        """
        return self.upload(artifact_type, content.encode('utf-8'), metadata)
    
    def download(self, uri: str) -> bytes:
        """
        成果物をダウンロード
        
        Args:
            uri: 成果物のURI
            
        Returns:
            成果物の内容（バイト列）
            
        Raises:
            RunnerError: ダウンロードに失敗した場合
        """
        try:
            response = self.session.get(uri, timeout=self.timeout)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            raise RunnerError(f"Failed to download artifact: {e}")
    
    def download_text(self, uri: str) -> str:
        """
        テキスト成果物をダウンロード
        
        Args:
            uri: 成果物のURI
            
        Returns:
            テキスト内容
            
        Raises:
            RunnerError: ダウンロードに失敗した場合
        """
        content = self.download(uri)
        return content.decode('utf-8')
    
    def get_metadata(self, uri: str) -> Dict[str, Any]:
        """
        成果物のメタデータを取得
        
        Args:
            uri: 成果物のURI
            
        Returns:
            メタデータ
            
        Raises:
            RunnerError: 取得に失敗した場合
        """
        url = f"{self.base_url}/artifacts/metadata"
        params = {"uri": uri}
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise RunnerError(f"Failed to get artifact metadata: {e}")
    
    def health_check(self) -> bool:
        """
        Artifact Storeのヘルスチェック
        
        Returns:
            サービスが正常な場合True
        """
        url = f"{self.base_url}/health"
        
        try:
            response = self.session.get(url, timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

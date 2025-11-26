"""
Metadata Manager for Artifact Store.

Manages artifact metadata storage, retrieval, and indexing.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import logging
from threading import Lock

from necrocode.artifact_store.models import ArtifactMetadata, ArtifactType
from necrocode.artifact_store.config import ArtifactStoreConfig
from necrocode.artifact_store.exceptions import (
    ArtifactNotFoundError,
    StorageError,
)


logger = logging.getLogger(__name__)


class MetadataManager:
    """
    メタデータマネージャー
    
    成果物のメタデータをJSON形式で保存・読み込み・検索する機能を提供します。
    メタデータインデックスを管理し、高速な検索を実現します。
    """
    
    def __init__(self, config: ArtifactStoreConfig):
        """
        初期化
        
        Args:
            config: Artifact Storeの設定
        """
        self.config = config
        self.base_path = config.base_path
        self.metadata_dir = self.base_path / "metadata"
        self.index_file = self.base_path / "metadata-index.json"
        
        # インデックスキャッシュ
        self._index: Dict[str, Dict[str, Any]] = {}
        self._index_lock = Lock()
        
        # 初期化
        self._ensure_directories()
        self._load_index()
    
    def _ensure_directories(self) -> None:
        """必要なディレクトリを作成"""
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_metadata_path(self, uri: str) -> Path:
        """
        URIからメタデータファイルのパスを取得
        
        Args:
            uri: 成果物のURI
            
        Returns:
            メタデータファイルのパス
        """
        # URIをファイル名に変換 (スラッシュをアンダースコアに置換)
        safe_name = uri.replace("://", "_").replace("/", "_").replace("\\", "_")
        return self.metadata_dir / f"{safe_name}.json"
    
    def save(self, metadata: ArtifactMetadata) -> None:
        """
        メタデータをJSON形式で保存
        
        Args:
            metadata: 保存するメタデータ
            
        Raises:
            StorageError: 保存に失敗した場合
        """
        try:
            # メタデータファイルに保存
            metadata_path = self._get_metadata_path(metadata.uri)
            with open(metadata_path, 'w', encoding='utf-8') as f:
                f.write(metadata.to_json())
            
            # インデックスを更新
            self._update_index(metadata)
            
            logger.debug(f"Saved metadata for {metadata.uri}")
            
        except Exception as e:
            logger.error(f"Failed to save metadata for {metadata.uri}: {e}")
            raise StorageError(f"Failed to save metadata: {e}")
    
    def load(self, uri: str) -> ArtifactMetadata:
        """
        メタデータを読み込み
        
        Args:
            uri: 成果物のURI
            
        Returns:
            読み込んだメタデータ
            
        Raises:
            ArtifactNotFoundError: メタデータが見つからない場合
            StorageError: 読み込みに失敗した場合
        """
        try:
            metadata_path = self._get_metadata_path(uri)
            
            if not metadata_path.exists():
                raise ArtifactNotFoundError(uri)
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                json_str = f.read()
            
            metadata = ArtifactMetadata.from_json(json_str)
            logger.debug(f"Loaded metadata for {uri}")
            return metadata
            
        except ArtifactNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to load metadata for {uri}: {e}")
            raise StorageError(f"Failed to load metadata: {e}")
    
    def get_by_uri(self, uri: str) -> Optional[ArtifactMetadata]:
        """
        URIからメタデータを取得
        
        Args:
            uri: 成果物のURI
            
        Returns:
            メタデータ、見つからない場合はNone
        """
        try:
            return self.load(uri)
        except ArtifactNotFoundError:
            return None
    
    def get_by_task_id(self, task_id: str) -> List[ArtifactMetadata]:
        """
        タスクIDに関連するすべての成果物のメタデータを取得
        
        Args:
            task_id: タスクID
            
        Returns:
            メタデータのリスト
        """
        results = []
        
        with self._index_lock:
            for uri, index_entry in self._index.items():
                if index_entry.get("task_id") == task_id:
                    try:
                        metadata = self.load(uri)
                        results.append(metadata)
                    except Exception as e:
                        logger.warning(f"Failed to load metadata for {uri}: {e}")
        
        logger.debug(f"Found {len(results)} artifacts for task_id={task_id}")
        return results
    
    def get_by_spec_name(self, spec_name: str) -> List[ArtifactMetadata]:
        """
        Spec名に関連するすべての成果物のメタデータを取得
        
        Args:
            spec_name: Spec名
            
        Returns:
            メタデータのリスト
        """
        results = []
        
        with self._index_lock:
            for uri, index_entry in self._index.items():
                if index_entry.get("spec_name") == spec_name:
                    try:
                        metadata = self.load(uri)
                        results.append(metadata)
                    except Exception as e:
                        logger.warning(f"Failed to load metadata for {uri}: {e}")
        
        logger.debug(f"Found {len(results)} artifacts for spec_name={spec_name}")
        return results
    
    def delete(self, uri: str) -> None:
        """
        メタデータを削除
        
        Args:
            uri: 成果物のURI
            
        Raises:
            ArtifactNotFoundError: メタデータが見つからない場合
        """
        metadata_path = self._get_metadata_path(uri)
        
        if not metadata_path.exists():
            raise ArtifactNotFoundError(uri)
        
        # メタデータファイルを削除
        metadata_path.unlink()
        
        # インデックスから削除
        self._remove_from_index(uri)
        
        logger.debug(f"Deleted metadata for {uri}")
    
    def _load_index(self) -> None:
        """インデックスファイルを読み込み"""
        with self._index_lock:
            if self.index_file.exists():
                try:
                    with open(self.index_file, 'r', encoding='utf-8') as f:
                        self._index = json.load(f)
                    logger.debug(f"Loaded index with {len(self._index)} entries")
                except Exception as e:
                    logger.warning(f"Failed to load index, creating new one: {e}")
                    self._index = {}
            else:
                self._index = {}
                logger.debug("Created new empty index")
    
    def _save_index(self) -> None:
        """インデックスファイルを保存"""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self._index, f, indent=2)
            logger.debug(f"Saved index with {len(self._index)} entries")
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
    
    def _update_index(self, metadata: ArtifactMetadata) -> None:
        """
        インデックスを更新
        
        Args:
            metadata: メタデータ
        """
        with self._index_lock:
            self._index[metadata.uri] = {
                "task_id": metadata.task_id,
                "spec_name": metadata.spec_name,
                "type": metadata.type.value,
                "size": metadata.size,
                "created_at": metadata.created_at.isoformat(),
                "tags": metadata.tags,
                "version": metadata.version,
            }
            self._save_index()
    
    def _remove_from_index(self, uri: str) -> None:
        """
        インデックスから削除
        
        Args:
            uri: 成果物のURI
        """
        with self._index_lock:
            if uri in self._index:
                del self._index[uri]
                self._save_index()
    
    def search(
        self,
        task_id: Optional[str] = None,
        spec_name: Optional[str] = None,
        artifact_type: Optional[ArtifactType] = None,
        tags: Optional[List[str]] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
    ) -> List[ArtifactMetadata]:
        """
        複数の条件で成果物を検索
        
        Args:
            task_id: タスクID (オプション)
            spec_name: Spec名 (オプション)
            artifact_type: 成果物のタイプ (オプション)
            tags: タグのリスト (オプション、いずれかのタグにマッチ)
            created_after: この日時以降に作成された成果物 (オプション)
            created_before: この日時以前に作成された成果物 (オプション)
            
        Returns:
            条件に合致するメタデータのリスト
        """
        results = []
        
        with self._index_lock:
            for uri, index_entry in self._index.items():
                # 条件チェック
                if task_id and index_entry.get("task_id") != task_id:
                    continue
                
                if spec_name and index_entry.get("spec_name") != spec_name:
                    continue
                
                if artifact_type and index_entry.get("type") != artifact_type.value:
                    continue
                
                if tags:
                    entry_tags = index_entry.get("tags", [])
                    if not any(tag in entry_tags for tag in tags):
                        continue
                
                # 日時フィルタ (インデックスから取得)
                created_at_str = index_entry.get("created_at")
                if created_at_str:
                    created_at = datetime.fromisoformat(created_at_str)
                    
                    if created_after and created_at < created_after:
                        continue
                    
                    if created_before and created_at > created_before:
                        continue
                
                # 条件に合致した場合、完全なメタデータを読み込み
                try:
                    metadata = self.load(uri)
                    results.append(metadata)
                except Exception as e:
                    logger.warning(f"Failed to load metadata for {uri}: {e}")
        
        logger.debug(
            f"Search found {len(results)} artifacts "
            f"(task_id={task_id}, spec_name={spec_name}, type={artifact_type})"
        )
        return results
    
    def get_all(self) -> List[ArtifactMetadata]:
        """
        すべてのメタデータを取得
        
        Returns:
            すべてのメタデータのリスト
        """
        results = []
        
        with self._index_lock:
            for uri in self._index.keys():
                try:
                    metadata = self.load(uri)
                    results.append(metadata)
                except Exception as e:
                    logger.warning(f"Failed to load metadata for {uri}: {e}")
        
        logger.debug(f"Retrieved {len(results)} total artifacts")
        return results
    
    def rebuild_index(self) -> int:
        """
        インデックスを再構築
        
        メタデータディレクトリ内のすべてのメタデータファイルを
        スキャンしてインデックスを再構築します。
        
        Returns:
            再構築されたエントリ数
        """
        logger.info("Rebuilding metadata index...")
        
        with self._index_lock:
            self._index = {}
            
            # すべてのメタデータファイルをスキャン
            count = 0
            for metadata_file in self.metadata_dir.glob("*.json"):
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        json_str = f.read()
                    
                    metadata = ArtifactMetadata.from_json(json_str)
                    
                    # インデックスに追加 (ファイル保存はしない)
                    self._index[metadata.uri] = {
                        "task_id": metadata.task_id,
                        "spec_name": metadata.spec_name,
                        "type": metadata.type.value,
                        "size": metadata.size,
                        "created_at": metadata.created_at.isoformat(),
                        "tags": metadata.tags,
                        "version": metadata.version,
                    }
                    count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to process {metadata_file}: {e}")
            
            # インデックスを保存
            self._save_index()
        
        logger.info(f"Rebuilt index with {count} entries")
        return count

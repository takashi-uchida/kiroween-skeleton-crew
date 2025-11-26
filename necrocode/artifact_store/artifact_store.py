"""
Artifact Store - Main API for artifact storage and management.

This module provides the main ArtifactStore class that coordinates
storage backends, compression, metadata management, and other features.
"""

import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

from necrocode.artifact_store.config import ArtifactStoreConfig
from necrocode.artifact_store.models import ArtifactMetadata, ArtifactType
from necrocode.artifact_store.storage_backend import (
    StorageBackend,
    FilesystemBackend,
    S3Backend,
    GCSBackend,
)
from necrocode.artifact_store.compression_engine import CompressionEngine
from necrocode.artifact_store.metadata_manager import MetadataManager
from necrocode.artifact_store.retention_policy import RetentionPolicy
from necrocode.artifact_store.lock_manager import ArtifactLockManager
from necrocode.artifact_store.exceptions import (
    ArtifactStoreError,
    ArtifactNotFoundError,
    StorageError,
    IntegrityError,
    StorageFullError,
    LockTimeoutError,
)


logger = logging.getLogger(__name__)


class ArtifactStore:
    """
    Artifact Storeのメインクラス
    
    成果物のアップロード、ダウンロード、削除、検索などの機能を提供します。
    ストレージバックエンド、圧縮、メタデータ管理を統合します。
    """
    
    def __init__(self, config: Optional[ArtifactStoreConfig] = None):
        """
        初期化
        
        Args:
            config: Artifact Storeの設定 (Noneの場合はデフォルト設定を使用)
        """
        self.config = config or ArtifactStoreConfig()
        
        # コンポーネントの初期化
        self.backend = self._create_backend(self.config.backend_type)
        self.metadata_manager = MetadataManager(self.config)
        self.compression_engine = CompressionEngine(
            compression_level=self.config.compression_level,
            enabled=self.config.compression_enabled
        )
        self.retention_policy = RetentionPolicy(self.config)
        
        # ロックマネージャーの初期化
        locks_dir = self.config.base_path / "locks"
        self.lock_manager = ArtifactLockManager(
            locks_dir=locks_dir,
            default_timeout=self.config.lock_timeout,
            default_retry_interval=self.config.lock_retry_interval,
        )
        
        logger.info(
            f"ArtifactStore initialized: backend={self.config.backend_type}, "
            f"compression={'enabled' if self.config.compression_enabled else 'disabled'}, "
            f"locking={'enabled' if self.config.locking_enabled else 'disabled'}"
        )
    
    def _create_backend(self, backend_type: str) -> StorageBackend:
        """
        ストレージバックエンドを作成
        
        Args:
            backend_type: バックエンドのタイプ (filesystem/s3/gcs)
            
        Returns:
            ストレージバックエンド
            
        Raises:
            ValueError: 不正なバックエンドタイプの場合
        """
        if backend_type == "filesystem":
            return FilesystemBackend(self.config.base_path)
        
        elif backend_type == "s3":
            if not self.config.s3_bucket:
                raise ValueError("s3_bucket is required for S3 backend")
            
            return S3Backend(
                bucket_name=self.config.s3_bucket,
                region=self.config.s3_region,
            )
        
        elif backend_type == "gcs":
            if not self.config.gcs_bucket:
                raise ValueError("gcs_bucket is required for GCS backend")
            if not self.config.gcs_project:
                raise ValueError("gcs_project is required for GCS backend")
            
            return GCSBackend(
                bucket_name=self.config.gcs_bucket,
                project=self.config.gcs_project,
            )
        
        else:
            raise ValueError(
                f"Unknown backend type: {backend_type}. "
                f"Must be one of: filesystem, s3, gcs"
            )

    def _generate_uri(
        self,
        spec_name: str,
        task_id: str,
        artifact_type: ArtifactType,
        version: Optional[int] = None
    ) -> str:
        """
        成果物のURIを生成
        
        Args:
            spec_name: Spec名
            task_id: タスクID
            artifact_type: 成果物のタイプ
            version: バージョン番号 (オプション、バージョニングが有効な場合)
            
        Returns:
            成果物のURI
        """
        # ファイル拡張子を決定
        extension_map = {
            ArtifactType.DIFF: "diff.txt",
            ArtifactType.LOG: "log.txt",
            ArtifactType.TEST_RESULT: "test-result.json",
        }
        filename = extension_map.get(artifact_type, "artifact.bin")
        
        # バージョニングが有効な場合はバージョン番号を追加
        if self.config.versioning_enabled and version is not None:
            base_name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
            filename = f"{base_name}.v{version}.{ext}" if ext else f"{base_name}.v{version}"
        
        # 圧縮が有効な場合は .gz を追加
        if self.config.compression_enabled:
            filename += ".gz"
        
        # URIを構築
        if self.config.backend_type == "filesystem":
            path = self.config.base_path / spec_name / task_id / filename
            return f"file://{path}"
        elif self.config.backend_type == "s3":
            return f"s3://{self.config.s3_bucket}/{spec_name}/{task_id}/{filename}"
        elif self.config.backend_type == "gcs":
            return f"gs://{self.config.gcs_bucket}/{spec_name}/{task_id}/{filename}"
        else:
            return f"{spec_name}/{task_id}/{filename}"
    
    def _calculate_checksum(self, content: bytes) -> str:
        """
        SHA256チェックサムを計算
        
        Args:
            content: チェックサムを計算する内容
            
        Returns:
            SHA256チェックサム (16進数文字列)
        """
        return hashlib.sha256(content).hexdigest()
    
    def _check_storage_quota(self, additional_size: int) -> None:
        """
        ストレージ使用量の上限をチェック
        
        Args:
            additional_size: 追加するサイズ (バイト)
            
        Raises:
            StorageFullError: ストレージ容量が上限を超える場合
        """
        # 現在の使用量を取得
        usage = self.get_storage_usage()
        current_size_gb = usage["total_size_gb"]
        
        # 追加後のサイズを計算
        additional_size_gb = additional_size / (1024 * 1024 * 1024)
        new_size_gb = current_size_gb + additional_size_gb
        
        # 上限をチェック
        max_size_gb = self.config.storage_quota.max_size_gb
        
        if new_size_gb > max_size_gb:
            logger.error(
                f"Storage quota exceeded: {new_size_gb:.2f} GB > {max_size_gb} GB"
            )
            raise StorageFullError(
                f"Storage quota exceeded: {new_size_gb:.2f} GB would exceed "
                f"limit of {max_size_gb} GB"
            )
        
        # 警告閾値をチェック
        warn_threshold = self.config.storage_quota.warn_threshold
        if new_size_gb >= (max_size_gb * warn_threshold):
            logger.warning(
                f"Storage usage approaching limit: {new_size_gb:.2f} GB / {max_size_gb} GB "
                f"({(new_size_gb / max_size_gb * 100):.1f}%)"
            )
    
    def upload(
        self,
        task_id: str,
        spec_name: str,
        artifact_type: ArtifactType,
        content: bytes,
        metadata: Optional[Dict[str, Any]] = None,
        mime_type: str = "text/plain",
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        成果物をアップロード
        
        Uses write lock to prevent concurrent writes to the same artifact.
        
        Args:
            task_id: タスクID
            spec_name: Spec名
            artifact_type: 成果物のタイプ
            content: 成果物の内容 (バイト列)
            metadata: 追加のメタデータ (オプション)
            mime_type: MIMEタイプ (デフォルト: text/plain)
            tags: タグのリスト (オプション)
            
        Returns:
            成果物のURI
            
        Raises:
            StorageError: アップロードに失敗した場合
            StorageFullError: ストレージ容量が上限を超える場合
            LockTimeoutError: ロック取得がタイムアウトした場合
            
        Requirements: 11.1, 11.2, 11.3, 11.4, 12.1, 12.2
        """
        try:
            # 1. バージョン番号を決定
            version = 1
            if self.config.versioning_enabled:
                # 既存のバージョンを取得
                existing_versions = self.get_all_versions(task_id, spec_name, artifact_type)
                if existing_versions:
                    # 最新バージョン番号 + 1
                    version = max(v.version for v in existing_versions) + 1
                    logger.debug(f"Creating new version: {version}")
            
            # 2. URIを生成
            uri = self._generate_uri(spec_name, task_id, artifact_type, version)
            logger.info(f"Uploading artifact: {uri}")
            
            # 3. 元のサイズとチェックサムを計算
            original_size = len(content)
            original_checksum = self._calculate_checksum(content)
            
            # 4. 圧縮
            compressed = False
            compressed_size = original_size
            
            if self.config.compression_enabled:
                compression_result = self.compression_engine.compress(content)
                content = compression_result.compressed_data
                compressed = True
                compressed_size = compression_result.compressed_size
                logger.debug(
                    f"Compressed artifact: {original_size} -> {compressed_size} bytes "
                    f"(ratio: {compression_result.compression_ratio:.2%})"
                )
            
            # 5. ストレージ使用量の上限をチェック
            self._check_storage_quota(compressed_size)
            
            # 6. ロックを取得してアップロード (ロックが有効な場合)
            if self.config.locking_enabled:
                with self.lock_manager.acquire_write_lock(uri):
                    # ストレージにアップロード
                    self.backend.upload(uri, content)
                    
                    # メタデータを作成して保存
                    artifact_metadata = ArtifactMetadata(
                        uri=uri,
                        task_id=task_id,
                        spec_name=spec_name,
                        type=artifact_type,
                        size=compressed_size,
                        checksum=original_checksum,
                        created_at=datetime.now(),
                        compressed=compressed,
                        original_size=original_size if compressed else None,
                        mime_type=mime_type,
                        tags=tags or [],
                        version=version,
                        metadata=metadata or {},
                    )
                    self.metadata_manager.save(artifact_metadata)
            else:
                # ロックなしでアップロード
                self.backend.upload(uri, content)
                
                artifact_metadata = ArtifactMetadata(
                    uri=uri,
                    task_id=task_id,
                    spec_name=spec_name,
                    type=artifact_type,
                    size=compressed_size,
                    checksum=original_checksum,
                    created_at=datetime.now(),
                    compressed=compressed,
                    original_size=original_size if compressed else None,
                    mime_type=mime_type,
                    tags=tags or [],
                    version=version,
                    metadata=metadata or {},
                )
                self.metadata_manager.save(artifact_metadata)
            
            logger.info(
                f"Successfully uploaded artifact: {uri} "
                f"({original_size} bytes, checksum: {original_checksum[:8]}...)"
            )
            
            return uri
            
        except (StorageFullError, LockTimeoutError):
            # Re-raise these errors without wrapping
            raise
        except Exception as e:
            logger.error(f"Failed to upload artifact: {e}")
            raise StorageError(f"Failed to upload artifact: {e}")

    def download(
        self,
        uri: str,
        verify_checksum: bool = True,
        max_retries: Optional[int] = None,
    ) -> bytes:
        """
        成果物をダウンロード
        
        Read operations do not require locks for better performance.
        
        Args:
            uri: 成果物のURI
            verify_checksum: チェックサムを検証するか (デフォルト: True)
            max_retries: 最大リトライ回数 (Noneの場合は設定値を使用)
            
        Returns:
            成果物の内容 (バイト列、解凍済み)
            
        Raises:
            ArtifactNotFoundError: 成果物が見つからない場合
            IntegrityError: チェックサム検証に失敗した場合
            StorageError: ダウンロードに失敗した場合
            
        Requirements: 11.5
        """
        if max_retries is None:
            max_retries = self.config.retry_attempts
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Downloading artifact: {uri} (attempt {attempt + 1}/{max_retries})")
                
                # 1. メタデータを読み込み
                metadata = self.metadata_manager.load(uri)
                
                # 2. ストレージからダウンロード
                content = self.backend.download(uri)
                
                # 3. 解凍
                if metadata.compressed:
                    decompression_result = self.compression_engine.decompress(content)
                    content = decompression_result.decompressed_data
                    logger.debug(
                        f"Decompressed artifact: {decompression_result.compressed_size} -> "
                        f"{decompression_result.decompressed_size} bytes"
                    )
                
                # 4. チェックサム検証
                if verify_checksum or self.config.verify_checksum:
                    actual_checksum = self._calculate_checksum(content)
                    if actual_checksum != metadata.checksum:
                        raise IntegrityError(uri, metadata.checksum, actual_checksum)
                    logger.debug(f"Checksum verified: {actual_checksum[:8]}...")
                
                logger.info(f"Successfully downloaded artifact: {uri} ({len(content)} bytes)")
                return content
                
            except (ArtifactNotFoundError, IntegrityError):
                # これらのエラーはリトライしない
                raise
            
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Download attempt {attempt + 1}/{max_retries} failed: {e}"
                )
                
                # 最後の試行でない場合は待機
                if attempt < max_retries - 1:
                    import time
                    backoff = self.config.retry_backoff_factor ** attempt
                    logger.debug(f"Waiting {backoff}s before retry...")
                    time.sleep(backoff)
        
        # すべてのリトライが失敗
        raise StorageError(
            f"Failed to download artifact after {max_retries} attempts: {last_error}"
        )
    
    def download_stream(
        self,
        uri: str,
        chunk_size: int = 8192,
    ):
        """
        成果物をストリーミングダウンロード (大きなファイル用)
        
        Args:
            uri: 成果物のURI
            chunk_size: チャンクサイズ (バイト)
            
        Yields:
            成果物の内容 (チャンク単位)
            
        Raises:
            ArtifactNotFoundError: 成果物が見つからない場合
            StorageError: ダウンロードに失敗した場合
            
        Note:
            現在の実装では全体をダウンロードしてからチャンクに分割します。
            将来的には真のストリーミングダウンロードを実装する予定です。
        """
        logger.info(f"Streaming download: {uri}")
        
        # 現在は全体をダウンロードしてからチャンクに分割
        # TODO: 真のストリーミングダウンロードを実装
        content = self.download(uri, verify_checksum=False)
        
        # チャンクに分割して yield
        for i in range(0, len(content), chunk_size):
            yield content[i:i + chunk_size]

    def delete(self, uri: str) -> None:
        """
        成果物を削除
        
        Uses write lock to prevent concurrent modifications.
        
        Args:
            uri: 成果物のURI
            
        Raises:
            ArtifactNotFoundError: 成果物が見つからない場合
            StorageError: 削除に失敗した場合
            LockTimeoutError: ロック取得がタイムアウトした場合
            
        Requirements: 11.1, 11.2
        """
        try:
            logger.info(f"Deleting artifact: {uri}")
            
            # ロックを取得して削除 (ロックが有効な場合)
            if self.config.locking_enabled:
                with self.lock_manager.acquire_write_lock(uri):
                    # ストレージから削除
                    self.backend.delete(uri)
                    
                    # メタデータを削除
                    self.metadata_manager.delete(uri)
            else:
                # ロックなしで削除
                self.backend.delete(uri)
                self.metadata_manager.delete(uri)
            
            logger.info(f"Successfully deleted artifact: {uri}")
            
        except (ArtifactNotFoundError, LockTimeoutError):
            raise
        except Exception as e:
            logger.error(f"Failed to delete artifact {uri}: {e}")
            raise StorageError(f"Failed to delete artifact: {e}")
    
    def delete_by_task_id(self, task_id: str) -> int:
        """
        タスクIDに関連するすべての成果物を削除
        
        Args:
            task_id: タスクID
            
        Returns:
            削除された成果物の数
            
        Raises:
            StorageError: 削除に失敗した場合
        """
        logger.info(f"Deleting artifacts for task_id: {task_id}")
        
        # タスクIDに関連するメタデータを取得
        metadata_list = self.metadata_manager.get_by_task_id(task_id)
        
        deleted_count = 0
        errors = []
        
        for metadata in metadata_list:
            try:
                self.delete(metadata.uri)
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete {metadata.uri}: {e}")
                errors.append((metadata.uri, str(e)))
        
        logger.info(
            f"Deleted {deleted_count}/{len(metadata_list)} artifacts for task_id: {task_id}"
        )
        
        if errors and deleted_count == 0:
            # すべて失敗した場合はエラーを投げる
            raise StorageError(
                f"Failed to delete all artifacts for task_id {task_id}: {errors[0][1]}"
            )
        
        return deleted_count
    
    def delete_by_spec_name(self, spec_name: str) -> int:
        """
        Spec名に関連するすべての成果物を削除
        
        Args:
            spec_name: Spec名
            
        Returns:
            削除された成果物の数
            
        Raises:
            StorageError: 削除に失敗した場合
        """
        logger.info(f"Deleting artifacts for spec_name: {spec_name}")
        
        # Spec名に関連するメタデータを取得
        metadata_list = self.metadata_manager.get_by_spec_name(spec_name)
        
        deleted_count = 0
        errors = []
        
        for metadata in metadata_list:
            try:
                self.delete(metadata.uri)
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete {metadata.uri}: {e}")
                errors.append((metadata.uri, str(e)))
        
        logger.info(
            f"Deleted {deleted_count}/{len(metadata_list)} artifacts for spec_name: {spec_name}"
        )
        
        if errors and deleted_count == 0:
            # すべて失敗した場合はエラーを投げる
            raise StorageError(
                f"Failed to delete all artifacts for spec_name {spec_name}: {errors[0][1]}"
            )
        
        return deleted_count

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
        
        Read operations do not require locks for better performance.
        
        Args:
            task_id: タスクID (オプション)
            spec_name: Spec名 (オプション)
            artifact_type: 成果物のタイプ (オプション)
            tags: タグのリスト (オプション、いずれかのタグにマッチ)
            created_after: この日時以降に作成された成果物 (オプション)
            created_before: この日時以前に作成された成果物 (オプション)
            
        Returns:
            条件に合致するメタデータのリスト
            
        Requirements: 11.5
        """
        logger.debug(
            f"Searching artifacts: task_id={task_id}, spec_name={spec_name}, "
            f"type={artifact_type}, tags={tags}"
        )
        
        results = self.metadata_manager.search(
            task_id=task_id,
            spec_name=spec_name,
            artifact_type=artifact_type,
            tags=tags,
            created_after=created_after,
            created_before=created_before,
        )
        
        logger.info(f"Search found {len(results)} artifacts")
        return results
    
    def get_metadata(self, uri: str) -> Optional[ArtifactMetadata]:
        """
        成果物のメタデータを取得
        
        Args:
            uri: 成果物のURI
            
        Returns:
            メタデータ、見つからない場合はNone
        """
        return self.metadata_manager.get_by_uri(uri)
    
    def exists(self, uri: str) -> bool:
        """
        成果物が存在するか確認
        
        Args:
            uri: 成果物のURI
            
        Returns:
            存在する場合はTrue、存在しない場合はFalse
        """
        return self.backend.exists(uri)
    
    def get_all_artifacts(self) -> List[ArtifactMetadata]:
        """
        すべての成果物のメタデータを取得
        
        Returns:
            すべてのメタデータのリスト
        """
        return self.metadata_manager.get_all()
    
    def verify_checksum(self, uri: str) -> bool:
        """
        成果物のチェックサムを検証
        
        Args:
            uri: 成果物のURI
            
        Returns:
            チェックサムが一致する場合はTrue
            
        Raises:
            ArtifactNotFoundError: 成果物が見つからない場合
            IntegrityError: チェックサムが一致しない場合
            StorageError: 検証に失敗した場合
        """
        try:
            logger.info(f"Verifying checksum for artifact: {uri}")
            
            # 1. メタデータを読み込み
            metadata = self.metadata_manager.load(uri)
            
            # 2. ストレージからダウンロード
            content = self.backend.download(uri)
            
            # 3. 解凍 (必要な場合)
            if metadata.compressed:
                decompression_result = self.compression_engine.decompress(content)
                content = decompression_result.decompressed_data
            
            # 4. チェックサムを計算
            actual_checksum = self._calculate_checksum(content)
            
            # 5. チェックサムを比較
            if actual_checksum != metadata.checksum:
                logger.error(
                    f"Checksum mismatch for {uri}: "
                    f"expected {metadata.checksum}, got {actual_checksum}"
                )
                raise IntegrityError(uri, metadata.checksum, actual_checksum)
            
            logger.info(f"Checksum verified successfully for {uri}")
            return True
            
        except (ArtifactNotFoundError, IntegrityError):
            raise
        except Exception as e:
            logger.error(f"Failed to verify checksum for {uri}: {e}")
            raise StorageError(f"Failed to verify checksum: {e}")
    
    def verify_all(self) -> Dict[str, Any]:
        """
        すべての成果物の整合性を検証
        
        Returns:
            検証結果の辞書:
                - total_artifacts: 検証した成果物の総数
                - valid_count: 整合性が確認された成果物の数
                - invalid_count: 整合性エラーの成果物の数
                - error_count: 検証エラーの成果物の数
                - errors: エラーのリスト (uri, error_message)
        """
        logger.info("Starting integrity verification for all artifacts")
        
        all_metadata = self.metadata_manager.get_all()
        total_artifacts = len(all_metadata)
        
        valid_count = 0
        invalid_count = 0
        error_count = 0
        errors = []
        
        for metadata in all_metadata:
            try:
                self.verify_checksum(metadata.uri)
                valid_count += 1
                
            except IntegrityError as e:
                invalid_count += 1
                errors.append({
                    "uri": metadata.uri,
                    "error": "integrity_error",
                    "message": str(e),
                    "expected_checksum": e.expected_checksum,
                    "actual_checksum": e.actual_checksum,
                })
                logger.warning(f"Integrity error for {metadata.uri}: {e}")
                
            except Exception as e:
                error_count += 1
                errors.append({
                    "uri": metadata.uri,
                    "error": "verification_error",
                    "message": str(e),
                })
                logger.warning(f"Verification error for {metadata.uri}: {e}")
        
        result = {
            "total_artifacts": total_artifacts,
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "error_count": error_count,
            "errors": errors,
        }
        
        logger.info(
            f"Integrity verification complete: "
            f"{valid_count}/{total_artifacts} valid, "
            f"{invalid_count} invalid, "
            f"{error_count} errors"
        )
        
        return result
    
    def cleanup_expired(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        保持期間を過ぎた成果物を自動的に削除
        
        Args:
            dry_run: Trueの場合、実際には削除せずに削除対象を報告
            
        Returns:
            クリーンアップ結果の辞書:
                - total_artifacts: 検査した成果物の総数
                - expired_count: 期限切れの成果物の数
                - deleted_count: 削除した成果物の数
                - failed_count: 削除に失敗した成果物の数
                - freed_bytes: 解放したバイト数
                - errors: エラーのリスト
        """
        return self.retention_policy.cleanup_expired(self, dry_run=dry_run)
    
    def get_storage_usage(self) -> Dict[str, Any]:
        """
        現在のストレージ使用量を取得
        
        Returns:
            ストレージ使用量の辞書:
                - total_size_bytes: 総使用量 (バイト)
                - total_size_mb: 総使用量 (MB)
                - total_size_gb: 総使用量 (GB)
                - artifact_count: 成果物の総数
                - quota_max_gb: 設定された上限 (GB)
                - quota_used_percent: 使用率 (%)
                - quota_warning: 警告閾値を超えているか
        """
        logger.info("Calculating storage usage")
        
        all_metadata = self.metadata_manager.get_all()
        
        total_size_bytes = sum(metadata.size for metadata in all_metadata)
        total_size_mb = total_size_bytes / (1024 * 1024)
        total_size_gb = total_size_bytes / (1024 * 1024 * 1024)
        
        quota_max_gb = self.config.storage_quota.max_size_gb
        quota_used_percent = (total_size_gb / quota_max_gb * 100) if quota_max_gb > 0 else 0
        quota_warning = quota_used_percent >= (self.config.storage_quota.warn_threshold * 100)
        
        result = {
            "total_size_bytes": total_size_bytes,
            "total_size_mb": round(total_size_mb, 4),  # More precision for small sizes
            "total_size_gb": round(total_size_gb, 6),  # More precision for small sizes
            "artifact_count": len(all_metadata),
            "quota_max_gb": quota_max_gb,
            "quota_used_percent": round(quota_used_percent, 2),
            "quota_warning": quota_warning,
        }
        
        if quota_warning:
            logger.warning(
                f"Storage usage warning: {result['quota_used_percent']}% "
                f"({result['total_size_gb']} GB / {quota_max_gb} GB)"
            )
        
        logger.info(
            f"Storage usage: {result['total_size_gb']} GB "
            f"({result['artifact_count']} artifacts)"
        )
        
        return result
    
    def get_usage_by_spec(self) -> Dict[str, Dict[str, Any]]:
        """
        Spec名ごとのストレージ使用量を取得
        
        Returns:
            Spec名をキーとした辞書:
                - size_bytes: 使用量 (バイト)
                - size_mb: 使用量 (MB)
                - size_gb: 使用量 (GB)
                - artifact_count: 成果物の数
        """
        logger.info("Calculating storage usage by spec")
        
        all_metadata = self.metadata_manager.get_all()
        
        # Spec名ごとに集計
        usage_by_spec: Dict[str, Dict[str, Any]] = {}
        
        for metadata in all_metadata:
            spec_name = metadata.spec_name
            
            if spec_name not in usage_by_spec:
                usage_by_spec[spec_name] = {
                    "size_bytes": 0,
                    "artifact_count": 0,
                }
            
            usage_by_spec[spec_name]["size_bytes"] += metadata.size
            usage_by_spec[spec_name]["artifact_count"] += 1
        
        # MB/GBを計算
        for spec_name, usage in usage_by_spec.items():
            size_bytes = usage["size_bytes"]
            usage["size_mb"] = round(size_bytes / (1024 * 1024), 2)
            usage["size_gb"] = round(size_bytes / (1024 * 1024 * 1024), 2)
        
        logger.info(f"Storage usage calculated for {len(usage_by_spec)} specs")
        
        return usage_by_spec
    
    def get_usage_by_type(self) -> Dict[str, Dict[str, Any]]:
        """
        成果物のタイプごとのストレージ使用量を取得
        
        Returns:
            タイプをキーとした辞書:
                - size_bytes: 使用量 (バイト)
                - size_mb: 使用量 (MB)
                - size_gb: 使用量 (GB)
                - artifact_count: 成果物の数
        """
        logger.info("Calculating storage usage by type")
        
        all_metadata = self.metadata_manager.get_all()
        
        # タイプごとに集計
        usage_by_type: Dict[str, Dict[str, Any]] = {}
        
        for metadata in all_metadata:
            artifact_type = metadata.type.value
            
            if artifact_type not in usage_by_type:
                usage_by_type[artifact_type] = {
                    "size_bytes": 0,
                    "artifact_count": 0,
                }
            
            usage_by_type[artifact_type]["size_bytes"] += metadata.size
            usage_by_type[artifact_type]["artifact_count"] += 1
        
        # MB/GBを計算
        for artifact_type, usage in usage_by_type.items():
            size_bytes = usage["size_bytes"]
            usage["size_mb"] = round(size_bytes / (1024 * 1024), 2)
            usage["size_gb"] = round(size_bytes / (1024 * 1024 * 1024), 2)
        
        logger.info(f"Storage usage calculated for {len(usage_by_type)} types")
        
        return usage_by_type
    
    def get_all_versions(
        self,
        task_id: str,
        spec_name: str,
        artifact_type: ArtifactType
    ) -> List[ArtifactMetadata]:
        """
        成果物の全バージョンを取得
        
        Args:
            task_id: タスクID
            spec_name: Spec名
            artifact_type: 成果物のタイプ
            
        Returns:
            全バージョンのメタデータのリスト (バージョン番号の昇順)
            
        Requirements: 12.3
        """
        logger.debug(
            f"Getting all versions: task_id={task_id}, spec_name={spec_name}, type={artifact_type}"
        )
        
        # タスクIDとSpec名でフィルタリング
        all_artifacts = self.metadata_manager.search(
            task_id=task_id,
            spec_name=spec_name,
            artifact_type=artifact_type
        )
        
        # バージョン番号でソート
        all_artifacts.sort(key=lambda x: x.version)
        
        logger.info(f"Found {len(all_artifacts)} versions")
        return all_artifacts
    
    def download_version(
        self,
        task_id: str,
        spec_name: str,
        artifact_type: ArtifactType,
        version: int,
        verify_checksum: bool = True
    ) -> bytes:
        """
        特定のバージョンをダウンロード
        
        Args:
            task_id: タスクID
            spec_name: Spec名
            artifact_type: 成果物のタイプ
            version: バージョン番号
            verify_checksum: チェックサムを検証するか (デフォルト: True)
            
        Returns:
            成果物の内容 (バイト列、解凍済み)
            
        Raises:
            ArtifactNotFoundError: 指定されたバージョンが見つからない場合
            IntegrityError: チェックサム検証に失敗した場合
            StorageError: ダウンロードに失敗した場合
            
        Requirements: 12.4
        """
        logger.info(
            f"Downloading version {version}: task_id={task_id}, spec_name={spec_name}, type={artifact_type}"
        )
        
        # URIを生成
        uri = self._generate_uri(spec_name, task_id, artifact_type, version)
        
        # ダウンロード
        return self.download(uri, verify_checksum=verify_checksum)
    
    def delete_old_versions(
        self,
        task_id: str,
        spec_name: str,
        artifact_type: ArtifactType,
        keep_latest: int = 1
    ) -> int:
        """
        古いバージョンを削除
        
        Args:
            task_id: タスクID
            spec_name: Spec名
            artifact_type: 成果物のタイプ
            keep_latest: 保持する最新バージョンの数 (デフォルト: 1)
            
        Returns:
            削除されたバージョンの数
            
        Raises:
            StorageError: 削除に失敗した場合
            
        Requirements: 12.5
        """
        logger.info(
            f"Deleting old versions (keep_latest={keep_latest}): "
            f"task_id={task_id}, spec_name={spec_name}, type={artifact_type}"
        )
        
        # 全バージョンを取得
        all_versions = self.get_all_versions(task_id, spec_name, artifact_type)
        
        if len(all_versions) <= keep_latest:
            logger.info(f"No versions to delete (total: {len(all_versions)}, keep: {keep_latest})")
            return 0
        
        # 削除対象のバージョンを決定 (古いものから)
        versions_to_delete = all_versions[:-keep_latest]
        
        deleted_count = 0
        errors = []
        
        for metadata in versions_to_delete:
            try:
                self.delete(metadata.uri)
                deleted_count += 1
                logger.debug(f"Deleted version {metadata.version}: {metadata.uri}")
            except Exception as e:
                logger.warning(f"Failed to delete version {metadata.version}: {e}")
                errors.append((metadata.uri, str(e)))
        
        logger.info(
            f"Deleted {deleted_count}/{len(versions_to_delete)} old versions "
            f"(kept latest {keep_latest})"
        )
        
        if errors and deleted_count == 0:
            # すべて失敗した場合はエラーを投げる
            raise StorageError(
                f"Failed to delete all old versions: {errors[0][1]}"
            )
        
        return deleted_count
    
    def add_tags(self, uri: str, tags: List[str]) -> None:
        """
        成果物にタグを追加
        
        Uses write lock to prevent concurrent modifications.
        
        Args:
            uri: 成果物のURI
            tags: 追加するタグのリスト
            
        Raises:
            ArtifactNotFoundError: 成果物が見つからない場合
            StorageError: タグの追加に失敗した場合
            LockTimeoutError: ロック取得がタイムアウトした場合
            
        Requirements: 13.1
        """
        try:
            logger.info(f"Adding tags to {uri}: {tags}")
            
            # ロックを取得してタグを追加 (ロックが有効な場合)
            if self.config.locking_enabled:
                with self.lock_manager.acquire_write_lock(uri):
                    # メタデータを読み込み
                    metadata = self.metadata_manager.load(uri)
                    
                    # タグを追加 (重複を避ける)
                    for tag in tags:
                        if tag not in metadata.tags:
                            metadata.tags.append(tag)
                    
                    # メタデータを保存
                    self.metadata_manager.save(metadata)
            else:
                # ロックなしでタグを追加
                metadata = self.metadata_manager.load(uri)
                
                for tag in tags:
                    if tag not in metadata.tags:
                        metadata.tags.append(tag)
                
                self.metadata_manager.save(metadata)
            
            logger.info(f"Successfully added tags to {uri}: {tags}")
            
        except (ArtifactNotFoundError, LockTimeoutError):
            raise
        except Exception as e:
            logger.error(f"Failed to add tags to {uri}: {e}")
            raise StorageError(f"Failed to add tags: {e}")
    
    def update_tags(self, uri: str, tags: List[str]) -> None:
        """
        成果物のタグを更新 (既存のタグを置き換え)
        
        Uses write lock to prevent concurrent modifications.
        
        Args:
            uri: 成果物のURI
            tags: 新しいタグのリスト
            
        Raises:
            ArtifactNotFoundError: 成果物が見つからない場合
            StorageError: タグの更新に失敗した場合
            LockTimeoutError: ロック取得がタイムアウトした場合
            
        Requirements: 13.2
        """
        try:
            logger.info(f"Updating tags for {uri}: {tags}")
            
            # ロックを取得してタグを更新 (ロックが有効な場合)
            if self.config.locking_enabled:
                with self.lock_manager.acquire_write_lock(uri):
                    # メタデータを読み込み
                    metadata = self.metadata_manager.load(uri)
                    
                    # タグを置き換え
                    metadata.tags = tags.copy()
                    
                    # メタデータを保存
                    self.metadata_manager.save(metadata)
            else:
                # ロックなしでタグを更新
                metadata = self.metadata_manager.load(uri)
                metadata.tags = tags.copy()
                self.metadata_manager.save(metadata)
            
            logger.info(f"Successfully updated tags for {uri}: {tags}")
            
        except (ArtifactNotFoundError, LockTimeoutError):
            raise
        except Exception as e:
            logger.error(f"Failed to update tags for {uri}: {e}")
            raise StorageError(f"Failed to update tags: {e}")
    
    def remove_tags(self, uri: str, tags: List[str]) -> None:
        """
        成果物からタグを削除
        
        Uses write lock to prevent concurrent modifications.
        
        Args:
            uri: 成果物のURI
            tags: 削除するタグのリスト
            
        Raises:
            ArtifactNotFoundError: 成果物が見つからない場合
            StorageError: タグの削除に失敗した場合
            LockTimeoutError: ロック取得がタイムアウトした場合
            
        Requirements: 13.4, 13.5
        """
        try:
            logger.info(f"Removing tags from {uri}: {tags}")
            
            # ロックを取得してタグを削除 (ロックが有効な場合)
            if self.config.locking_enabled:
                with self.lock_manager.acquire_write_lock(uri):
                    # メタデータを読み込み
                    metadata = self.metadata_manager.load(uri)
                    
                    # タグを削除
                    for tag in tags:
                        if tag in metadata.tags:
                            metadata.tags.remove(tag)
                    
                    # メタデータを保存
                    self.metadata_manager.save(metadata)
            else:
                # ロックなしでタグを削除
                metadata = self.metadata_manager.load(uri)
                
                for tag in tags:
                    if tag in metadata.tags:
                        metadata.tags.remove(tag)
                
                self.metadata_manager.save(metadata)
            
            logger.info(f"Successfully removed tags from {uri}: {tags}")
            
        except (ArtifactNotFoundError, LockTimeoutError):
            raise
        except Exception as e:
            logger.error(f"Failed to remove tags from {uri}: {e}")
            raise StorageError(f"Failed to remove tags: {e}")
    
    def search_by_tags(self, tags: List[str]) -> List[ArtifactMetadata]:
        """
        タグで成果物を検索
        
        Read operations do not require locks for better performance.
        
        Args:
            tags: 検索するタグのリスト (いずれかのタグにマッチ)
            
        Returns:
            条件に合致するメタデータのリスト
            
        Requirements: 13.3
        """
        logger.info(f"Searching artifacts by tags: {tags}")
        
        results = self.metadata_manager.search(tags=tags)
        
        logger.info(f"Found {len(results)} artifacts with tags: {tags}")
        return results
    
    def export_by_spec(
        self,
        spec_name: str,
        output_path: Path,
        include_metadata: bool = True,
        progress_callback: Optional[callable] = None
    ) -> Path:
        """
        Spec名に関連するすべての成果物をZIPファイルにエクスポート
        
        Args:
            spec_name: Spec名
            output_path: 出力先のZIPファイルパス
            include_metadata: メタデータを含めるか (デフォルト: True)
            progress_callback: 進捗報告用のコールバック関数 (current, total)
            
        Returns:
            作成されたZIPファイルのパス
            
        Raises:
            StorageError: エクスポートに失敗した場合
            
        Requirements: 14.1, 14.3, 14.4, 14.5
        """
        import zipfile
        import json
        
        logger.info(f"Exporting artifacts for spec_name: {spec_name} to {output_path}")
        
        try:
            # Spec名に関連する成果物を取得
            artifacts = self.metadata_manager.get_by_spec_name(spec_name)
            
            if not artifacts:
                logger.warning(f"No artifacts found for spec_name: {spec_name}")
                raise StorageError(f"No artifacts found for spec_name: {spec_name}")
            
            total_artifacts = len(artifacts)
            logger.info(f"Found {total_artifacts} artifacts to export")
            
            # 出力ディレクトリを作成
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # ZIPファイルを作成
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 各成果物をエクスポート
                for i, metadata in enumerate(artifacts):
                    try:
                        # 進捗報告
                        if progress_callback:
                            progress_callback(i + 1, total_artifacts)
                        
                        logger.debug(f"Exporting artifact {i+1}/{total_artifacts}: {metadata.uri}")
                        
                        # 成果物をダウンロード
                        content = self.download(metadata.uri, verify_checksum=False)
                        
                        # ZIPファイル内のパスを決定
                        # 例: spec_name/task_id/artifact_type.ext
                        zip_path = f"{metadata.spec_name}/{metadata.task_id}/{metadata.type.value}"
                        
                        # 拡張子を追加
                        extension_map = {
                            ArtifactType.DIFF: ".diff.txt",
                            ArtifactType.LOG: ".log.txt",
                            ArtifactType.TEST_RESULT: ".test-result.json",
                        }
                        zip_path += extension_map.get(metadata.type, ".bin")
                        
                        # バージョン番号を追加 (バージョニングが有効な場合)
                        if metadata.version > 1:
                            base_path, ext = zip_path.rsplit(".", 1) if "." in zip_path else (zip_path, "")
                            zip_path = f"{base_path}.v{metadata.version}.{ext}" if ext else f"{base_path}.v{metadata.version}"
                        
                        # ZIPに追加
                        zipf.writestr(zip_path, content)
                        
                        # メタデータを含める場合
                        if include_metadata:
                            metadata_path = f"{zip_path}.metadata.json"
                            metadata_json = json.dumps(metadata.to_dict(), indent=2)
                            zipf.writestr(metadata_path, metadata_json)
                        
                    except Exception as e:
                        logger.warning(f"Failed to export artifact {metadata.uri}: {e}")
                        # 個別のエラーは警告として記録し、処理を続行
                
                # 全体のメタデータサマリーを含める
                if include_metadata:
                    summary = {
                        "spec_name": spec_name,
                        "exported_at": datetime.now().isoformat(),
                        "total_artifacts": total_artifacts,
                        "artifacts": [
                            {
                                "uri": m.uri,
                                "task_id": m.task_id,
                                "type": m.type.value,
                                "size": m.size,
                                "created_at": m.created_at.isoformat(),
                                "version": m.version,
                            }
                            for m in artifacts
                        ]
                    }
                    zipf.writestr("export_summary.json", json.dumps(summary, indent=2))
            
            logger.info(f"Successfully exported {total_artifacts} artifacts to {output_path}")
            
            # 最終進捗報告
            if progress_callback:
                progress_callback(total_artifacts, total_artifacts)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to export artifacts for spec_name {spec_name}: {e}")
            raise StorageError(f"Failed to export artifacts: {e}")
    
    def export_by_task(
        self,
        task_id: str,
        output_path: Path,
        include_metadata: bool = True,
        progress_callback: Optional[callable] = None
    ) -> Path:
        """
        タスクIDに関連するすべての成果物をZIPファイルにエクスポート
        
        Args:
            task_id: タスクID
            output_path: 出力先のZIPファイルパス
            include_metadata: メタデータを含めるか (デフォルト: True)
            progress_callback: 進捗報告用のコールバック関数 (current, total)
            
        Returns:
            作成されたZIPファイルのパス
            
        Raises:
            StorageError: エクスポートに失敗した場合
            
        Requirements: 14.2, 14.3, 14.4, 14.5
        """
        import zipfile
        import json
        
        logger.info(f"Exporting artifacts for task_id: {task_id} to {output_path}")
        
        try:
            # タスクIDに関連する成果物を取得
            artifacts = self.metadata_manager.get_by_task_id(task_id)
            
            if not artifacts:
                logger.warning(f"No artifacts found for task_id: {task_id}")
                raise StorageError(f"No artifacts found for task_id: {task_id}")
            
            total_artifacts = len(artifacts)
            logger.info(f"Found {total_artifacts} artifacts to export")
            
            # 出力ディレクトリを作成
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # ZIPファイルを作成
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 各成果物をエクスポート
                for i, metadata in enumerate(artifacts):
                    try:
                        # 進捗報告
                        if progress_callback:
                            progress_callback(i + 1, total_artifacts)
                        
                        logger.debug(f"Exporting artifact {i+1}/{total_artifacts}: {metadata.uri}")
                        
                        # 成果物をダウンロード
                        content = self.download(metadata.uri, verify_checksum=False)
                        
                        # ZIPファイル内のパスを決定
                        # 例: task_id/artifact_type.ext
                        zip_path = f"{metadata.task_id}/{metadata.type.value}"
                        
                        # 拡張子を追加
                        extension_map = {
                            ArtifactType.DIFF: ".diff.txt",
                            ArtifactType.LOG: ".log.txt",
                            ArtifactType.TEST_RESULT: ".test-result.json",
                        }
                        zip_path += extension_map.get(metadata.type, ".bin")
                        
                        # バージョン番号を追加 (バージョニングが有効な場合)
                        if metadata.version > 1:
                            base_path, ext = zip_path.rsplit(".", 1) if "." in zip_path else (zip_path, "")
                            zip_path = f"{base_path}.v{metadata.version}.{ext}" if ext else f"{base_path}.v{metadata.version}"
                        
                        # ZIPに追加
                        zipf.writestr(zip_path, content)
                        
                        # メタデータを含める場合
                        if include_metadata:
                            metadata_path = f"{zip_path}.metadata.json"
                            metadata_json = json.dumps(metadata.to_dict(), indent=2)
                            zipf.writestr(metadata_path, metadata_json)
                        
                    except Exception as e:
                        logger.warning(f"Failed to export artifact {metadata.uri}: {e}")
                        # 個別のエラーは警告として記録し、処理を続行
                
                # 全体のメタデータサマリーを含める
                if include_metadata:
                    summary = {
                        "task_id": task_id,
                        "exported_at": datetime.now().isoformat(),
                        "total_artifacts": total_artifacts,
                        "artifacts": [
                            {
                                "uri": m.uri,
                                "spec_name": m.spec_name,
                                "type": m.type.value,
                                "size": m.size,
                                "created_at": m.created_at.isoformat(),
                                "version": m.version,
                            }
                            for m in artifacts
                        ]
                    }
                    zipf.writestr("export_summary.json", json.dumps(summary, indent=2))
            
            logger.info(f"Successfully exported {total_artifacts} artifacts to {output_path}")
            
            # 最終進捗報告
            if progress_callback:
                progress_callback(total_artifacts, total_artifacts)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to export artifacts for task_id {task_id}: {e}")
            raise StorageError(f"Failed to export artifacts: {e}")

"""
Retention Policy - Manages artifact retention and cleanup.

This module provides the RetentionPolicy class that handles
artifact retention periods and automatic cleanup of expired artifacts.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable, TYPE_CHECKING

from necrocode.artifact_store.config import ArtifactStoreConfig, RetentionPolicyConfig
from necrocode.artifact_store.models import ArtifactMetadata, ArtifactType

if TYPE_CHECKING:
    from necrocode.artifact_store.artifact_store import ArtifactStore


logger = logging.getLogger(__name__)


class RetentionPolicy:
    """
    保持期間ポリシーを管理するクラス
    
    成果物のタイプごとに保持期間を設定し、期限切れの成果物を検出・削除します。
    """
    
    def __init__(
        self,
        config: Optional[ArtifactStoreConfig] = None,
        retention_config: Optional[RetentionPolicyConfig] = None
    ):
        """
        初期化
        
        Args:
            config: Artifact Storeの設定 (retention_policyを含む)
            retention_config: 保持期間ポリシーの設定 (configより優先)
        """
        if retention_config:
            self.retention_config = retention_config
        elif config:
            self.retention_config = config.retention_policy
        else:
            self.retention_config = RetentionPolicyConfig()
        
        # タイプごとの保持期間マップ
        self._retention_days: Dict[ArtifactType, int] = {
            ArtifactType.DIFF: self.retention_config.diff_days,
            ArtifactType.LOG: self.retention_config.log_days,
            ArtifactType.TEST_RESULT: self.retention_config.test_days,
        }
        
        logger.info(
            f"RetentionPolicy initialized: "
            f"diff={self.retention_config.diff_days}d, "
            f"log={self.retention_config.log_days}d, "
            f"test={self.retention_config.test_days}d"
        )
    
    def get_retention_days(self, artifact_type: ArtifactType) -> int:
        """
        成果物のタイプに対する保持期間を取得
        
        Args:
            artifact_type: 成果物のタイプ
            
        Returns:
            保持期間 (日数)
        """
        return self._retention_days.get(artifact_type, 30)  # デフォルト30日
    
    def set_retention_days(self, artifact_type: ArtifactType, days: int) -> None:
        """
        成果物のタイプに対する保持期間を設定
        
        Args:
            artifact_type: 成果物のタイプ
            days: 保持期間 (日数)
            
        Raises:
            ValueError: 日数が負の場合
        """
        if days < 0:
            raise ValueError(f"Retention days must be non-negative, got {days}")
        
        self._retention_days[artifact_type] = days
        logger.info(f"Updated retention policy: {artifact_type.value}={days}d")
    
    def is_expired(self, metadata: ArtifactMetadata, reference_time: Optional[datetime] = None) -> bool:
        """
        成果物が期限切れかどうかを判定
        
        Args:
            metadata: 成果物のメタデータ
            reference_time: 基準時刻 (Noneの場合は現在時刻)
            
        Returns:
            期限切れの場合はTrue、そうでない場合はFalse
        """
        if reference_time is None:
            reference_time = datetime.now()
        
        retention_days = self.get_retention_days(metadata.type)
        expiration_date = metadata.created_at + timedelta(days=retention_days)
        
        return reference_time > expiration_date
    
    def get_expiration_date(self, metadata: ArtifactMetadata) -> datetime:
        """
        成果物の有効期限を取得
        
        Args:
            metadata: 成果物のメタデータ
            
        Returns:
            有効期限の日時
        """
        retention_days = self.get_retention_days(metadata.type)
        return metadata.created_at + timedelta(days=retention_days)
    
    def get_days_until_expiration(self, metadata: ArtifactMetadata) -> int:
        """
        成果物の有効期限までの日数を取得
        
        Args:
            metadata: 成果物のメタデータ
            
        Returns:
            有効期限までの日数 (負の値は期限切れを示す)
        """
        expiration_date = self.get_expiration_date(metadata)
        delta = expiration_date - datetime.now()
        return delta.days
    
    def find_expired(
        self,
        artifacts: List[ArtifactMetadata],
        reference_time: Optional[datetime] = None
    ) -> List[ArtifactMetadata]:
        """
        保持期間を過ぎた成果物を検出
        
        Args:
            artifacts: 成果物のメタデータのリスト
            reference_time: 基準時刻 (Noneの場合は現在時刻)
            
        Returns:
            期限切れの成果物のメタデータのリスト
        """
        if reference_time is None:
            reference_time = datetime.now()
        
        expired = []
        
        for metadata in artifacts:
            if self.is_expired(metadata, reference_time):
                expired.append(metadata)
                logger.debug(
                    f"Found expired artifact: {metadata.uri} "
                    f"(created: {metadata.created_at}, "
                    f"retention: {self.get_retention_days(metadata.type)}d)"
                )
        
        logger.info(
            f"Found {len(expired)} expired artifacts out of {len(artifacts)} total"
        )
        
        return expired
    
    def find_expiring_soon(
        self,
        artifacts: List[ArtifactMetadata],
        days_threshold: int = 7
    ) -> List[ArtifactMetadata]:
        """
        まもなく期限切れになる成果物を検出
        
        Args:
            artifacts: 成果物のメタデータのリスト
            days_threshold: 何日以内に期限切れになるものを検出するか
            
        Returns:
            まもなく期限切れになる成果物のメタデータのリスト
        """
        expiring_soon = []
        
        for metadata in artifacts:
            days_until_expiration = self.get_days_until_expiration(metadata)
            
            # 期限切れでなく、かつ閾値以内
            if 0 <= days_until_expiration <= days_threshold:
                expiring_soon.append(metadata)
                logger.debug(
                    f"Found artifact expiring soon: {metadata.uri} "
                    f"({days_until_expiration} days remaining)"
                )
        
        logger.info(
            f"Found {len(expiring_soon)} artifacts expiring within {days_threshold} days"
        )
        
        return expiring_soon
    
    def cleanup_expired(
        self,
        artifact_store: "ArtifactStore",
        dry_run: bool = False,
        reference_time: Optional[datetime] = None
    ) -> Dict[str, any]:
        """
        期限切れ成果物を削除
        
        Args:
            artifact_store: ArtifactStoreインスタンス
            dry_run: Trueの場合、実際には削除せずに削除対象を報告
            reference_time: 基準時刻 (Noneの場合は現在時刻)
            
        Returns:
            クリーンアップ結果の辞書:
                - total_artifacts: 検査した成果物の総数
                - expired_count: 期限切れの成果物の数
                - deleted_count: 削除した成果物の数
                - failed_count: 削除に失敗した成果物の数
                - freed_bytes: 解放したバイト数
                - errors: エラーのリスト
        """
        if reference_time is None:
            reference_time = datetime.now()
        
        logger.info(
            f"Starting cleanup (dry_run={dry_run}, reference_time={reference_time})"
        )
        
        # すべての成果物を取得
        all_artifacts = artifact_store.get_all_artifacts()
        
        # 期限切れの成果物を検出
        expired_artifacts = self.find_expired(all_artifacts, reference_time)
        
        deleted_count = 0
        failed_count = 0
        freed_bytes = 0
        errors = []
        
        # 期限切れの成果物を削除
        for metadata in expired_artifacts:
            try:
                if dry_run:
                    logger.info(f"[DRY RUN] Would delete: {metadata.uri}")
                    deleted_count += 1
                    freed_bytes += metadata.size
                else:
                    # 実際に削除
                    artifact_store.delete(metadata.uri)
                    deleted_count += 1
                    freed_bytes += metadata.size
                    logger.info(
                        f"Deleted expired artifact: {metadata.uri} "
                        f"(created: {metadata.created_at}, size: {metadata.size} bytes)"
                    )
            
            except Exception as e:
                failed_count += 1
                error_msg = f"Failed to delete {metadata.uri}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        # クリーンアップ結果をログに記録
        result = {
            "timestamp": reference_time.isoformat(),
            "dry_run": dry_run,
            "total_artifacts": len(all_artifacts),
            "expired_count": len(expired_artifacts),
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "freed_bytes": freed_bytes,
            "freed_mb": round(freed_bytes / (1024 * 1024), 2),
            "errors": errors,
        }
        
        logger.info(
            f"Cleanup completed: "
            f"deleted={deleted_count}/{len(expired_artifacts)}, "
            f"failed={failed_count}, "
            f"freed={result['freed_mb']}MB"
        )
        
        # クリーンアップログを記録
        self._log_cleanup_result(result)
        
        return result
    
    def _log_cleanup_result(self, result: Dict[str, any]) -> None:
        """
        クリーンアップ結果をログファイルに記録
        
        Args:
            result: クリーンアップ結果の辞書
        """
        # 簡易的なログ記録 (将来的にはより詳細なログファイルに記録)
        logger.info(f"Cleanup result: {result}")
        
        # エラーがあった場合は警告レベルでログ
        if result["failed_count"] > 0:
            logger.warning(
                f"Cleanup had {result['failed_count']} failures. "
                f"Errors: {result['errors']}"
            )


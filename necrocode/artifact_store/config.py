"""
Configuration for Artifact Store.

Defines configuration classes and default settings.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional
import os


@dataclass
class RetentionPolicyConfig:
    """
    保持期間ポリシーの設定
    
    Attributes:
        diff_days: diffの保持期間 (日数)
        log_days: logの保持期間 (日数)
        test_days: test結果の保持期間 (日数)
    """
    diff_days: int = 30
    log_days: int = 7
    test_days: int = 14


@dataclass
class StorageQuotaConfig:
    """
    ストレージ使用量の上限設定
    
    Attributes:
        max_size_gb: 最大ストレージサイズ (GB)
        warn_threshold: 警告を出す閾値 (0.0-1.0)
    """
    max_size_gb: float = 100.0
    warn_threshold: float = 0.8


@dataclass
class ArtifactStoreConfig:
    """
    Artifact Storeの設定
    
    Attributes:
        backend_type: ストレージバックエンドのタイプ (filesystem/s3/gcs)
        base_path: ベースパス (filesystemバックエンドの場合)
        compression_enabled: 圧縮を有効にするか
        verify_checksum: チェックサムを検証するか
        versioning_enabled: バージョニングを有効にするか
        retention_policy: 保持期間ポリシー
        storage_quota: ストレージ使用量の上限
        lock_timeout: ロック取得のタイムアウト (秒)
        retry_attempts: リトライ回数
        retry_backoff_factor: リトライのバックオフ係数
        s3_bucket: S3バケット名 (S3バックエンドの場合)
        s3_region: S3リージョン (S3バックエンドの場合)
        gcs_bucket: GCSバケット名 (GCSバックエンドの場合)
        gcs_project: GCSプロジェクトID (GCSバックエンドの場合)
    """
    backend_type: str = "filesystem"
    base_path: Path = field(default_factory=lambda: Path.home() / ".necrocode" / "artifacts")
    compression_enabled: bool = True
    compression_level: int = 6
    verify_checksum: bool = True
    versioning_enabled: bool = False
    retention_policy: RetentionPolicyConfig = field(default_factory=RetentionPolicyConfig)
    storage_quota: StorageQuotaConfig = field(default_factory=StorageQuotaConfig)
    
    # Locking settings
    locking_enabled: bool = True
    lock_timeout: float = 30.0
    lock_retry_interval: float = 0.1
    
    # Retry settings
    retry_attempts: int = 3
    retry_backoff_factor: float = 2.0
    
    # S3 backend settings
    s3_bucket: Optional[str] = None
    s3_region: str = "us-east-1"
    
    # GCS backend settings
    gcs_bucket: Optional[str] = None
    gcs_project: Optional[str] = None

    def __post_init__(self):
        """設定の検証と初期化"""
        # base_pathをPathオブジェクトに変換
        if isinstance(self.base_path, str):
            self.base_path = Path(self.base_path).expanduser()
        
        # backend_typeの検証
        valid_backends = ["filesystem", "s3", "gcs"]
        if self.backend_type not in valid_backends:
            raise ValueError(
                f"Invalid backend_type: {self.backend_type}. "
                f"Must be one of {valid_backends}"
            )
        
        # S3バックエンドの検証
        if self.backend_type == "s3" and not self.s3_bucket:
            raise ValueError("s3_bucket is required when backend_type is 's3'")
        
        # GCSバックエンドの検証
        if self.backend_type == "gcs":
            if not self.gcs_bucket:
                raise ValueError("gcs_bucket is required when backend_type is 'gcs'")
            if not self.gcs_project:
                raise ValueError("gcs_project is required when backend_type is 'gcs'")

    @classmethod
    def from_dict(cls, data: Dict) -> "ArtifactStoreConfig":
        """辞書から設定を作成"""
        # retention_policyの処理
        retention_data = data.get("retention_policy", {})
        retention_policy = RetentionPolicyConfig(
            diff_days=retention_data.get("diff", 30),
            log_days=retention_data.get("log", 7),
            test_days=retention_data.get("test", 14),
        )
        
        # storage_quotaの処理
        quota_data = data.get("storage_quota", {})
        storage_quota = StorageQuotaConfig(
            max_size_gb=quota_data.get("max_size_gb", 100.0),
            warn_threshold=quota_data.get("warn_threshold", 0.8),
        )
        
        return cls(
            backend_type=data.get("backend_type", "filesystem"),
            base_path=Path(data.get("base_path", "~/.necrocode/artifacts")).expanduser(),
            compression_enabled=data.get("compression_enabled", True),
            compression_level=data.get("compression_level", 6),
            verify_checksum=data.get("verify_checksum", True),
            versioning_enabled=data.get("versioning_enabled", False),
            retention_policy=retention_policy,
            storage_quota=storage_quota,
            locking_enabled=data.get("locking_enabled", True),
            lock_timeout=data.get("lock_timeout", 30.0),
            lock_retry_interval=data.get("lock_retry_interval", 0.1),
            retry_attempts=data.get("retry_attempts", 3),
            retry_backoff_factor=data.get("retry_backoff_factor", 2.0),
            s3_bucket=data.get("s3_bucket"),
            s3_region=data.get("s3_region", "us-east-1"),
            gcs_bucket=data.get("gcs_bucket"),
            gcs_project=data.get("gcs_project"),
        )

    @classmethod
    def from_env(cls) -> "ArtifactStoreConfig":
        """環境変数から設定を作成"""
        return cls(
            backend_type=os.getenv("ARTIFACT_STORE_BACKEND", "filesystem"),
            base_path=Path(os.getenv(
                "ARTIFACT_STORE_BASE_PATH",
                "~/.necrocode/artifacts"
            )).expanduser(),
            compression_enabled=os.getenv("ARTIFACT_STORE_COMPRESSION", "true").lower() == "true",
            compression_level=int(os.getenv("ARTIFACT_STORE_COMPRESSION_LEVEL", "6")),
            verify_checksum=os.getenv("ARTIFACT_STORE_VERIFY_CHECKSUM", "true").lower() == "true",
            versioning_enabled=os.getenv("ARTIFACT_STORE_VERSIONING", "false").lower() == "true",
            s3_bucket=os.getenv("ARTIFACT_STORE_S3_BUCKET"),
            s3_region=os.getenv("ARTIFACT_STORE_S3_REGION", "us-east-1"),
            gcs_bucket=os.getenv("ARTIFACT_STORE_GCS_BUCKET"),
            gcs_project=os.getenv("ARTIFACT_STORE_GCS_PROJECT"),
        )

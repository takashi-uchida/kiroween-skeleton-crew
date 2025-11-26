#!/usr/bin/env python3
"""
S3 Backend Setup Example

このサンプルは、S3バックエンドを使用したArtifact Storeの設定方法を示します。
"""

import os
from necrocode.artifact_store import (
    ArtifactStore,
    ArtifactStoreConfig,
    ArtifactType
)


def example_basic_s3_setup():
    """基本的なS3バックエンドの設定"""
    print("=== Basic S3 Backend Setup ===\n")
    
    # 環境変数から認証情報を取得
    config = ArtifactStoreConfig(
        backend_type="s3",
        s3_bucket="my-necrocode-artifacts",
        s3_region="us-west-2",
        s3_access_key=os.getenv("AWS_ACCESS_KEY_ID"),
        s3_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        compression_enabled=True,
        verify_checksum=True
    )
    
    print(f"Backend Type: {config.backend_type}")
    print(f"S3 Bucket: {config.s3_bucket}")
    print(f"S3 Region: {config.s3_region}")
    print(f"Compression: {config.compression_enabled}")
    print(f"Checksum Verification: {config.verify_checksum}\n")
    
    # Artifact Storeを初期化
    store = ArtifactStore(config)
    print("✓ Artifact Store initialized with S3 backend\n")
    
    return store


def example_s3_with_custom_endpoint():
    """カスタムエンドポイント（MinIO等）を使用したS3バックエンドの設定"""
    print("=== S3 Backend with Custom Endpoint (MinIO) ===\n")
    
    config = ArtifactStoreConfig(
        backend_type="s3",
        s3_bucket="necrocode-artifacts",
        s3_region="us-east-1",
        s3_endpoint_url="http://localhost:9000",  # MinIOのエンドポイント
        s3_access_key="minioadmin",
        s3_secret_key="minioadmin",
        compression_enabled=True
    )
    
    print(f"Backend Type: {config.backend_type}")
    print(f"S3 Bucket: {config.s3_bucket}")
    print(f"S3 Endpoint: {config.s3_endpoint_url}")
    print(f"S3 Region: {config.s3_region}\n")
    
    store = ArtifactStore(config)
    print("✓ Artifact Store initialized with MinIO backend\n")
    
    return store


def example_s3_with_iam_role():
    """IAMロールを使用したS3バックエンドの設定"""
    print("=== S3 Backend with IAM Role ===\n")
    
    # IAMロールを使用する場合、access_keyとsecret_keyは不要
    config = ArtifactStoreConfig(
        backend_type="s3",
        s3_bucket="my-necrocode-artifacts",
        s3_region="us-west-2",
        # s3_access_keyとs3_secret_keyを指定しない
        # boto3が自動的にIAMロールから認証情報を取得
        compression_enabled=True
    )
    
    print(f"Backend Type: {config.backend_type}")
    print(f"S3 Bucket: {config.s3_bucket}")
    print(f"S3 Region: {config.s3_region}")
    print("Authentication: IAM Role (automatic)\n")
    
    store = ArtifactStore(config)
    print("✓ Artifact Store initialized with IAM role authentication\n")
    
    return store


def example_s3_with_server_side_encryption():
    """サーバーサイド暗号化を使用したS3バックエンドの設定"""
    print("=== S3 Backend with Server-Side Encryption ===\n")
    
    config = ArtifactStoreConfig(
        backend_type="s3",
        s3_bucket="my-necrocode-artifacts",
        s3_region="us-west-2",
        s3_access_key=os.getenv("AWS_ACCESS_KEY_ID"),
        s3_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        s3_server_side_encryption="AES256",  # または "aws:kms"
        compression_enabled=True
    )
    
    print(f"Backend Type: {config.backend_type}")
    print(f"S3 Bucket: {config.s3_bucket}")
    print(f"S3 Region: {config.s3_region}")
    print(f"Server-Side Encryption: {config.s3_server_side_encryption}\n")
    
    store = ArtifactStore(config)
    print("✓ Artifact Store initialized with server-side encryption\n")
    
    return store


def example_upload_and_download():
    """S3バックエンドでのアップロードとダウンロード"""
    print("=== Upload and Download with S3 Backend ===\n")
    
    # 環境変数をチェック
    if not os.getenv("AWS_ACCESS_KEY_ID") or not os.getenv("AWS_SECRET_ACCESS_KEY"):
        print("⚠ AWS credentials not found in environment variables")
        print("Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY to run this example\n")
        return
    
    config = ArtifactStoreConfig(
        backend_type="s3",
        s3_bucket=os.getenv("S3_BUCKET", "my-necrocode-artifacts"),
        s3_region=os.getenv("AWS_REGION", "us-west-2"),
        s3_access_key=os.getenv("AWS_ACCESS_KEY_ID"),
        s3_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        compression_enabled=True
    )
    
    store = ArtifactStore(config)
    print("✓ Artifact Store initialized\n")
    
    # アップロード
    print("Uploading artifact to S3...")
    content = b"This is a test artifact stored in S3"
    uri = store.upload(
        task_id="1.1",
        spec_name="s3-test",
        artifact_type=ArtifactType.DIFF,
        content=content,
        tags=["s3", "test"]
    )
    print(f"✓ Uploaded: {uri}\n")
    
    # ダウンロード
    print("Downloading artifact from S3...")
    downloaded = store.download(uri)
    print(f"✓ Downloaded: {len(downloaded)} bytes")
    print(f"Content matches: {downloaded == content}\n")
    
    # メタデータを取得
    print("Getting metadata...")
    metadata = store.get_metadata(uri)
    print(f"Task ID: {metadata.task_id}")
    print(f"Spec Name: {metadata.spec_name}")
    print(f"Type: {metadata.type.value}")
    print(f"Size: {metadata.size} bytes")
    print(f"Tags: {metadata.tags}\n")
    
    # 削除
    print("Deleting artifact from S3...")
    store.delete(uri)
    print("✓ Deleted\n")


def example_s3_configuration_best_practices():
    """S3バックエンドの設定ベストプラクティス"""
    print("=== S3 Configuration Best Practices ===\n")
    
    config = ArtifactStoreConfig(
        backend_type="s3",
        s3_bucket="my-necrocode-artifacts",
        s3_region="us-west-2",
        
        # 認証情報は環境変数から取得
        s3_access_key=os.getenv("AWS_ACCESS_KEY_ID"),
        s3_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        
        # 圧縮を有効化してストレージコストを削減
        compression_enabled=True,
        
        # チェックサム検証を有効化してデータ整合性を保証
        verify_checksum=True,
        
        # 保持期間ポリシーを設定
        retention_policy={
            "diff": 90,   # 本番環境では長めに設定
            "log": 30,
            "test": 60
        },
        
        # ストレージクォータを設定
        max_storage_gb=500,
        storage_warn_threshold=0.8,
        
        # リトライ設定
        lock_retry_count=5,
        lock_retry_delay=2.0
    )
    
    print("Configuration:")
    print(f"  Backend: {config.backend_type}")
    print(f"  Bucket: {config.s3_bucket}")
    print(f"  Region: {config.s3_region}")
    print(f"  Compression: {config.compression_enabled}")
    print(f"  Checksum Verification: {config.verify_checksum}")
    print(f"  Retention Policy: {config.retention_policy}")
    print(f"  Max Storage: {config.max_storage_gb} GB")
    print(f"  Warn Threshold: {config.storage_warn_threshold * 100}%\n")
    
    store = ArtifactStore(config)
    print("✓ Artifact Store initialized with best practices\n")
    
    return store


def main():
    print("=== S3 Backend Setup Examples ===\n")
    
    # 基本的なS3設定
    print("1. Basic S3 Setup")
    print("-" * 50)
    try:
        example_basic_s3_setup()
    except Exception as e:
        print(f"⚠ Error: {e}\n")
    
    # カスタムエンドポイント（MinIO）
    print("\n2. S3 with Custom Endpoint (MinIO)")
    print("-" * 50)
    try:
        example_s3_with_custom_endpoint()
    except Exception as e:
        print(f"⚠ Error: {e}\n")
    
    # IAMロール
    print("\n3. S3 with IAM Role")
    print("-" * 50)
    try:
        example_s3_with_iam_role()
    except Exception as e:
        print(f"⚠ Error: {e}\n")
    
    # サーバーサイド暗号化
    print("\n4. S3 with Server-Side Encryption")
    print("-" * 50)
    try:
        example_s3_with_server_side_encryption()
    except Exception as e:
        print(f"⚠ Error: {e}\n")
    
    # アップロードとダウンロード
    print("\n5. Upload and Download")
    print("-" * 50)
    try:
        example_upload_and_download()
    except Exception as e:
        print(f"⚠ Error: {e}\n")
    
    # ベストプラクティス
    print("\n6. Configuration Best Practices")
    print("-" * 50)
    try:
        example_s3_configuration_best_practices()
    except Exception as e:
        print(f"⚠ Error: {e}\n")
    
    print("=== Examples completed ===")


if __name__ == "__main__":
    main()

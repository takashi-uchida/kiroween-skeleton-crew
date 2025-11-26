"""
Example demonstrating error handling and retry functionality in Artifact Store.

This example shows:
1. Network error retry with exponential backoff
2. Storage full error detection
3. Permission error detection
4. Error logging
"""

import logging
import tempfile
from pathlib import Path

from necrocode.artifact_store.artifact_store import ArtifactStore
from necrocode.artifact_store.config import ArtifactStoreConfig, StorageQuotaConfig
from necrocode.artifact_store.models import ArtifactType
from necrocode.artifact_store.exceptions import (
    StorageFullError,
    PermissionError,
    ArtifactNotFoundError,
)

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def example_basic_error_handling():
    """基本的なエラーハンドリングの例"""
    print("\n=== Example 1: Basic Error Handling ===\n")
    
    # 一時ディレクトリを作成
    with tempfile.TemporaryDirectory() as temp_dir:
        # Artifact Storeを初期化
        config = ArtifactStoreConfig(
            backend_type="filesystem",
            base_path=Path(temp_dir) / "artifacts",
            compression_enabled=True,
        )
        store = ArtifactStore(config)
        
        # 成果物をアップロード
        content = b"Test artifact content"
        uri = store.upload(
            task_id="1.1",
            spec_name="test-spec",
            artifact_type=ArtifactType.DIFF,
            content=content,
        )
        print(f"✓ Uploaded artifact: {uri}")
        
        # 存在しない成果物をダウンロードしようとする
        try:
            store.download("file:///nonexistent/artifact.txt")
        except ArtifactNotFoundError as e:
            print(f"✓ Caught expected error: {e}")
        
        # 成果物をダウンロード
        downloaded = store.download(uri)
        print(f"✓ Downloaded artifact: {len(downloaded)} bytes")
        
        # 成果物を削除
        store.delete(uri)
        print(f"✓ Deleted artifact: {uri}")


def example_storage_quota():
    """ストレージ容量制限の例"""
    print("\n=== Example 2: Storage Quota ===\n")
    
    # 一時ディレクトリを作成
    with tempfile.TemporaryDirectory() as temp_dir:
        # 非常に小さい容量制限を設定
        config = ArtifactStoreConfig(
            backend_type="filesystem",
            base_path=Path(temp_dir) / "artifacts",
            compression_enabled=False,
            storage_quota=StorageQuotaConfig(
                max_size_gb=0.000001,  # 1 byte (非常に小さい)
                warn_threshold=0.5,
            ),
        )
        store = ArtifactStore(config)
        
        # 大きな成果物をアップロードしようとする
        large_content = b"X" * 1024 * 1024  # 1 MB
        
        try:
            store.upload(
                task_id="1.1",
                spec_name="test-spec",
                artifact_type=ArtifactType.LOG,
                content=large_content,
            )
            print("✗ Should have raised StorageFullError")
        except StorageFullError as e:
            print(f"✓ Caught expected StorageFullError: {e}")


def example_retry_behavior():
    """リトライ動作の例 (シミュレーション)"""
    print("\n=== Example 3: Retry Behavior ===\n")
    
    print("Note: This example demonstrates the retry configuration.")
    print("In real scenarios, network errors would trigger automatic retries.")
    print("The retry handler will:")
    print("  - Retry up to 3 times for network errors")
    print("  - Use exponential backoff (1s, 2s, 4s)")
    print("  - Not retry for non-retryable errors (NotFound, PermissionError, etc.)")
    print("  - Log all retry attempts and failures")
    
    # 一時ディレクトリを作成
    with tempfile.TemporaryDirectory() as temp_dir:
        config = ArtifactStoreConfig(
            backend_type="filesystem",
            base_path=Path(temp_dir) / "artifacts",
            retry_attempts=3,
            retry_backoff_factor=2.0,
        )
        store = ArtifactStore(config)
        
        print(f"\n✓ Configured with:")
        print(f"  - Max retry attempts: {config.retry_attempts}")
        print(f"  - Backoff factor: {config.retry_backoff_factor}")
        
        # 通常の操作 (リトライは発生しない)
        content = b"Test content"
        uri = store.upload(
            task_id="1.1",
            spec_name="test-spec",
            artifact_type=ArtifactType.DIFF,
            content=content,
        )
        print(f"\n✓ Successfully uploaded without retries: {uri}")
        
        # ダウンロード (リトライ設定を使用)
        downloaded = store.download(uri, max_retries=3)
        print(f"✓ Successfully downloaded with retry config: {len(downloaded)} bytes")


def example_error_logging():
    """エラーログの例"""
    print("\n=== Example 4: Error Logging ===\n")
    
    print("All errors are automatically logged:")
    print("  - Network errors: WARNING level (with retry info)")
    print("  - Storage errors: ERROR level")
    print("  - Permission errors: ERROR level")
    print("  - Not found errors: INFO level (expected errors)")
    
    # 一時ディレクトリを作成
    with tempfile.TemporaryDirectory() as temp_dir:
        config = ArtifactStoreConfig(
            backend_type="filesystem",
            base_path=Path(temp_dir) / "artifacts",
        )
        store = ArtifactStore(config)
        
        # エラーを発生させてログを確認
        try:
            store.download("file:///nonexistent/artifact.txt")
        except ArtifactNotFoundError:
            print("\n✓ Error was logged (check logs above)")


def main():
    """メイン関数"""
    print("=" * 60)
    print("Artifact Store - Error Handling and Retry Examples")
    print("=" * 60)
    
    try:
        example_basic_error_handling()
        example_storage_quota()
        example_retry_behavior()
        example_error_logging()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

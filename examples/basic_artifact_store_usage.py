#!/usr/bin/env python3
"""
Basic Artifact Store Usage Example

このサンプルは、Artifact Storeの基本的な使用方法を示します。
"""

import tempfile
from pathlib import Path
from necrocode.artifact_store import (
    ArtifactStore,
    ArtifactStoreConfig,
    ArtifactType,
    ArtifactNotFoundError
)


def main():
    print("=== Artifact Store Basic Usage Example ===\n")
    
    # 一時ディレクトリを使用
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. 設定を作成
        print("1. Creating configuration...")
        config = ArtifactStoreConfig(
            backend_type="filesystem",
            base_path=tmpdir,
            compression_enabled=True,
            verify_checksum=True
        )
        print(f"   Base path: {tmpdir}")
        print(f"   Compression: {config.compression_enabled}")
        print(f"   Checksum verification: {config.verify_checksum}\n")
        
        # 2. Artifact Storeを初期化
        print("2. Initializing Artifact Store...")
        store = ArtifactStore(config)
        print("   ✓ Artifact Store initialized\n")
        
        # 3. 成果物をアップロード
        print("3. Uploading artifacts...")
        
        # DIFFをアップロード
        diff_content = b"""
--- a/src/main.py
+++ b/src/main.py
@@ -1,3 +1,4 @@
+import logging
 def main():
-    print("Hello")
+    logging.info("Hello, World!")
"""
        diff_uri = store.upload(
            task_id="1.1",
            spec_name="chat-app",
            artifact_type=ArtifactType.DIFF,
            content=diff_content,
            tags=["backend", "logging"]
        )
        print(f"   ✓ Uploaded DIFF: {diff_uri}")
        
        # LOGをアップロード
        log_content = b"""
[2024-01-01 10:00:00] INFO: Starting task execution
[2024-01-01 10:00:01] INFO: Processing file main.py
[2024-01-01 10:00:02] INFO: Task completed successfully
"""
        log_uri = store.upload(
            task_id="1.1",
            spec_name="chat-app",
            artifact_type=ArtifactType.LOG,
            content=log_content,
            tags=["backend"]
        )
        print(f"   ✓ Uploaded LOG: {log_uri}")
        
        # TEST_RESULTをアップロード
        test_content = b"""
{
    "tests_run": 10,
    "tests_passed": 9,
    "tests_failed": 1,
    "failures": [
        {
            "test": "test_authentication",
            "error": "AssertionError: Expected 200, got 401"
        }
    ]
}
"""
        test_uri = store.upload(
            task_id="1.2",
            spec_name="chat-app",
            artifact_type=ArtifactType.TEST_RESULT,
            content=test_content,
            tags=["backend", "auth"]
        )
        print(f"   ✓ Uploaded TEST_RESULT: {test_uri}\n")
        
        # 4. 成果物をダウンロード
        print("4. Downloading artifacts...")
        downloaded_diff = store.download(diff_uri)
        print(f"   ✓ Downloaded DIFF: {len(downloaded_diff)} bytes")
        print(f"   Content matches: {downloaded_diff == diff_content}")
        
        downloaded_log = store.download(log_uri)
        print(f"   ✓ Downloaded LOG: {len(downloaded_log)} bytes")
        
        downloaded_test = store.download(test_uri)
        print(f"   ✓ Downloaded TEST_RESULT: {len(downloaded_test)} bytes\n")
        
        # 5. メタデータを取得
        print("5. Getting metadata...")
        metadata = store.get_metadata(diff_uri)
        print(f"   URI: {metadata.uri}")
        print(f"   Task ID: {metadata.task_id}")
        print(f"   Spec Name: {metadata.spec_name}")
        print(f"   Type: {metadata.type.value}")
        print(f"   Size: {metadata.size} bytes")
        print(f"   Compressed: {metadata.compressed}")
        if metadata.compressed:
            print(f"   Original Size: {metadata.original_size} bytes")
            compression_ratio = (1 - metadata.size / metadata.original_size) * 100
            print(f"   Compression Ratio: {compression_ratio:.1f}%")
        print(f"   Checksum: {metadata.checksum[:16]}...")
        print(f"   Tags: {metadata.tags}")
        print(f"   Created: {metadata.created_at}\n")
        
        # 6. 成果物を検索
        print("6. Searching artifacts...")
        
        # Spec名で検索
        artifacts = store.search(spec_name="chat-app")
        print(f"   Found {len(artifacts)} artifacts for spec 'chat-app'")
        
        # タスクIDで検索
        artifacts = store.search(task_id="1.1")
        print(f"   Found {len(artifacts)} artifacts for task '1.1'")
        
        # タイプで検索
        artifacts = store.search(artifact_type=ArtifactType.DIFF)
        print(f"   Found {len(artifacts)} DIFF artifacts")
        
        # タグで検索
        artifacts = store.search(tags=["backend"])
        print(f"   Found {len(artifacts)} artifacts with tag 'backend'")
        
        # 複数条件で検索
        artifacts = store.search(spec_name="chat-app", artifact_type=ArtifactType.LOG)
        print(f"   Found {len(artifacts)} LOG artifacts for 'chat-app'\n")
        
        # 7. タグを追加
        print("7. Adding tags...")
        store.add_tags(diff_uri, ["reviewed", "approved"])
        metadata = store.get_metadata(diff_uri)
        print(f"   Updated tags: {metadata.tags}\n")
        
        # 8. ストレージ使用量を取得
        print("8. Getting storage usage...")
        usage = store.get_storage_usage()
        print(f"   Total size: {usage['total_size_bytes']} bytes ({usage['total_size_mb']:.2f} MB)")
        print(f"   Total count: {usage['artifact_count']} artifacts")
        print(f"   Quota: {usage['quota_used_percent']:.1f}% of {usage['quota_max_gb']} GB")
        
        # Spec別の使用量
        usage_by_spec = store.get_usage_by_spec()
        print(f"   By spec:")
        for spec_name, spec_usage in usage_by_spec.items():
            print(f"     {spec_name}: {spec_usage['size_bytes']} bytes ({spec_usage['artifact_count']} artifacts)")
        
        # タイプ別の使用量
        usage_by_type = store.get_usage_by_type()
        print(f"   By type:")
        for artifact_type, type_usage in usage_by_type.items():
            print(f"     {artifact_type}: {type_usage['size_bytes']} bytes ({type_usage['artifact_count']} artifacts)\n")
        
        # 9. 成果物を削除
        print("9. Deleting artifacts...")
        store.delete(test_uri)
        print(f"   ✓ Deleted: {test_uri}")
        
        # 削除された成果物をダウンロードしようとする
        try:
            store.download(test_uri)
            print("   ✗ Should have raised ArtifactNotFoundError")
        except ArtifactNotFoundError:
            print("   ✓ Confirmed artifact was deleted\n")
        
        # 10. タスクIDで一括削除
        print("10. Deleting by task ID...")
        deleted_count = store.delete_by_task_id("1.1")
        print(f"   ✓ Deleted {deleted_count} artifacts for task '1.1'\n")
        
        # 11. 最終的なストレージ使用量
        print("11. Final storage usage...")
        usage = store.get_storage_usage()
        print(f"   Total size: {usage['total_size_bytes']} bytes ({usage['total_size_mb']:.2f} MB)")
        print(f"   Total count: {usage['artifact_count']} artifacts\n")
        
        print("=== Example completed successfully ===")


if __name__ == "__main__":
    main()

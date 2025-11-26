"""
Example: Retention Policy Cleanup Demo

Demonstrates cleanup of expired artifacts by simulating old artifacts.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from necrocode.artifact_store.artifact_store import ArtifactStore
from necrocode.artifact_store.config import ArtifactStoreConfig, RetentionPolicyConfig
from necrocode.artifact_store.models import ArtifactType, ArtifactMetadata


def main():
    print("=== Retention Policy Cleanup Demo ===\n")
    
    # 1. 短い保持期間で設定を作成 (テスト用)
    retention_config = RetentionPolicyConfig(
        diff_days=30,
        log_days=7,
        test_days=14,
    )
    
    config = ArtifactStoreConfig(
        backend_type="filesystem",
        base_path=Path("/tmp/artifact-store-cleanup-demo"),
        retention_policy=retention_config,
    )
    
    # 2. Artifact Storeを初期化
    store = ArtifactStore(config)
    print(f"Initialized ArtifactStore at {config.base_path}\n")
    
    # 3. 新しい成果物をアップロード
    print("Uploading recent artifacts...")
    store.upload(
        task_id="1.1",
        spec_name="test-spec",
        artifact_type=ArtifactType.DIFF,
        content=b"Recent diff content",
    )
    
    store.upload(
        task_id="1.2",
        spec_name="test-spec",
        artifact_type=ArtifactType.LOG,
        content=b"Recent log content",
    )
    print("Uploaded 2 recent artifacts\n")
    
    # 4. 古い成果物をシミュレート (メタデータを直接操作)
    print("Simulating old artifacts...")
    
    # 40日前のdiff (期限切れ: 30日保持)
    old_diff_uri = store.upload(
        task_id="0.1",
        spec_name="old-spec",
        artifact_type=ArtifactType.DIFF,
        content=b"Old diff content",
    )
    old_diff_metadata = store.get_metadata(old_diff_uri)
    old_diff_metadata.created_at = datetime.now() - timedelta(days=40)
    store.metadata_manager.save(old_diff_metadata)
    print(f"  Created old diff (40 days ago): {old_diff_uri}")
    
    # 10日前のlog (期限切れ: 7日保持)
    old_log_uri = store.upload(
        task_id="0.2",
        spec_name="old-spec",
        artifact_type=ArtifactType.LOG,
        content=b"Old log content",
    )
    old_log_metadata = store.get_metadata(old_log_uri)
    old_log_metadata.created_at = datetime.now() - timedelta(days=10)
    store.metadata_manager.save(old_log_metadata)
    print(f"  Created old log (10 days ago): {old_log_uri}")
    
    # 20日前のtest (期限切れ: 14日保持)
    old_test_uri = store.upload(
        task_id="0.3",
        spec_name="old-spec",
        artifact_type=ArtifactType.TEST_RESULT,
        content=b'{"status": "passed"}',
    )
    old_test_metadata = store.get_metadata(old_test_uri)
    old_test_metadata.created_at = datetime.now() - timedelta(days=20)
    store.metadata_manager.save(old_test_metadata)
    print(f"  Created old test (20 days ago): {old_test_uri}")
    print()
    
    # 5. すべての成果物を表示
    all_artifacts = store.get_all_artifacts()
    print(f"Total artifacts: {len(all_artifacts)}\n")
    
    print("All artifacts:")
    for artifact in all_artifacts:
        age_days = (datetime.now() - artifact.created_at).days
        retention_days = store.retention_policy.get_retention_days(artifact.type)
        is_expired = store.retention_policy.is_expired(artifact)
        
        status = "EXPIRED" if is_expired else "VALID"
        print(f"  [{status}] {artifact.type.value} - {artifact.task_id}")
        print(f"    Age: {age_days} days, Retention: {retention_days} days")
        print(f"    URI: {artifact.uri}")
    print()
    
    # 6. 期限切れの成果物を検出
    expired = store.retention_policy.find_expired(all_artifacts)
    print(f"Expired artifacts: {len(expired)}")
    for artifact in expired:
        print(f"  - {artifact.type.value} ({artifact.task_id})")
    print()
    
    # 7. クリーンアップのドライラン
    print("Running cleanup (dry run)...")
    dry_result = store.cleanup_expired(dry_run=True)
    
    print(f"Dry Run Result:")
    print(f"  Total artifacts: {dry_result['total_artifacts']}")
    print(f"  Expired: {dry_result['expired_count']}")
    print(f"  Would delete: {dry_result['deleted_count']}")
    print(f"  Would free: {dry_result['freed_mb']} MB")
    print()
    
    # 8. 実際のクリーンアップ
    print("Running actual cleanup...")
    actual_result = store.cleanup_expired(dry_run=False)
    
    print(f"Actual Cleanup Result:")
    print(f"  Deleted: {actual_result['deleted_count']}")
    print(f"  Failed: {actual_result['failed_count']}")
    print(f"  Freed: {actual_result['freed_mb']} MB")
    
    if actual_result['errors']:
        print(f"  Errors:")
        for error in actual_result['errors']:
            print(f"    - {error}")
    print()
    
    # 9. クリーンアップ後の成果物を確認
    remaining_artifacts = store.get_all_artifacts()
    print(f"Remaining artifacts after cleanup: {len(remaining_artifacts)}")
    for artifact in remaining_artifacts:
        print(f"  - {artifact.type.value} ({artifact.task_id})")
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()

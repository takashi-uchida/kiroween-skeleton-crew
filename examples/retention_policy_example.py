"""
Example: Retention Policy Usage

Demonstrates how to use the RetentionPolicy to manage artifact retention
and perform automatic cleanup of expired artifacts.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from necrocode.artifact_store.artifact_store import ArtifactStore
from necrocode.artifact_store.config import ArtifactStoreConfig, RetentionPolicyConfig
from necrocode.artifact_store.models import ArtifactType


def main():
    print("=== Retention Policy Example ===\n")
    
    # 1. カスタム保持期間ポリシーで設定を作成
    retention_config = RetentionPolicyConfig(
        diff_days=30,  # diffは30日間保持
        log_days=7,    # logは7日間保持
        test_days=14,  # test結果は14日間保持
    )
    
    config = ArtifactStoreConfig(
        backend_type="filesystem",
        base_path=Path("/tmp/artifact-store-retention-example"),
        retention_policy=retention_config,
    )
    
    # 2. Artifact Storeを初期化
    store = ArtifactStore(config)
    print(f"Initialized ArtifactStore at {config.base_path}\n")
    
    # 3. テスト用の成果物をアップロード
    print("Uploading test artifacts...")
    
    # 最近の成果物
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
    
    # 4. 保持期間ポリシーの情報を表示
    print("Retention Policy Settings:")
    print(f"  DIFF: {store.retention_policy.get_retention_days(ArtifactType.DIFF)} days")
    print(f"  LOG: {store.retention_policy.get_retention_days(ArtifactType.LOG)} days")
    print(f"  TEST: {store.retention_policy.get_retention_days(ArtifactType.TEST_RESULT)} days")
    print()
    
    # 5. すべての成果物を取得
    all_artifacts = store.get_all_artifacts()
    print(f"Total artifacts: {len(all_artifacts)}\n")
    
    # 6. 各成果物の有効期限を表示
    print("Artifact Expiration Info:")
    for artifact in all_artifacts:
        expiration_date = store.retention_policy.get_expiration_date(artifact)
        days_until = store.retention_policy.get_days_until_expiration(artifact)
        
        print(f"  {artifact.uri}")
        print(f"    Type: {artifact.type.value}")
        print(f"    Created: {artifact.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"    Expires: {expiration_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"    Days until expiration: {days_until}")
        print()
    
    # 7. 期限切れの成果物を検出 (現在時刻基準)
    expired = store.retention_policy.find_expired(all_artifacts)
    print(f"Expired artifacts (now): {len(expired)}\n")
    
    # 8. 未来の時刻で期限切れを検出 (シミュレーション)
    future_time = datetime.now() + timedelta(days=10)
    expired_future = store.retention_policy.find_expired(all_artifacts, future_time)
    print(f"Expired artifacts (10 days from now): {len(expired_future)}")
    
    if expired_future:
        print("  Would be expired:")
        for artifact in expired_future:
            print(f"    - {artifact.uri} ({artifact.type.value})")
    print()
    
    # 9. まもなく期限切れになる成果物を検出
    expiring_soon = store.retention_policy.find_expiring_soon(all_artifacts, days_threshold=7)
    print(f"Artifacts expiring within 7 days: {len(expiring_soon)}\n")
    
    # 10. クリーンアップのドライラン
    print("Running cleanup (dry run)...")
    result = store.cleanup_expired(dry_run=True)
    
    print(f"Cleanup Result (dry run):")
    print(f"  Total artifacts: {result['total_artifacts']}")
    print(f"  Expired: {result['expired_count']}")
    print(f"  Would delete: {result['deleted_count']}")
    print(f"  Would free: {result['freed_mb']} MB")
    print()
    
    # 11. 実際のクリーンアップ (期限切れがある場合のみ)
    if result['expired_count'] > 0:
        print("Running actual cleanup...")
        actual_result = store.cleanup_expired(dry_run=False)
        
        print(f"Cleanup Result (actual):")
        print(f"  Deleted: {actual_result['deleted_count']}")
        print(f"  Failed: {actual_result['failed_count']}")
        print(f"  Freed: {actual_result['freed_mb']} MB")
        
        if actual_result['errors']:
            print(f"  Errors: {actual_result['errors']}")
    else:
        print("No expired artifacts to clean up.")
    
    print("\n=== Example Complete ===")


if __name__ == "__main__":
    main()

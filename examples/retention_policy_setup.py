#!/usr/bin/env python3
"""
Retention Policy Setup Example

このサンプルは、保持期間ポリシーの設定と使用方法を示します。
"""

import tempfile
import time
from datetime import datetime, timedelta
from necrocode.artifact_store import (
    ArtifactStore,
    ArtifactStoreConfig,
    ArtifactType
)


def example_default_retention_policy():
    """デフォルトの保持期間ポリシー"""
    print("=== Default Retention Policy ===\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # デフォルトの保持期間を使用
        config = ArtifactStoreConfig(
            backend_type="filesystem",
            base_path=tmpdir
        )
        
        print("Default retention policy:")
        print(f"  DIFF: {config.retention_policy['diff']} days")
        print(f"  LOG: {config.retention_policy['log']} days")
        print(f"  TEST_RESULT: {config.retention_policy['test']} days\n")
        
        store = ArtifactStore(config)
        print("✓ Artifact Store initialized with default retention policy\n")
        
        return store


def example_custom_retention_policy():
    """カスタム保持期間ポリシー"""
    print("=== Custom Retention Policy ===\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # カスタム保持期間を設定
        config = ArtifactStoreConfig(
            backend_type="filesystem",
            base_path=tmpdir,
            retention_policy={
                "diff": 60,   # 60日間保持
                "log": 14,    # 14日間保持
                "test": 30    # 30日間保持
            }
        )
        
        print("Custom retention policy:")
        print(f"  DIFF: {config.retention_policy['diff']} days")
        print(f"  LOG: {config.retention_policy['log']} days")
        print(f"  TEST_RESULT: {config.retention_policy['test']} days\n")
        
        store = ArtifactStore(config)
        print("✓ Artifact Store initialized with custom retention policy\n")
        
        return store


def example_environment_specific_policies():
    """環境ごとの保持期間ポリシー"""
    print("=== Environment-Specific Retention Policies ===\n")
    
    # 開発環境: 短い保持期間
    dev_config = ArtifactStoreConfig(
        backend_type="filesystem",
        base_path="/tmp/dev-artifacts",
        retention_policy={
            "diff": 7,    # 1週間
            "log": 3,     # 3日間
            "test": 7     # 1週間
        }
    )
    print("Development environment:")
    print(f"  DIFF: {dev_config.retention_policy['diff']} days")
    print(f"  LOG: {dev_config.retention_policy['log']} days")
    print(f"  TEST_RESULT: {dev_config.retention_policy['test']} days\n")
    
    # ステージング環境: 中程度の保持期間
    staging_config = ArtifactStoreConfig(
        backend_type="filesystem",
        base_path="/tmp/staging-artifacts",
        retention_policy={
            "diff": 30,   # 1ヶ月
            "log": 14,    # 2週間
            "test": 30    # 1ヶ月
        }
    )
    print("Staging environment:")
    print(f"  DIFF: {staging_config.retention_policy['diff']} days")
    print(f"  LOG: {staging_config.retention_policy['log']} days")
    print(f"  TEST_RESULT: {staging_config.retention_policy['test']} days\n")
    
    # 本番環境: 長い保持期間
    prod_config = ArtifactStoreConfig(
        backend_type="filesystem",
        base_path="/tmp/prod-artifacts",
        retention_policy={
            "diff": 90,   # 3ヶ月
            "log": 30,    # 1ヶ月
            "test": 60    # 2ヶ月
        }
    )
    print("Production environment:")
    print(f"  DIFF: {prod_config.retention_policy['diff']} days")
    print(f"  LOG: {prod_config.retention_policy['log']} days")
    print(f"  TEST_RESULT: {prod_config.retention_policy['test']} days\n")


def example_cleanup_expired_artifacts():
    """期限切れ成果物のクリーンアップ"""
    print("=== Cleanup Expired Artifacts ===\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 短い保持期間を設定（テスト用）
        config = ArtifactStoreConfig(
            backend_type="filesystem",
            base_path=tmpdir,
            retention_policy={
                "diff": 1,    # 1日
                "log": 1,     # 1日
                "test": 1     # 1日
            }
        )
        
        store = ArtifactStore(config)
        print("✓ Artifact Store initialized\n")
        
        # 成果物をアップロード
        print("Uploading artifacts...")
        uri1 = store.upload(
            task_id="1.1",
            spec_name="test-project",
            artifact_type=ArtifactType.DIFF,
            content=b"diff content 1"
        )
        print(f"  ✓ Uploaded: {uri1}")
        
        uri2 = store.upload(
            task_id="1.2",
            spec_name="test-project",
            artifact_type=ArtifactType.LOG,
            content=b"log content 1"
        )
        print(f"  ✓ Uploaded: {uri2}\n")
        
        # 現在の成果物数を確認
        usage = store.get_storage_usage()
        print(f"Current artifacts: {usage['total_count']}\n")
        
        # メタデータを直接操作して古い日付に設定（テスト用）
        print("Simulating old artifacts (setting created_at to 2 days ago)...")
        metadata1 = store.get_metadata(uri1)
        metadata1.created_at = datetime.now() - timedelta(days=2)
        store.metadata_manager.save(metadata1)
        
        metadata2 = store.get_metadata(uri2)
        metadata2.created_at = datetime.now() - timedelta(days=2)
        store.metadata_manager.save(metadata2)
        print("  ✓ Metadata updated\n")
        
        # 期限切れ成果物を検出
        print("Finding expired artifacts...")
        expired = store.retention_policy.find_expired(
            store.metadata_manager.list_all()
        )
        print(f"  Found {len(expired)} expired artifacts\n")
        
        # クリーンアップを実行
        print("Running cleanup...")
        deleted_count = store.cleanup_expired()
        print(f"  ✓ Deleted {deleted_count} expired artifacts\n")
        
        # クリーンアップ後の成果物数を確認
        usage = store.get_storage_usage()
        print(f"Remaining artifacts: {usage['total_count']}\n")


def example_scheduled_cleanup():
    """定期的なクリーンアップのスケジューリング"""
    print("=== Scheduled Cleanup ===\n")
    
    print("Example: Using schedule library for periodic cleanup\n")
    
    print("```python")
    print("import schedule")
    print("import time")
    print("from necrocode.artifact_store import ArtifactStore, ArtifactStoreConfig")
    print()
    print("# Artifact Storeを初期化")
    print("config = ArtifactStoreConfig()")
    print("store = ArtifactStore(config)")
    print()
    print("def cleanup_job():")
    print("    print('Running cleanup...')")
    print("    deleted = store.cleanup_expired()")
    print("    print(f'Deleted {deleted} expired artifacts')")
    print()
    print("# 毎日午前2時に実行")
    print("schedule.every().day.at('02:00').do(cleanup_job)")
    print()
    print("# または、6時間ごとに実行")
    print("schedule.every(6).hours.do(cleanup_job)")
    print()
    print("# スケジューラーを実行")
    print("while True:")
    print("    schedule.run_pending()")
    print("    time.sleep(60)")
    print("```\n")


def example_manual_cleanup_workflow():
    """手動クリーンアップのワークフロー"""
    print("=== Manual Cleanup Workflow ===\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config = ArtifactStoreConfig(
            backend_type="filesystem",
            base_path=tmpdir,
            retention_policy={
                "diff": 30,
                "log": 7,
                "test": 14
            }
        )
        
        store = ArtifactStore(config)
        
        # ステップ1: ストレージ使用量を確認
        print("Step 1: Check storage usage")
        usage = store.get_storage_usage()
        total_mb = usage['total_size'] / 1024 / 1024
        print(f"  Total size: {total_mb:.2f} MB")
        print(f"  Total count: {usage['total_count']} artifacts\n")
        
        # ステップ2: 期限切れ成果物を検出
        print("Step 2: Find expired artifacts")
        expired = store.retention_policy.find_expired(
            store.metadata_manager.list_all()
        )
        print(f"  Found {len(expired)} expired artifacts")
        
        if expired:
            expired_size = sum(m.size for m in expired)
            expired_mb = expired_size / 1024 / 1024
            print(f"  Total size to be freed: {expired_mb:.2f} MB\n")
            
            # ステップ3: 確認
            print("Step 3: Confirm cleanup")
            print("  Would you like to delete these artifacts? (y/n)")
            # response = input("  > ")
            response = "y"  # 自動実行用
            
            if response.lower() == 'y':
                # ステップ4: クリーンアップを実行
                print("\nStep 4: Execute cleanup")
                deleted_count = store.cleanup_expired()
                print(f"  ✓ Deleted {deleted_count} artifacts\n")
                
                # ステップ5: 結果を確認
                print("Step 5: Verify results")
                usage = store.get_storage_usage()
                total_mb = usage['total_size'] / 1024 / 1024
                print(f"  Total size: {total_mb:.2f} MB")
                print(f"  Total count: {usage['total_count']} artifacts\n")
            else:
                print("  Cleanup cancelled\n")
        else:
            print("  No expired artifacts to clean up\n")


def example_selective_cleanup():
    """選択的なクリーンアップ"""
    print("=== Selective Cleanup ===\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config = ArtifactStoreConfig(
            backend_type="filesystem",
            base_path=tmpdir
        )
        
        store = ArtifactStore(config)
        
        # 複数のプロジェクトの成果物をアップロード
        print("Uploading artifacts for multiple projects...")
        for spec_name in ["project-a", "project-b", "project-c"]:
            for i in range(3):
                store.upload(
                    task_id=f"{i+1}.1",
                    spec_name=spec_name,
                    artifact_type=ArtifactType.DIFF,
                    content=f"content for {spec_name}".encode()
                )
        print("  ✓ Uploaded 9 artifacts\n")
        
        # プロジェクトごとの使用量を確認
        print("Storage usage by project:")
        usage = store.get_storage_usage()
        for spec_name, size in usage['by_spec'].items():
            count = len(store.search({"spec_name": spec_name}))
            print(f"  {spec_name}: {size} bytes ({count} artifacts)")
        print()
        
        # 特定のプロジェクトの成果物を削除
        print("Deleting artifacts for 'project-b'...")
        deleted_count = store.delete_by_spec_name("project-b")
        print(f"  ✓ Deleted {deleted_count} artifacts\n")
        
        # 削除後の使用量を確認
        print("Storage usage after deletion:")
        usage = store.get_storage_usage()
        for spec_name, size in usage['by_spec'].items():
            count = len(store.search({"spec_name": spec_name}))
            print(f"  {spec_name}: {size} bytes ({count} artifacts)")
        print()


def example_retention_policy_best_practices():
    """保持期間ポリシーのベストプラクティス"""
    print("=== Retention Policy Best Practices ===\n")
    
    print("1. Set appropriate retention periods based on artifact type:")
    print("   - DIFF: Longer retention (30-90 days) for code review history")
    print("   - LOG: Shorter retention (7-14 days) as logs are verbose")
    print("   - TEST_RESULT: Medium retention (14-30 days) for trend analysis\n")
    
    print("2. Adjust retention periods based on environment:")
    print("   - Development: Short (3-7 days) to save space")
    print("   - Staging: Medium (14-30 days) for testing")
    print("   - Production: Long (30-90 days) for compliance\n")
    
    print("3. Schedule regular cleanup:")
    print("   - Run cleanup during off-peak hours (e.g., 2 AM)")
    print("   - Use cron or schedule library for automation")
    print("   - Monitor cleanup logs for issues\n")
    
    print("4. Monitor storage usage:")
    print("   - Set up alerts when storage reaches threshold")
    print("   - Review usage trends regularly")
    print("   - Adjust retention policies as needed\n")
    
    print("5. Consider compliance requirements:")
    print("   - Some artifacts may need longer retention for audits")
    print("   - Use tags to mark artifacts that need special retention")
    print("   - Document retention policies for your organization\n")


def main():
    print("=== Retention Policy Setup Examples ===\n")
    
    # デフォルトの保持期間ポリシー
    print("1. Default Retention Policy")
    print("-" * 50)
    example_default_retention_policy()
    
    # カスタム保持期間ポリシー
    print("\n2. Custom Retention Policy")
    print("-" * 50)
    example_custom_retention_policy()
    
    # 環境ごとのポリシー
    print("\n3. Environment-Specific Policies")
    print("-" * 50)
    example_environment_specific_policies()
    
    # 期限切れ成果物のクリーンアップ
    print("\n4. Cleanup Expired Artifacts")
    print("-" * 50)
    example_cleanup_expired_artifacts()
    
    # 定期的なクリーンアップ
    print("\n5. Scheduled Cleanup")
    print("-" * 50)
    example_scheduled_cleanup()
    
    # 手動クリーンアップのワークフロー
    print("\n6. Manual Cleanup Workflow")
    print("-" * 50)
    example_manual_cleanup_workflow()
    
    # 選択的なクリーンアップ
    print("\n7. Selective Cleanup")
    print("-" * 50)
    example_selective_cleanup()
    
    # ベストプラクティス
    print("\n8. Best Practices")
    print("-" * 50)
    example_retention_policy_best_practices()
    
    print("=== Examples completed ===")


if __name__ == "__main__":
    main()

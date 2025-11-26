"""
Storage Usage Monitoring Example

This example demonstrates how to monitor storage usage in the Artifact Store.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from necrocode.artifact_store.artifact_store import ArtifactStore
from necrocode.artifact_store.config import ArtifactStoreConfig, StorageQuotaConfig
from necrocode.artifact_store.models import ArtifactType
from necrocode.artifact_store.exceptions import StorageFullError


def main():
    """Storage usage monitoring example"""
    
    # Create config with a small quota for demonstration
    config = ArtifactStoreConfig(
        backend_type="filesystem",
        base_path=Path("tmp_artifacts_usage"),
        compression_enabled=True,
        storage_quota=StorageQuotaConfig(
            max_size_gb=0.001,  # 1 MB limit for demo
            warn_threshold=0.7,  # Warn at 70%
        ),
    )
    
    store = ArtifactStore(config)
    
    print("=" * 60)
    print("Storage Usage Monitoring Example")
    print("=" * 60)
    
    # Upload some artifacts
    print("\n1. Uploading artifacts...")
    
    artifacts = [
        ("chat-app", "1.1", ArtifactType.DIFF, b"diff content " * 100),
        ("chat-app", "1.2", ArtifactType.LOG, b"log content " * 100),
        ("chat-app", "1.3", ArtifactType.TEST_RESULT, b"test result " * 100),
        ("iot-dashboard", "2.1", ArtifactType.DIFF, b"diff content " * 100),
        ("iot-dashboard", "2.2", ArtifactType.LOG, b"log content " * 100),
    ]
    
    for spec_name, task_id, artifact_type, content in artifacts:
        try:
            uri = store.upload(
                task_id=task_id,
                spec_name=spec_name,
                artifact_type=artifact_type,
                content=content,
            )
            print(f"  ✓ Uploaded: {spec_name}/{task_id}/{artifact_type.value}")
        except StorageFullError as e:
            print(f"  ✗ Storage full: {e}")
            break
    
    # Get overall storage usage
    print("\n2. Overall Storage Usage:")
    print("-" * 60)
    
    usage = store.get_storage_usage()
    print(f"  Total Size: {usage['total_size_mb']} MB ({usage['total_size_bytes']} bytes)")
    print(f"  Artifact Count: {usage['artifact_count']}")
    print(f"  Quota: {usage['total_size_gb']} GB / {usage['quota_max_gb']} GB")
    print(f"  Usage: {usage['quota_used_percent']}%")
    print(f"  Warning: {'⚠️  YES' if usage['quota_warning'] else '✓ No'}")
    
    # Get usage by spec
    print("\n3. Storage Usage by Spec:")
    print("-" * 60)
    
    usage_by_spec = store.get_usage_by_spec()
    for spec_name, spec_usage in sorted(usage_by_spec.items()):
        print(f"  {spec_name}:")
        print(f"    Size: {spec_usage['size_mb']} MB ({spec_usage['size_bytes']} bytes)")
        print(f"    Artifacts: {spec_usage['artifact_count']}")
    
    # Get usage by type
    print("\n4. Storage Usage by Type:")
    print("-" * 60)
    
    usage_by_type = store.get_usage_by_type()
    for artifact_type, type_usage in sorted(usage_by_type.items()):
        print(f"  {artifact_type}:")
        print(f"    Size: {type_usage['size_mb']} MB ({type_usage['size_bytes']} bytes)")
        print(f"    Artifacts: {type_usage['artifact_count']}")
    
    # Try to upload when quota is exceeded
    print("\n5. Testing Quota Enforcement:")
    print("-" * 60)
    
    try:
        # Try to upload a large artifact
        large_content = b"x" * (2 * 1024 * 1024)  # 2 MB
        store.upload(
            task_id="3.1",
            spec_name="large-project",
            artifact_type=ArtifactType.DIFF,
            content=large_content,
        )
        print("  ✓ Upload succeeded (unexpected)")
    except StorageFullError as e:
        print(f"  ✓ Upload blocked: {e}")
    
    # Cleanup
    print("\n6. Cleanup:")
    print("-" * 60)
    
    deleted_count = store.delete_by_spec_name("chat-app")
    print(f"  Deleted {deleted_count} artifacts from chat-app")
    
    # Check usage after cleanup
    usage_after = store.get_storage_usage()
    print(f"  New total size: {usage_after['total_size_mb']} MB")
    print(f"  New usage: {usage_after['quota_used_percent']}%")
    
    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)
    
    # Cleanup temp directory
    import shutil
    if Path("tmp_artifacts_usage").exists():
        shutil.rmtree("tmp_artifacts_usage")
        print("\nCleaned up temporary directory")


if __name__ == "__main__":
    main()

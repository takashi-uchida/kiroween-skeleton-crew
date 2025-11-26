"""
Example demonstrating artifact versioning functionality.

This example shows how to:
1. Enable versioning
2. Upload multiple versions of the same artifact
3. Retrieve all versions
4. Download a specific version
5. Delete old versions
"""

import tempfile
from pathlib import Path

from necrocode.artifact_store.artifact_store import ArtifactStore
from necrocode.artifact_store.config import ArtifactStoreConfig
from necrocode.artifact_store.models import ArtifactType


def main():
    """Demonstrate artifact versioning."""
    
    # Create temporary directory for this example
    with tempfile.TemporaryDirectory() as temp_dir:
        print("=== Artifact Store Versioning Example ===\n")
        
        # 1. Initialize ArtifactStore with versioning enabled
        print("1. Initializing ArtifactStore with versioning enabled...")
        config = ArtifactStoreConfig(
            base_path=Path(temp_dir) / "artifacts",
            compression_enabled=True,
            versioning_enabled=True,  # Enable versioning
        )
        store = ArtifactStore(config)
        print(f"   ✓ Versioning enabled: {config.versioning_enabled}\n")
        
        # 2. Upload multiple versions of the same artifact
        print("2. Uploading multiple versions of the same artifact...")
        task_id = "1.1"
        spec_name = "chat-app"
        artifact_type = ArtifactType.DIFF
        
        # Version 1
        content_v1 = b"Initial implementation of login feature"
        uri_v1 = store.upload(
            task_id=task_id,
            spec_name=spec_name,
            artifact_type=artifact_type,
            content=content_v1,
        )
        print(f"   ✓ Uploaded version 1: {uri_v1}")
        
        # Version 2
        content_v2 = b"Added password validation to login feature"
        uri_v2 = store.upload(
            task_id=task_id,
            spec_name=spec_name,
            artifact_type=artifact_type,
            content=content_v2,
        )
        print(f"   ✓ Uploaded version 2: {uri_v2}")
        
        # Version 3
        content_v3 = b"Fixed security vulnerability in login feature"
        uri_v3 = store.upload(
            task_id=task_id,
            spec_name=spec_name,
            artifact_type=artifact_type,
            content=content_v3,
        )
        print(f"   ✓ Uploaded version 3: {uri_v3}\n")
        
        # 3. Retrieve all versions
        print("3. Retrieving all versions...")
        all_versions = store.get_all_versions(task_id, spec_name, artifact_type)
        print(f"   ✓ Found {len(all_versions)} versions:")
        for metadata in all_versions:
            print(f"     - Version {metadata.version}: {metadata.uri}")
            print(f"       Size: {metadata.size} bytes, Created: {metadata.created_at}")
        print()
        
        # 4. Download specific versions
        print("4. Downloading specific versions...")
        
        # Download version 1
        downloaded_v1 = store.download_version(
            task_id=task_id,
            spec_name=spec_name,
            artifact_type=artifact_type,
            version=1,
        )
        print(f"   ✓ Version 1 content: {downloaded_v1.decode()}")
        
        # Download version 2
        downloaded_v2 = store.download_version(
            task_id=task_id,
            spec_name=spec_name,
            artifact_type=artifact_type,
            version=2,
        )
        print(f"   ✓ Version 2 content: {downloaded_v2.decode()}")
        
        # Download version 3 (latest)
        downloaded_v3 = store.download_version(
            task_id=task_id,
            spec_name=spec_name,
            artifact_type=artifact_type,
            version=3,
        )
        print(f"   ✓ Version 3 content: {downloaded_v3.decode()}\n")
        
        # 5. Delete old versions (keep only latest 2)
        print("5. Deleting old versions (keeping latest 2)...")
        deleted_count = store.delete_old_versions(
            task_id=task_id,
            spec_name=spec_name,
            artifact_type=artifact_type,
            keep_latest=2,
        )
        print(f"   ✓ Deleted {deleted_count} old version(s)")
        
        # Verify remaining versions
        remaining_versions = store.get_all_versions(task_id, spec_name, artifact_type)
        print(f"   ✓ Remaining versions: {len(remaining_versions)}")
        for metadata in remaining_versions:
            print(f"     - Version {metadata.version}: {metadata.uri}")
        print()
        
        # 6. Compare with non-versioned behavior
        print("6. Comparing with non-versioned behavior...")
        
        # Create a new store without versioning
        config_no_version = ArtifactStoreConfig(
            base_path=Path(temp_dir) / "artifacts_no_version",
            compression_enabled=True,
            versioning_enabled=False,  # Disable versioning
        )
        store_no_version = ArtifactStore(config_no_version)
        
        # Upload multiple times (should overwrite)
        uri1 = store_no_version.upload(
            task_id="2.1",
            spec_name="test-app",
            artifact_type=ArtifactType.LOG,
            content=b"First log entry",
        )
        print(f"   ✓ First upload: {uri1}")
        
        uri2 = store_no_version.upload(
            task_id="2.1",
            spec_name="test-app",
            artifact_type=ArtifactType.LOG,
            content=b"Second log entry (overwrites first)",
        )
        print(f"   ✓ Second upload: {uri2}")
        
        # Check versions (should only have 1)
        versions = store_no_version.get_all_versions("2.1", "test-app", ArtifactType.LOG)
        print(f"   ✓ Total versions without versioning: {len(versions)}")
        
        # Download and verify content
        content = store_no_version.download(uri2)
        print(f"   ✓ Content: {content.decode()}")
        print()
        
        print("=== Example Complete ===")
        print("\nKey takeaways:")
        print("- With versioning enabled, each upload creates a new version")
        print("- Without versioning, uploads overwrite existing artifacts")
        print("- You can retrieve all versions, download specific versions, and delete old versions")
        print("- Version numbers are automatically incremented")


if __name__ == "__main__":
    main()

"""
Example: Artifact Store Integrity Verification

This example demonstrates how to use the integrity verification features
of the Artifact Store to ensure artifact data integrity.
"""

import sys
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from necrocode.artifact_store.artifact_store import ArtifactStore
from necrocode.artifact_store.config import ArtifactStoreConfig
from necrocode.artifact_store.models import ArtifactType
from necrocode.artifact_store.exceptions import IntegrityError


def main():
    """Demonstrate integrity verification features"""
    
    # Create temporary directory for this example
    temp_dir = tempfile.mkdtemp()
    
    try:
        print("Artifact Store - Integrity Verification Example")
        print("=" * 60)
        
        # Initialize artifact store
        config = ArtifactStoreConfig(
            backend_type="filesystem",
            base_path=Path(temp_dir),
            compression_enabled=True,
            verify_checksum=True,  # Enable automatic checksum verification
        )
        store = ArtifactStore(config)
        
        # Example 1: Upload artifacts with automatic checksum calculation
        print("\n1. Uploading artifacts (checksums calculated automatically)...")
        
        diff_content = b"+ Added new feature\n- Removed old code"
        log_content = b"[INFO] Task started\n[INFO] Task completed successfully"
        test_content = b'{"tests": 10, "passed": 10, "failed": 0}'
        
        diff_uri = store.upload("1.1", "chat-app", ArtifactType.DIFF, diff_content)
        log_uri = store.upload("1.1", "chat-app", ArtifactType.LOG, log_content)
        test_uri = store.upload("1.1", "chat-app", ArtifactType.TEST_RESULT, test_content)
        
        print(f"   ✓ Uploaded 3 artifacts with checksums")
        
        # Example 2: Download with automatic checksum verification
        print("\n2. Downloading artifacts (checksums verified automatically)...")
        
        downloaded_diff = store.download(diff_uri, verify_checksum=True)
        print(f"   ✓ Downloaded and verified: {diff_uri}")
        print(f"     Content matches original: {downloaded_diff == diff_content}")
        
        # Example 3: Manually verify individual artifact checksum
        print("\n3. Manually verifying individual artifact checksums...")
        
        try:
            result = store.verify_checksum(diff_uri)
            print(f"   ✓ Checksum verified for: {diff_uri}")
            print(f"     Result: {result}")
        except IntegrityError as e:
            print(f"   ✗ Integrity error: {e}")
        
        # Example 4: Verify all artifacts at once
        print("\n4. Verifying all artifacts in the store...")
        
        verification_result = store.verify_all()
        
        print(f"   ✓ Verification complete:")
        print(f"     - Total artifacts: {verification_result['total_artifacts']}")
        print(f"     - Valid: {verification_result['valid_count']}")
        print(f"     - Invalid: {verification_result['invalid_count']}")
        print(f"     - Errors: {verification_result['error_count']}")
        
        # Example 5: Get metadata to see checksum information
        print("\n5. Viewing artifact metadata (including checksum)...")
        
        metadata = store.get_metadata(diff_uri)
        if metadata:
            print(f"   Artifact: {metadata.uri}")
            print(f"   - Task ID: {metadata.task_id}")
            print(f"   - Type: {metadata.type.value}")
            print(f"   - Size: {metadata.size} bytes")
            print(f"   - Checksum (SHA256): {metadata.checksum[:32]}...")
            print(f"   - Compressed: {metadata.compressed}")
            print(f"   - Created: {metadata.created_at}")
        
        # Example 6: Demonstrate integrity error detection
        print("\n6. Demonstrating integrity error detection...")
        print("   (Simulating corrupted artifact)")
        
        # Upload a new uncompressed artifact for easier corruption testing
        config_no_compression = ArtifactStoreConfig(
            backend_type="filesystem",
            base_path=Path(temp_dir),
            compression_enabled=False,
        )
        store_no_compression = ArtifactStore(config_no_compression)
        
        test_uri2 = store_no_compression.upload(
            "1.2", "chat-app", ArtifactType.DIFF,
            b"Original content"
        )
        
        # Simulate corruption by modifying the file directly
        file_path = Path(test_uri2.replace("file://", ""))
        with open(file_path, "wb") as f:
            f.write(b"Corrupted content")
        
        # Try to verify the corrupted artifact
        try:
            store_no_compression.verify_checksum(test_uri2)
            print("   ✗ ERROR: Corruption not detected!")
        except IntegrityError as e:
            print(f"   ✓ Corruption detected successfully!")
            print(f"     Expected checksum: {e.expected_checksum[:32]}...")
            print(f"     Actual checksum: {e.actual_checksum[:32]}...")
        
        print("\n" + "=" * 60)
        print("Example completed successfully!")
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
        print(f"\nCleaned up temporary directory: {temp_dir}")


if __name__ == "__main__":
    main()

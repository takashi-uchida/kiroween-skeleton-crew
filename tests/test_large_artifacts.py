"""
Tests for large artifact handling (>10MB).

Tests streaming download, compression efficiency, and performance
with large artifacts.

Requirements: 2.4
"""

import pytest
import tempfile
import shutil
import time
from pathlib import Path
from necrocode.artifact_store.artifact_store import ArtifactStore
from necrocode.artifact_store.config import ArtifactStoreConfig
from necrocode.artifact_store.models import ArtifactType


@pytest.fixture
def temp_base_path():
    """Create a temporary base path for testing."""
    temp_dir = tempfile.mkdtemp(prefix="large_artifacts_")
    yield Path(temp_dir)
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def store_with_compression(temp_base_path):
    """Create an artifact store with compression enabled."""
    config = ArtifactStoreConfig(
        backend_type="filesystem",
        base_path=temp_base_path / "compressed",
        compression_enabled=True,
        verify_checksum=True,
    )
    return ArtifactStore(config)


@pytest.fixture
def store_without_compression(temp_base_path):
    """Create an artifact store without compression."""
    config = ArtifactStoreConfig(
        backend_type="filesystem",
        base_path=temp_base_path / "uncompressed",
        compression_enabled=False,
        verify_checksum=True,
    )
    return ArtifactStore(config)


def test_upload_download_10mb_artifact(store_with_compression):
    """Test uploading and downloading a 10MB artifact."""
    # Create 10 MB content
    content = b"x" * (10 * 1024 * 1024)
    
    # Upload
    start_time = time.time()
    uri = store_with_compression.upload(
        task_id="1.1",
        spec_name="large-test",
        artifact_type=ArtifactType.LOG,
        content=content,
    )
    upload_time = time.time() - start_time
    
    print(f"\n10MB upload time: {upload_time:.2f}s")
    
    # Verify upload
    assert store_with_compression.exists(uri)
    
    # Check metadata
    metadata = store_with_compression.get_metadata(uri)
    assert metadata.original_size == len(content)
    assert metadata.compressed is True
    assert metadata.size < metadata.original_size  # Should be compressed
    
    compression_ratio = metadata.size / metadata.original_size
    print(f"Compression ratio: {compression_ratio:.2%}")
    
    # Download
    start_time = time.time()
    downloaded = store_with_compression.download(uri)
    download_time = time.time() - start_time
    
    print(f"10MB download time: {download_time:.2f}s")
    
    # Verify content
    assert len(downloaded) == len(content)
    assert downloaded == content


def test_upload_download_50mb_artifact(store_with_compression):
    """Test uploading and downloading a 50MB artifact."""
    # Create 50 MB content
    content = b"y" * (50 * 1024 * 1024)
    
    # Upload
    start_time = time.time()
    uri = store_with_compression.upload(
        task_id="2.1",
        spec_name="large-test",
        artifact_type=ArtifactType.LOG,
        content=content,
    )
    upload_time = time.time() - start_time
    
    print(f"\n50MB upload time: {upload_time:.2f}s")
    
    # Verify upload
    assert store_with_compression.exists(uri)
    
    # Check metadata
    metadata = store_with_compression.get_metadata(uri)
    assert metadata.original_size == len(content)
    assert metadata.compressed is True
    
    compression_ratio = metadata.size / metadata.original_size
    print(f"Compression ratio: {compression_ratio:.2%}")
    
    # Download
    start_time = time.time()
    downloaded = store_with_compression.download(uri)
    download_time = time.time() - start_time
    
    print(f"50MB download time: {download_time:.2f}s")
    
    # Verify content
    assert len(downloaded) == len(content)
    assert downloaded == content


def test_upload_download_100mb_artifact(store_with_compression):
    """Test uploading and downloading a 100MB artifact."""
    # Create 100 MB content
    content = b"z" * (100 * 1024 * 1024)
    
    # Upload
    start_time = time.time()
    uri = store_with_compression.upload(
        task_id="3.1",
        spec_name="large-test",
        artifact_type=ArtifactType.LOG,
        content=content,
    )
    upload_time = time.time() - start_time
    
    print(f"\n100MB upload time: {upload_time:.2f}s")
    
    # Verify upload
    assert store_with_compression.exists(uri)
    
    # Check metadata
    metadata = store_with_compression.get_metadata(uri)
    assert metadata.original_size == len(content)
    assert metadata.compressed is True
    
    compression_ratio = metadata.size / metadata.original_size
    print(f"Compression ratio: {compression_ratio:.2%}")
    
    # Download
    start_time = time.time()
    downloaded = store_with_compression.download(uri)
    download_time = time.time() - start_time
    
    print(f"100MB download time: {download_time:.2f}s")
    
    # Verify content
    assert len(downloaded) == len(content)
    assert downloaded == content


def test_streaming_download_large_artifact(store_with_compression):
    """Test streaming download for large artifacts (Requirement 2.4)."""
    # Create 20 MB content
    content = b"stream test " * (20 * 1024 * 1024 // 12)
    
    # Upload
    uri = store_with_compression.upload(
        task_id="4.1",
        spec_name="stream-test",
        artifact_type=ArtifactType.LOG,
        content=content,
    )
    
    # Stream download
    chunks = []
    chunk_count = 0
    
    for chunk in store_with_compression.download_stream(uri, chunk_size=1024 * 1024):  # 1MB chunks
        chunks.append(chunk)
        chunk_count += 1
    
    # Reconstruct content
    downloaded = b"".join(chunks)
    
    # Verify
    assert len(downloaded) == len(content)
    assert downloaded == content
    assert chunk_count > 1  # Should have multiple chunks
    
    print(f"\nStreamed {len(content)} bytes in {chunk_count} chunks")


def test_compression_efficiency_large_text(store_with_compression):
    """Test compression efficiency with large text content."""
    # Create highly compressible content (repeated text)
    text = "This is a test line that will be repeated many times.\n"
    content = (text * (10 * 1024 * 1024 // len(text))).encode()
    
    # Upload
    uri = store_with_compression.upload(
        task_id="5.1",
        spec_name="compression-test",
        artifact_type=ArtifactType.LOG,
        content=content,
    )
    
    # Check compression
    metadata = store_with_compression.get_metadata(uri)
    compression_ratio = metadata.size / metadata.original_size
    
    print(f"\nText compression ratio: {compression_ratio:.2%}")
    print(f"Original size: {metadata.original_size / (1024*1024):.2f} MB")
    print(f"Compressed size: {metadata.size / (1024*1024):.2f} MB")
    print(f"Space saved: {(metadata.original_size - metadata.size) / (1024*1024):.2f} MB")
    
    # Text should compress very well
    assert compression_ratio < 0.1  # Should compress to less than 10%
    
    # Download and verify
    downloaded = store_with_compression.download(uri)
    assert downloaded == content


def test_compression_efficiency_large_binary(store_with_compression):
    """Test compression efficiency with large binary content."""
    # Create less compressible content (pseudo-random)
    import random
    random.seed(42)
    content = bytes([random.randint(0, 255) for _ in range(10 * 1024 * 1024)])
    
    # Upload
    uri = store_with_compression.upload(
        task_id="6.1",
        spec_name="compression-test",
        artifact_type=ArtifactType.LOG,
        content=content,
    )
    
    # Check compression
    metadata = store_with_compression.get_metadata(uri)
    compression_ratio = metadata.size / metadata.original_size
    
    print(f"\nBinary compression ratio: {compression_ratio:.2%}")
    print(f"Original size: {metadata.original_size / (1024*1024):.2f} MB")
    print(f"Compressed size: {metadata.size / (1024*1024):.2f} MB")
    
    # Binary data should not compress as well
    assert compression_ratio > 0.8  # Should compress to more than 80%
    
    # Download and verify
    downloaded = store_with_compression.download(uri)
    assert downloaded == content


def test_large_artifact_without_compression(store_without_compression):
    """Test large artifact handling without compression."""
    # Create 15 MB content
    content = b"no compression " * (15 * 1024 * 1024 // 15)
    
    # Upload
    start_time = time.time()
    uri = store_without_compression.upload(
        task_id="7.1",
        spec_name="no-compression-test",
        artifact_type=ArtifactType.LOG,
        content=content,
    )
    upload_time = time.time() - start_time
    
    print(f"\n15MB upload time (no compression): {upload_time:.2f}s")
    
    # Check metadata
    metadata = store_without_compression.get_metadata(uri)
    assert metadata.compressed is False
    assert metadata.original_size is None
    assert metadata.size == len(content)
    
    # Download
    start_time = time.time()
    downloaded = store_without_compression.download(uri)
    download_time = time.time() - start_time
    
    print(f"15MB download time (no compression): {download_time:.2f}s")
    
    # Verify
    assert downloaded == content


def test_checksum_verification_large_artifact(store_with_compression):
    """Test checksum verification with large artifacts."""
    # Create 20 MB content
    content = b"checksum test " * (20 * 1024 * 1024 // 14)
    
    # Upload
    uri = store_with_compression.upload(
        task_id="8.1",
        spec_name="checksum-test",
        artifact_type=ArtifactType.LOG,
        content=content,
    )
    
    # Download with checksum verification
    start_time = time.time()
    downloaded = store_with_compression.download(uri, verify_checksum=True)
    verify_time = time.time() - start_time
    
    print(f"\n20MB download with checksum verification: {verify_time:.2f}s")
    
    # Verify content
    assert downloaded == content
    
    # Verify checksum explicitly
    assert store_with_compression.verify_checksum(uri)


def test_multiple_large_artifacts(store_with_compression):
    """Test handling multiple large artifacts."""
    uris = []
    total_size = 0
    
    # Upload 5 large artifacts
    for i in range(5):
        content = f"Artifact {i} ".encode() * (10 * 1024 * 1024 // 12)
        
        uri = store_with_compression.upload(
            task_id=f"{i+1}.1",
            spec_name="multi-large-test",
            artifact_type=ArtifactType.LOG,
            content=content,
        )
        
        uris.append(uri)
        total_size += len(content)
    
    print(f"\nUploaded 5 artifacts, total size: {total_size / (1024*1024):.2f} MB")
    
    # Verify all exist
    for uri in uris:
        assert store_with_compression.exists(uri)
    
    # Check storage usage
    usage = store_with_compression.get_storage_usage()
    assert usage["artifact_count"] == 5
    
    print(f"Storage usage: {usage['total_size_mb']:.2f} MB")
    print(f"Compression saved: {(total_size / (1024*1024)) - usage['total_size_mb']:.2f} MB")
    
    # Download all and verify
    for i, uri in enumerate(uris):
        downloaded = store_with_compression.download(uri)
        expected_content = f"Artifact {i} ".encode() * (10 * 1024 * 1024 // 12)
        assert downloaded == expected_content


def test_large_artifact_deletion(store_with_compression):
    """Test deletion of large artifacts."""
    # Upload large artifact
    content = b"delete me " * (15 * 1024 * 1024 // 10)
    
    uri = store_with_compression.upload(
        task_id="10.1",
        spec_name="delete-test",
        artifact_type=ArtifactType.LOG,
        content=content,
    )
    
    # Verify exists
    assert store_with_compression.exists(uri)
    
    # Get initial storage usage
    usage_before = store_with_compression.get_storage_usage()
    
    # Delete
    start_time = time.time()
    store_with_compression.delete(uri)
    delete_time = time.time() - start_time
    
    print(f"\nLarge artifact deletion time: {delete_time:.2f}s")
    
    # Verify deleted
    assert not store_with_compression.exists(uri)
    
    # Check storage usage decreased
    usage_after = store_with_compression.get_storage_usage()
    assert usage_after["total_size_bytes"] < usage_before["total_size_bytes"]


def test_large_artifact_export(store_with_compression, temp_base_path):
    """Test exporting large artifacts to ZIP."""
    # Upload multiple large artifacts
    for i in range(3):
        content = f"Export {i} ".encode() * (10 * 1024 * 1024 // 9)
        
        store_with_compression.upload(
            task_id=f"{i+1}.1",
            spec_name="export-large-test",
            artifact_type=ArtifactType.LOG,
            content=content,
        )
    
    # Export
    output_path = temp_base_path / "large_export.zip"
    
    start_time = time.time()
    result_path = store_with_compression.export_by_spec(
        spec_name="export-large-test",
        output_path=output_path,
        include_metadata=True,
    )
    export_time = time.time() - start_time
    
    print(f"\nExport time for 3x10MB artifacts: {export_time:.2f}s")
    
    # Verify export
    assert result_path.exists()
    export_size = result_path.stat().st_size
    
    print(f"Export ZIP size: {export_size / (1024*1024):.2f} MB")
    
    # ZIP should be smaller than original due to compression
    assert export_size > 0


def test_performance_comparison_compression_vs_no_compression(
    store_with_compression,
    store_without_compression
):
    """Compare performance with and without compression."""
    # Create 20 MB compressible content
    content = b"Performance test content. " * (20 * 1024 * 1024 // 26)
    
    # Test with compression
    start_time = time.time()
    uri_compressed = store_with_compression.upload(
        task_id="12.1",
        spec_name="perf-test",
        artifact_type=ArtifactType.LOG,
        content=content,
    )
    upload_time_compressed = time.time() - start_time
    
    start_time = time.time()
    downloaded_compressed = store_with_compression.download(uri_compressed)
    download_time_compressed = time.time() - start_time
    
    # Test without compression
    start_time = time.time()
    uri_uncompressed = store_without_compression.upload(
        task_id="12.1",
        spec_name="perf-test",
        artifact_type=ArtifactType.LOG,
        content=content,
    )
    upload_time_uncompressed = time.time() - start_time
    
    start_time = time.time()
    downloaded_uncompressed = store_without_compression.download(uri_uncompressed)
    download_time_uncompressed = time.time() - start_time
    
    # Print results
    print(f"\n=== Performance Comparison (20MB) ===")
    print(f"With compression:")
    print(f"  Upload: {upload_time_compressed:.2f}s")
    print(f"  Download: {download_time_compressed:.2f}s")
    print(f"  Total: {upload_time_compressed + download_time_compressed:.2f}s")
    
    print(f"Without compression:")
    print(f"  Upload: {upload_time_uncompressed:.2f}s")
    print(f"  Download: {download_time_uncompressed:.2f}s")
    print(f"  Total: {upload_time_uncompressed + download_time_uncompressed:.2f}s")
    
    # Get storage sizes
    metadata_compressed = store_with_compression.get_metadata(uri_compressed)
    metadata_uncompressed = store_without_compression.get_metadata(uri_uncompressed)
    
    print(f"\nStorage size:")
    print(f"  Compressed: {metadata_compressed.size / (1024*1024):.2f} MB")
    print(f"  Uncompressed: {metadata_uncompressed.size / (1024*1024):.2f} MB")
    print(f"  Space saved: {(metadata_uncompressed.size - metadata_compressed.size) / (1024*1024):.2f} MB")
    
    # Verify content
    assert downloaded_compressed == content
    assert downloaded_uncompressed == content

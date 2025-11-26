"""
Unit tests for Artifact Store compression engine.

Tests compression and decompression functionality.
Requirements: 8.1, 8.2, 8.3
"""

import pytest
import gzip
from necrocode.artifact_store.compression_engine import (
    CompressionEngine,
    CompressionResult,
    DecompressionResult,
)


def test_compression_engine_initialization():
    """Test CompressionEngine initialization with default values."""
    engine = CompressionEngine()
    
    assert engine.compression_level == 6
    assert engine.enabled is True


def test_compression_engine_initialization_custom():
    """Test CompressionEngine initialization with custom values."""
    engine = CompressionEngine(compression_level=9, enabled=False)
    
    assert engine.compression_level == 9
    assert engine.enabled is False


def test_compression_engine_invalid_level():
    """Test that invalid compression level raises error."""
    with pytest.raises(ValueError, match="Compression level must be between 0 and 9"):
        CompressionEngine(compression_level=10)
    
    with pytest.raises(ValueError, match="Compression level must be between 0 and 9"):
        CompressionEngine(compression_level=-1)


def test_compress_basic():
    """Test basic compression."""
    engine = CompressionEngine()
    data = b"Test content to compress" * 100
    
    result = engine.compress(data)
    
    assert isinstance(result, CompressionResult)
    assert result.original_size == len(data)
    assert result.compressed_size > 0
    assert result.compressed_size < result.original_size
    assert 0 < result.compression_ratio < 1.0
    assert len(result.compressed_data) == result.compressed_size


def test_compress_empty_data():
    """Test that compressing empty data raises error."""
    engine = CompressionEngine()
    
    with pytest.raises(ValueError, match="Cannot compress empty data"):
        engine.compress(b"")


def test_compress_with_disabled_compression():
    """Test compression when disabled returns original data."""
    engine = CompressionEngine(enabled=False)
    data = b"Test content"
    
    result = engine.compress(data)
    
    assert result.compressed_data == data
    assert result.original_size == len(data)
    assert result.compressed_size == len(data)
    assert result.compression_ratio == 1.0


def test_compress_different_levels():
    """Test compression with different levels."""
    data = b"Test content to compress" * 100
    
    # Level 1 (fast, less compression)
    engine1 = CompressionEngine(compression_level=1)
    result1 = engine1.compress(data)
    
    # Level 9 (slow, more compression)
    engine9 = CompressionEngine(compression_level=9)
    result9 = engine9.compress(data)
    
    # Level 9 should produce smaller output
    assert result9.compressed_size <= result1.compressed_size


def test_decompress_basic():
    """Test basic decompression."""
    engine = CompressionEngine()
    original_data = b"Test content to compress and decompress"
    
    # Compress first
    compress_result = engine.compress(original_data)
    
    # Decompress
    decompress_result = engine.decompress(compress_result.compressed_data)
    
    assert isinstance(decompress_result, DecompressionResult)
    assert decompress_result.decompressed_data == original_data
    assert decompress_result.compressed_size == compress_result.compressed_size
    assert decompress_result.decompressed_size == len(original_data)


def test_decompress_empty_data():
    """Test that decompressing empty data raises error."""
    engine = CompressionEngine()
    
    with pytest.raises(ValueError, match="Cannot decompress empty data"):
        engine.decompress(b"")


def test_decompress_invalid_data():
    """Test that decompressing invalid data raises error."""
    engine = CompressionEngine()
    invalid_data = b"This is not gzip compressed data"
    
    with pytest.raises(gzip.BadGzipFile):
        engine.decompress(invalid_data)


def test_decompress_with_disabled_compression():
    """Test decompression when disabled returns data as-is."""
    engine = CompressionEngine(enabled=False)
    data = b"Test content"
    
    result = engine.decompress(data)
    
    assert result.decompressed_data == data
    assert result.compressed_size == len(data)
    assert result.decompressed_size == len(data)


def test_compress_decompress_roundtrip():
    """Test compression and decompression roundtrip."""
    engine = CompressionEngine()
    original_data = b"Test content for roundtrip" * 50
    
    # Compress
    compress_result = engine.compress(original_data)
    
    # Decompress
    decompress_result = engine.decompress(compress_result.compressed_data)
    
    # Should get back original data
    assert decompress_result.decompressed_data == original_data


def test_compress_large_data():
    """Test compressing large data."""
    engine = CompressionEngine()
    large_data = b"x" * (10 * 1024 * 1024)  # 10 MB
    
    result = engine.compress(large_data)
    
    assert result.original_size == len(large_data)
    assert result.compressed_size < result.original_size
    
    # Verify decompression works
    decompress_result = engine.decompress(result.compressed_data)
    assert decompress_result.decompressed_data == large_data


def test_compress_already_compressed_data():
    """Test compressing already compressed data."""
    engine = CompressionEngine()
    data = b"Test content"
    
    # Compress once
    result1 = engine.compress(data)
    
    # Compress again (should still work but may not reduce size)
    result2 = engine.compress(result1.compressed_data)
    
    assert result2.compressed_size >= result1.compressed_size


def test_is_enabled():
    """Test is_enabled method."""
    engine_enabled = CompressionEngine(enabled=True)
    engine_disabled = CompressionEngine(enabled=False)
    
    assert engine_enabled.is_enabled() is True
    assert engine_disabled.is_enabled() is False


def test_set_enabled():
    """Test set_enabled method."""
    engine = CompressionEngine(enabled=True)
    
    assert engine.is_enabled() is True
    
    engine.set_enabled(False)
    assert engine.is_enabled() is False
    
    engine.set_enabled(True)
    assert engine.is_enabled() is True


def test_get_compression_level():
    """Test get_compression_level method."""
    engine = CompressionEngine(compression_level=7)
    
    assert engine.get_compression_level() == 7


def test_set_compression_level():
    """Test set_compression_level method."""
    engine = CompressionEngine(compression_level=6)
    
    assert engine.get_compression_level() == 6
    
    engine.set_compression_level(9)
    assert engine.get_compression_level() == 9
    
    engine.set_compression_level(1)
    assert engine.get_compression_level() == 1


def test_set_compression_level_invalid():
    """Test that setting invalid compression level raises error."""
    engine = CompressionEngine()
    
    with pytest.raises(ValueError, match="Compression level must be between 0 and 9"):
        engine.set_compression_level(10)
    
    with pytest.raises(ValueError, match="Compression level must be between 0 and 9"):
        engine.set_compression_level(-1)


def test_compression_ratio_calculation():
    """Test that compression ratio is calculated correctly."""
    engine = CompressionEngine()
    
    # Highly compressible data
    data = b"a" * 10000
    result = engine.compress(data)
    
    expected_ratio = result.compressed_size / result.original_size
    assert abs(result.compression_ratio - expected_ratio) < 0.001


def test_compression_result_attributes():
    """Test CompressionResult attributes."""
    engine = CompressionEngine()
    data = b"Test content"
    
    result = engine.compress(data)
    
    assert hasattr(result, 'compressed_data')
    assert hasattr(result, 'original_size')
    assert hasattr(result, 'compressed_size')
    assert hasattr(result, 'compression_ratio')
    assert isinstance(result.compressed_data, bytes)
    assert isinstance(result.original_size, int)
    assert isinstance(result.compressed_size, int)
    assert isinstance(result.compression_ratio, float)


def test_decompression_result_attributes():
    """Test DecompressionResult attributes."""
    engine = CompressionEngine()
    data = b"Test content"
    
    compress_result = engine.compress(data)
    decompress_result = engine.decompress(compress_result.compressed_data)
    
    assert hasattr(decompress_result, 'decompressed_data')
    assert hasattr(decompress_result, 'compressed_size')
    assert hasattr(decompress_result, 'decompressed_size')
    assert isinstance(decompress_result.decompressed_data, bytes)
    assert isinstance(decompress_result.compressed_size, int)
    assert isinstance(decompress_result.decompressed_size, int)


def test_compress_various_data_types():
    """Test compressing various types of data."""
    engine = CompressionEngine()
    
    # Text data
    text_data = b"This is some text content" * 100
    text_result = engine.compress(text_data)
    assert text_result.compressed_size < text_result.original_size
    
    # Binary data
    binary_data = bytes(range(256)) * 100
    binary_result = engine.compress(binary_data)
    assert binary_result.compressed_size < binary_result.original_size
    
    # Random-like data (less compressible)
    import random
    random.seed(42)
    random_data = bytes([random.randint(0, 255) for _ in range(10000)])
    random_result = engine.compress(random_data)
    # Random data may not compress well, but should still work
    assert random_result.compressed_size > 0


def test_compression_level_zero():
    """Test compression with level 0 (no compression, just gzip wrapper)."""
    engine = CompressionEngine(compression_level=0)
    data = b"Test content" * 100
    
    result = engine.compress(data)
    
    # Level 0 adds gzip wrapper but doesn't compress
    # So compressed size might be larger than original
    assert result.compressed_size > 0
    
    # But decompression should still work
    decompress_result = engine.decompress(result.compressed_data)
    assert decompress_result.decompressed_data == data

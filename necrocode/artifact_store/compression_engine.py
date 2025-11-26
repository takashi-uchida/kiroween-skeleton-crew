"""
Compression engine for artifact storage.

Provides gzip compression and decompression functionality for artifacts,
with metadata tracking for compression ratios and size information.
"""

import gzip
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class CompressionResult:
    """Result of a compression operation."""
    compressed_data: bytes
    original_size: int
    compressed_size: int
    compression_ratio: float


@dataclass
class DecompressionResult:
    """Result of a decompression operation."""
    decompressed_data: bytes
    compressed_size: int
    decompressed_size: int


class CompressionEngine:
    """
    Handles compression and decompression of artifact data.
    
    Uses gzip compression with configurable compression level.
    Tracks compression metadata including original and compressed sizes.
    """
    
    def __init__(self, compression_level: int = 6, enabled: bool = True):
        """
        Initialize the compression engine.
        
        Args:
            compression_level: Gzip compression level (0-9, default 6)
            enabled: Whether compression is enabled (default True)
        """
        if not 0 <= compression_level <= 9:
            raise ValueError("Compression level must be between 0 and 9")
        
        self.compression_level = compression_level
        self.enabled = enabled
        logger.info(
            f"CompressionEngine initialized: level={compression_level}, enabled={enabled}"
        )
    
    def compress(self, data: bytes) -> CompressionResult:
        """
        Compress data using gzip.
        
        Args:
            data: Raw bytes to compress
            
        Returns:
            CompressionResult with compressed data and metadata
            
        Raises:
            ValueError: If data is empty
        """
        if not data:
            raise ValueError("Cannot compress empty data")
        
        original_size = len(data)
        
        if not self.enabled:
            logger.debug("Compression disabled, returning original data")
            return CompressionResult(
                compressed_data=data,
                original_size=original_size,
                compressed_size=original_size,
                compression_ratio=1.0
            )
        
        try:
            compressed_data = gzip.compress(data, compresslevel=self.compression_level)
            compressed_size = len(compressed_data)
            compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
            
            logger.debug(
                f"Compressed {original_size} bytes to {compressed_size} bytes "
                f"(ratio: {compression_ratio:.2%})"
            )
            
            return CompressionResult(
                compressed_data=compressed_data,
                original_size=original_size,
                compressed_size=compressed_size,
                compression_ratio=compression_ratio
            )
        except Exception as e:
            logger.error(f"Compression failed: {e}")
            raise
    
    def decompress(self, compressed_data: bytes) -> DecompressionResult:
        """
        Decompress gzip-compressed data.
        
        Args:
            compressed_data: Gzip-compressed bytes
            
        Returns:
            DecompressionResult with decompressed data and metadata
            
        Raises:
            ValueError: If compressed_data is empty
            gzip.BadGzipFile: If data is not valid gzip format
        """
        if not compressed_data:
            raise ValueError("Cannot decompress empty data")
        
        compressed_size = len(compressed_data)
        
        if not self.enabled:
            logger.debug("Compression disabled, returning data as-is")
            return DecompressionResult(
                decompressed_data=compressed_data,
                compressed_size=compressed_size,
                decompressed_size=compressed_size
            )
        
        try:
            decompressed_data = gzip.decompress(compressed_data)
            decompressed_size = len(decompressed_data)
            
            logger.debug(
                f"Decompressed {compressed_size} bytes to {decompressed_size} bytes"
            )
            
            return DecompressionResult(
                decompressed_data=decompressed_data,
                compressed_size=compressed_size,
                decompressed_size=decompressed_size
            )
        except gzip.BadGzipFile as e:
            logger.error(f"Invalid gzip data: {e}")
            raise
        except Exception as e:
            logger.error(f"Decompression failed: {e}")
            raise
    
    def is_enabled(self) -> bool:
        """Check if compression is enabled."""
        return self.enabled
    
    def set_enabled(self, enabled: bool) -> None:
        """
        Enable or disable compression.
        
        Args:
            enabled: Whether to enable compression
        """
        self.enabled = enabled
        logger.info(f"Compression {'enabled' if enabled else 'disabled'}")
    
    def get_compression_level(self) -> int:
        """Get the current compression level."""
        return self.compression_level
    
    def set_compression_level(self, level: int) -> None:
        """
        Set the compression level.
        
        Args:
            level: Gzip compression level (0-9)
            
        Raises:
            ValueError: If level is not between 0 and 9
        """
        if not 0 <= level <= 9:
            raise ValueError("Compression level must be between 0 and 9")
        
        self.compression_level = level
        logger.info(f"Compression level set to {level}")

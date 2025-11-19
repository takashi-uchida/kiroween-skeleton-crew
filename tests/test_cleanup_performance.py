"""Performance tests for cleanup operations.

Tests cleanup performance and optimization.
Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
"""

import time
from pathlib import Path
import sys
import pytest
import statistics

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from necrocode.repo_pool.pool_manager import PoolManager
from necrocode.repo_pool.config import PoolConfig
from necrocode.repo_pool.git_operations import GitOperations


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def workspaces_dir(tmp_path):
    """Create temporary workspaces directory."""
    return tmp_path / "workspaces"


@pytest.fixture
def config(workspaces_dir):
    """Create PoolConfig instance."""
    return PoolConfig(
        workspaces_dir=workspaces_dir,
        default_num_slots=5,
        lock_timeout=30.0,
        cleanup_timeout=120.0,
    )


@pytest.fixture
def pool_manager(config):
    """Create PoolManager instance."""
    return PoolManager(config)


@pytest.fixture
def test_repo_url():
    """Return a test repository URL."""
    return "https://github.com/octocat/Hello-World.git"


@pytest.fixture
def cleanup_pool(pool_manager, test_repo_url):
    """Create a pool for cleanup testing."""
    pool = pool_manager.create_pool(
        repo_name="cleanup-perf",
        repo_url=test_repo_url,
        num_slots=5
    )
    return pool


# ============================================================================
# Basic Cleanup Performance Tests
# ============================================================================

def test_basic_cleanup_performance(pool_manager, cleanup_pool):
    """Test basic cleanup performance."""
    slot = pool_manager.allocate_slot("cleanup-perf")
    slot_path = slot.slot_path
    
    # Create some untracked files
    for i in range(10):
        (slot_path / f"file_{i}.txt").write_text(f"Content {i}")
    
    # Measure cleanup time
    start_time = time.time()
    pool_manager.release_slot(slot.slot_id)
    cleanup_time = time.time() - start_time
    
    print(f"\nBasic Cleanup Performance:")
    print(f"  Cleanup time: {cleanup_time:.3f}s")
    
    # Cleanup should be reasonably fast
    assert cleanup_time < 10.0


def test_cleanup_with_many_files_performance(pool_manager, cleanup_pool):
    """Test cleanup performance with many untracked files."""
    slot = pool_manager.allocate_slot("cleanup-perf")
    slot_path = slot.slot_path
    
    # Create many untracked files
    num_files = 100
    for i in range(num_files):
        (slot_path / f"file_{i}.txt").write_text(f"Content {i}")
    
    # Measure cleanup time
    start_time = time.time()
    pool_manager.release_slot(slot.slot_id)
    cleanup_time = time.time() - start_time
    
    print(f"\nCleanup with Many Files ({num_files} files):")
    print(f"  Cleanup time: {cleanup_time:.3f}s")
    print(f"  Time per file: {cleanup_time / num_files:.4f}s")
    
    # Should complete in reasonable time
    assert cleanup_time < 30.0


def test_cleanup_with_nested_directories_performance(pool_manager, cleanup_pool):
    """Test cleanup performance with nested directory structures."""
    slot = pool_manager.allocate_slot("cleanup-perf")
    slot_path = slot.slot_path
    
    # Create nested directory structure
    for i in range(10):
        dir_path = slot_path / f"dir_{i}" / f"subdir_{i}" / f"subsubdir_{i}"
        dir_path.mkdir(parents=True)
        (dir_path / "file.txt").write_text(f"Nested content {i}")
    
    # Measure cleanup time
    start_time = time.time()
    pool_manager.release_slot(slot.slot_id)
    cleanup_time = time.time() - start_time
    
    print(f"\nCleanup with Nested Directories:")
    print(f"  Cleanup time: {cleanup_time:.3f}s")
    
    assert cleanup_time < 15.0


# ============================================================================
# Git Operations Performance Tests
# ============================================================================

def test_git_fetch_performance(pool_manager, cleanup_pool):
    """Test git fetch performance."""
    slot = pool_manager.allocate_slot("cleanup-perf")
    git_ops = GitOperations()
    
    # Measure fetch time
    start_time = time.time()
    result = git_ops.fetch_all(slot.slot_path)
    fetch_time = time.time() - start_time
    
    print(f"\nGit Fetch Performance:")
    print(f"  Fetch time: {fetch_time:.3f}s")
    print(f"  Success: {result.success}")
    
    assert result.success
    # Fetch should complete in reasonable time
    assert fetch_time < 30.0


def test_git_clean_performance(pool_manager, cleanup_pool):
    """Test git clean performance."""
    slot = pool_manager.allocate_slot("cleanup-perf")
    slot_path = slot.slot_path
    git_ops = GitOperations()
    
    # Create untracked files
    for i in range(50):
        (slot_path / f"untracked_{i}.txt").write_text(f"Content {i}")
    
    # Measure clean time
    start_time = time.time()
    result = git_ops.clean(slot_path, force=True)
    clean_time = time.time() - start_time
    
    print(f"\nGit Clean Performance (50 files):")
    print(f"  Clean time: {clean_time:.3f}s")
    
    assert result.success
    assert clean_time < 10.0


def test_git_reset_performance(pool_manager, cleanup_pool):
    """Test git reset performance."""
    slot = pool_manager.allocate_slot("cleanup-perf")
    slot_path = slot.slot_path
    git_ops = GitOperations()
    
    # Modify tracked files
    readme_path = slot_path / "README"
    if readme_path.exists():
        readme_path.write_text("Modified content")
    
    # Measure reset time
    start_time = time.time()
    result = git_ops.reset_hard(slot_path)
    reset_time = time.time() - start_time
    
    print(f"\nGit Reset Performance:")
    print(f"  Reset time: {reset_time:.3f}s")
    
    assert result.success
    assert reset_time < 5.0


# ============================================================================
# Sequential Cleanup Performance Tests
# ============================================================================

def test_sequential_cleanup_cycles_performance(pool_manager, cleanup_pool):
    """Test performance of sequential cleanup cycles."""
    cleanup_times = []
    
    for cycle in range(10):
        slot = pool_manager.allocate_slot("cleanup-perf")
        slot_path = slot.slot_path
        
        # Create some files
        for i in range(10):
            (slot_path / f"file_{i}.txt").write_text(f"Cycle {cycle}")
        
        # Measure cleanup
        start_time = time.time()
        pool_manager.release_slot(slot.slot_id)
        cleanup_time = time.time() - start_time
        cleanup_times.append(cleanup_time)
    
    avg_time = statistics.mean(cleanup_times)
    min_time = min(cleanup_times)
    max_time = max(cleanup_times)
    
    print(f"\nSequential Cleanup Cycles (10 cycles):")
    print(f"  Average: {avg_time:.3f}s")
    print(f"  Min: {min_time:.3f}s")
    print(f"  Max: {max_time:.3f}s")
    
    # Average should be reasonable
    assert avg_time < 15.0


def test_cleanup_consistency_over_time(pool_manager, cleanup_pool):
    """Test that cleanup performance remains consistent."""
    early_times = []
    late_times = []
    
    # Early cleanups
    for i in range(5):
        slot = pool_manager.allocate_slot("cleanup-perf")
        (slot.slot_path / "test.txt").write_text("Test")
        
        start = time.time()
        pool_manager.release_slot(slot.slot_id)
        early_times.append(time.time() - start)
    
    # Late cleanups
    for i in range(5):
        slot = pool_manager.allocate_slot("cleanup-perf")
        (slot.slot_path / "test.txt").write_text("Test")
        
        start = time.time()
        pool_manager.release_slot(slot.slot_id)
        late_times.append(time.time() - start)
    
    early_avg = statistics.mean(early_times)
    late_avg = statistics.mean(late_times)
    
    print(f"\nCleanup Consistency:")
    print(f"  Early average: {early_avg:.3f}s")
    print(f"  Late average: {late_avg:.3f}s")
    
    # Performance should not degrade significantly
    assert late_avg < early_avg * 1.5


# ============================================================================
# Cleanup Result Tracking Performance
# ============================================================================

def test_cleanup_logging_performance(pool_manager, cleanup_pool):
    """Test performance impact of cleanup logging."""
    slot = pool_manager.allocate_slot("cleanup-perf")
    
    # Create files
    for i in range(20):
        (slot.slot_path / f"file_{i}.txt").write_text(f"Content {i}")
    
    # Measure cleanup with logging
    start_time = time.time()
    pool_manager.release_slot(slot.slot_id)
    cleanup_time = time.time() - start_time
    
    print(f"\nCleanup with Logging:")
    print(f"  Cleanup time: {cleanup_time:.3f}s")
    
    # Logging should not significantly impact performance
    assert cleanup_time < 15.0


# ============================================================================
# Slot Verification Performance Tests
# ============================================================================

def test_slot_integrity_verification_performance(pool_manager, cleanup_pool):
    """Test performance of slot integrity verification."""
    pool = pool_manager.get_pool("cleanup-perf")
    slot = pool.slots[0]
    
    # Measure verification time
    start_time = time.time()
    is_valid = pool_manager.slot_cleaner.verify_slot_integrity(slot)
    verify_time = time.time() - start_time
    
    print(f"\nSlot Integrity Verification:")
    print(f"  Verification time: {verify_time:.3f}s")
    print(f"  Is valid: {is_valid}")
    
    # Verification should be fast
    assert verify_time < 5.0


def test_multiple_slot_verification_performance(pool_manager, cleanup_pool):
    """Test performance of verifying multiple slots."""
    pool = pool_manager.get_pool("cleanup-perf")
    
    start_time = time.time()
    
    results = []
    for slot in pool.slots:
        is_valid = pool_manager.slot_cleaner.verify_slot_integrity(slot)
        results.append(is_valid)
    
    total_time = time.time() - start_time
    avg_time = total_time / len(pool.slots)
    
    print(f"\nMultiple Slot Verification (5 slots):")
    print(f"  Total time: {total_time:.3f}s")
    print(f"  Average per slot: {avg_time:.3f}s")
    
    assert total_time < 15.0


# ============================================================================
# Cleanup with Different File Sizes
# ============================================================================

def test_cleanup_small_files_performance(pool_manager, cleanup_pool):
    """Test cleanup performance with many small files."""
    slot = pool_manager.allocate_slot("cleanup-perf")
    slot_path = slot.slot_path
    
    # Create many small files (1KB each)
    num_files = 100
    for i in range(num_files):
        (slot_path / f"small_{i}.txt").write_text("x" * 1024)
    
    start_time = time.time()
    pool_manager.release_slot(slot.slot_id)
    cleanup_time = time.time() - start_time
    
    print(f"\nCleanup Small Files ({num_files} x 1KB):")
    print(f"  Cleanup time: {cleanup_time:.3f}s")
    print(f"  Time per file: {cleanup_time / num_files:.4f}s")
    
    assert cleanup_time < 30.0


def test_cleanup_large_files_performance(pool_manager, cleanup_pool):
    """Test cleanup performance with large files."""
    slot = pool_manager.allocate_slot("cleanup-perf")
    slot_path = slot.slot_path
    
    # Create a few large files (10MB each)
    num_files = 5
    file_size = 10 * 1024 * 1024  # 10MB
    
    for i in range(num_files):
        (slot_path / f"large_{i}.bin").write_bytes(b"x" * file_size)
    
    start_time = time.time()
    pool_manager.release_slot(slot.slot_id)
    cleanup_time = time.time() - start_time
    
    total_mb = (num_files * file_size) / (1024 * 1024)
    
    print(f"\nCleanup Large Files ({num_files} x 10MB = {total_mb:.0f}MB):")
    print(f"  Cleanup time: {cleanup_time:.3f}s")
    print(f"  MB per second: {total_mb / cleanup_time:.2f}")
    
    assert cleanup_time < 60.0


def test_cleanup_mixed_file_sizes_performance(pool_manager, cleanup_pool):
    """Test cleanup performance with mixed file sizes."""
    slot = pool_manager.allocate_slot("cleanup-perf")
    slot_path = slot.slot_path
    
    # Create mixed files
    # 50 small files (1KB)
    for i in range(50):
        (slot_path / f"small_{i}.txt").write_text("x" * 1024)
    
    # 5 medium files (1MB)
    for i in range(5):
        (slot_path / f"medium_{i}.bin").write_bytes(b"x" * (1024 * 1024))
    
    # 2 large files (5MB)
    for i in range(2):
        (slot_path / f"large_{i}.bin").write_bytes(b"x" * (5 * 1024 * 1024))
    
    start_time = time.time()
    pool_manager.release_slot(slot.slot_id)
    cleanup_time = time.time() - start_time
    
    print(f"\nCleanup Mixed Files (50 small + 5 medium + 2 large):")
    print(f"  Cleanup time: {cleanup_time:.3f}s")
    
    assert cleanup_time < 60.0


# ============================================================================
# Cleanup Optimization Tests
# ============================================================================

def test_cleanup_before_vs_after_allocation(pool_manager, cleanup_pool):
    """Compare cleanup performance before and after allocation."""
    # Cleanup before allocation
    slot1 = pool_manager.allocate_slot("cleanup-perf")
    (slot1.slot_path / "test.txt").write_text("Test")
    
    start = time.time()
    pool_manager.release_slot(slot1.slot_id)
    cleanup_after_time = time.time() - start
    
    # Next allocation triggers cleanup before
    start = time.time()
    slot2 = pool_manager.allocate_slot("cleanup-perf")
    allocation_time = time.time() - start
    
    print(f"\nCleanup Timing:")
    print(f"  Cleanup after release: {cleanup_after_time:.3f}s")
    print(f"  Allocation time (includes cleanup): {allocation_time:.3f}s")


def test_cleanup_result_overhead(pool_manager, cleanup_pool):
    """Test overhead of cleanup result tracking."""
    slot = pool_manager.allocate_slot("cleanup-perf")
    
    # Create files
    for i in range(10):
        (slot.slot_path / f"file_{i}.txt").write_text(f"Content {i}")
    
    # Measure cleanup
    start_time = time.time()
    pool_manager.release_slot(slot.slot_id)
    cleanup_time = time.time() - start_time
    
    print(f"\nCleanup Result Overhead:")
    print(f"  Total cleanup time: {cleanup_time:.3f}s")
    
    # Overhead should be minimal
    assert cleanup_time < 15.0


# ============================================================================
# Stress Tests
# ============================================================================

def test_rapid_cleanup_cycles(pool_manager, cleanup_pool):
    """Test rapid cleanup cycles."""
    num_cycles = 20
    cycle_times = []
    
    for i in range(num_cycles):
        slot = pool_manager.allocate_slot("cleanup-perf")
        (slot.slot_path / "test.txt").write_text("Test")
        
        start = time.time()
        pool_manager.release_slot(slot.slot_id)
        cycle_times.append(time.time() - start)
    
    avg_time = statistics.mean(cycle_times)
    total_time = sum(cycle_times)
    
    print(f"\nRapid Cleanup Cycles ({num_cycles} cycles):")
    print(f"  Total time: {total_time:.3f}s")
    print(f"  Average per cycle: {avg_time:.3f}s")
    print(f"  Cycles per second: {num_cycles / total_time:.2f}")
    
    assert avg_time < 10.0


def test_cleanup_under_memory_pressure(pool_manager, cleanup_pool):
    """Test cleanup performance under memory pressure."""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Perform cleanups
    for i in range(10):
        slot = pool_manager.allocate_slot("cleanup-perf")
        
        # Create files
        for j in range(20):
            (slot.slot_path / f"file_{j}.txt").write_text(f"Content {j}")
        
        pool_manager.release_slot(slot.slot_id)
    
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory
    
    print(f"\nCleanup Memory Usage:")
    print(f"  Initial: {initial_memory:.2f} MB")
    print(f"  Final: {final_memory:.2f} MB")
    print(f"  Increase: {memory_increase:.2f} MB")
    
    # Memory increase should be reasonable
    assert memory_increase < 100


# ============================================================================
# Comparative Performance Tests
# ============================================================================

def test_cleanup_performance_comparison(pool_manager, cleanup_pool):
    """Compare cleanup performance across different scenarios."""
    scenarios = {
        "empty": 0,
        "few_files": 10,
        "many_files": 50,
        "nested_dirs": 20,
    }
    
    results = {}
    
    for scenario, file_count in scenarios.items():
        slot = pool_manager.allocate_slot("cleanup-perf")
        slot_path = slot.slot_path
        
        # Setup scenario
        if scenario == "empty":
            pass  # No files
        elif scenario == "few_files":
            for i in range(file_count):
                (slot_path / f"file_{i}.txt").write_text(f"Content {i}")
        elif scenario == "many_files":
            for i in range(file_count):
                (slot_path / f"file_{i}.txt").write_text(f"Content {i}")
        elif scenario == "nested_dirs":
            for i in range(file_count):
                dir_path = slot_path / f"dir_{i}"
                dir_path.mkdir()
                (dir_path / "file.txt").write_text(f"Content {i}")
        
        # Measure cleanup
        start = time.time()
        pool_manager.release_slot(slot.slot_id)
        cleanup_time = time.time() - start
        
        results[scenario] = cleanup_time
    
    print(f"\nCleanup Performance Comparison:")
    for scenario, time_taken in results.items():
        print(f"  {scenario}: {time_taken:.3f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

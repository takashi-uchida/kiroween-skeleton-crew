"""Slot allocation strategy for Repo Pool Manager."""

import time
from collections import OrderedDict
from datetime import datetime
from typing import Dict, List, Optional

from necrocode.repo_pool.models import AllocationMetrics, Slot, SlotState
from necrocode.repo_pool.slot_store import SlotStore


class SlotAllocator:
    """
    Manages slot allocation strategy with LRU caching.
    
    This class implements the allocation logic for finding and assigning
    available slots to agents. It uses an LRU (Least Recently Used) cache
    strategy to prioritize recently used slots for better performance.
    """
    
    def __init__(self, slot_store: SlotStore):
        """
        Initialize SlotAllocator.
        
        Args:
            slot_store: SlotStore instance for persistence
        """
        self.slot_store = slot_store
        
        # LRU cache: repo_name -> OrderedDict[slot_id, last_used_timestamp]
        # OrderedDict maintains insertion order, most recent at the end
        self.lru_cache: Dict[str, OrderedDict] = {}
        
        # Allocation metrics tracking
        self._allocation_times: Dict[str, List[float]] = {}  # repo_name -> [duration_seconds]
        self._failed_allocations: Dict[str, int] = {}  # repo_name -> count
        self._cache_hits: Dict[str, int] = {}  # repo_name -> count
        self._cache_misses: Dict[str, int] = {}  # repo_name -> count
    
    def find_available_slot(self, repo_name: str) -> Optional[Slot]:
        """
        Find an available slot using LRU strategy.
        
        This method searches for available slots and prioritizes recently
        used slots (LRU cache hits) for better performance. If no cached
        slot is available, it falls back to any available slot.
        
        Args:
            repo_name: Name of the repository
            
        Returns:
            Available Slot object, or None if no slots available
        """
        start_time = time.time()
        
        try:
            # Load all slots for the repository
            slots = self.slot_store.list_slots(repo_name)
            
            if not slots:
                self._record_failed_allocation(repo_name)
                return None
            
            # Filter available slots
            available_slots = [s for s in slots if s.state == SlotState.AVAILABLE]
            
            if not available_slots:
                self._record_failed_allocation(repo_name)
                return None
            
            # Initialize LRU cache for this repo if not exists
            if repo_name not in self.lru_cache:
                self.lru_cache[repo_name] = OrderedDict()
            
            # Try to find a slot from LRU cache first (cache hit)
            cache = self.lru_cache[repo_name]
            for slot_id in reversed(cache.keys()):  # Most recent first
                slot = next((s for s in available_slots if s.slot_id == slot_id), None)
                if slot:
                    self._record_cache_hit(repo_name)
                    self._record_allocation_time(repo_name, time.time() - start_time)
                    return slot
            
            # No cache hit, select the most recently used available slot
            # Sort by last_allocated_at (most recent first)
            available_slots.sort(
                key=lambda s: s.last_allocated_at or datetime.min,
                reverse=True
            )
            
            selected_slot = available_slots[0]
            self._record_cache_miss(repo_name)
            self._record_allocation_time(repo_name, time.time() - start_time)
            
            return selected_slot
            
        except Exception as e:
            self._record_failed_allocation(repo_name)
            raise
    
    def mark_allocated(self, slot_id: str, metadata: Optional[Dict] = None) -> None:
        """
        Mark a slot as allocated and update its state.
        
        Args:
            slot_id: Slot identifier
            metadata: Optional metadata to attach to the slot
        """
        # Load the slot
        slot = self.slot_store.load_slot(slot_id)
        
        # Mark as allocated (updates state, timestamps, etc.)
        slot.mark_allocated(metadata)
        
        # Save updated slot
        self.slot_store.save_slot(slot)
        
        # Update LRU cache
        self.update_lru_cache(slot.repo_name, slot_id)
    
    def mark_available(self, slot_id: str) -> None:
        """
        Mark a slot as available (released).
        
        Args:
            slot_id: Slot identifier
        """
        # Load the slot
        slot = self.slot_store.load_slot(slot_id)
        
        # Mark as released (updates state, timestamps, usage stats)
        slot.mark_released()
        
        # Save updated slot
        self.slot_store.save_slot(slot)
    
    def update_lru_cache(self, repo_name: str, slot_id: str) -> None:
        """
        Update LRU cache with recently used slot.
        
        This method moves the slot to the end of the OrderedDict,
        making it the most recently used slot.
        
        Args:
            repo_name: Name of the repository
            slot_id: Slot identifier
        """
        if repo_name not in self.lru_cache:
            self.lru_cache[repo_name] = OrderedDict()
        
        cache = self.lru_cache[repo_name]
        
        # Remove if already exists (to re-add at the end)
        if slot_id in cache:
            del cache[slot_id]
        
        # Add to the end (most recent)
        cache[slot_id] = time.time()
        
        # Limit cache size to prevent unbounded growth
        # Keep only the 100 most recent slots
        max_cache_size = 100
        if len(cache) > max_cache_size:
            # Remove oldest entries
            for _ in range(len(cache) - max_cache_size):
                cache.popitem(last=False)
    
    def get_allocation_metrics(self, repo_name: str) -> AllocationMetrics:
        """
        Get allocation metrics for a repository.
        
        Args:
            repo_name: Name of the repository
            
        Returns:
            AllocationMetrics object with statistics
        """
        # Calculate total allocations
        cache_hits = self._cache_hits.get(repo_name, 0)
        cache_misses = self._cache_misses.get(repo_name, 0)
        total_allocations = cache_hits + cache_misses
        
        # Calculate average allocation time
        allocation_times = self._allocation_times.get(repo_name, [])
        avg_time = sum(allocation_times) / len(allocation_times) if allocation_times else 0.0
        
        # Calculate cache hit rate
        cache_hit_rate = cache_hits / total_allocations if total_allocations > 0 else 0.0
        
        # Get failed allocations
        failed_allocations = self._failed_allocations.get(repo_name, 0)
        
        return AllocationMetrics(
            repo_name=repo_name,
            total_allocations=total_allocations,
            average_allocation_time_seconds=avg_time,
            cache_hit_rate=cache_hit_rate,
            failed_allocations=failed_allocations,
        )
    
    def _record_allocation_time(self, repo_name: str, duration: float) -> None:
        """Record allocation time for metrics."""
        if repo_name not in self._allocation_times:
            self._allocation_times[repo_name] = []
        self._allocation_times[repo_name].append(duration)
        
        # Limit history to last 1000 allocations
        if len(self._allocation_times[repo_name]) > 1000:
            self._allocation_times[repo_name] = self._allocation_times[repo_name][-1000:]
    
    def _record_failed_allocation(self, repo_name: str) -> None:
        """Record failed allocation for metrics."""
        if repo_name not in self._failed_allocations:
            self._failed_allocations[repo_name] = 0
        self._failed_allocations[repo_name] += 1
    
    def _record_cache_hit(self, repo_name: str) -> None:
        """Record cache hit for metrics."""
        if repo_name not in self._cache_hits:
            self._cache_hits[repo_name] = 0
        self._cache_hits[repo_name] += 1
    
    def _record_cache_miss(self, repo_name: str) -> None:
        """Record cache miss for metrics."""
        if repo_name not in self._cache_misses:
            self._cache_misses[repo_name] = 0
        self._cache_misses[repo_name] += 1
    
    def clear_metrics(self, repo_name: Optional[str] = None) -> None:
        """
        Clear allocation metrics.
        
        Args:
            repo_name: Optional repository name. If None, clears all metrics.
        """
        if repo_name:
            self._allocation_times.pop(repo_name, None)
            self._failed_allocations.pop(repo_name, None)
            self._cache_hits.pop(repo_name, None)
            self._cache_misses.pop(repo_name, None)
        else:
            self._allocation_times.clear()
            self._failed_allocations.clear()
            self._cache_hits.clear()
            self._cache_misses.clear()

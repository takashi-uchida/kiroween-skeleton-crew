"""
Metrics Collector for Review & PR Service.

Collects and tracks metrics for pull requests including time to merge,
review comments, CI execution time, and merge rates.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
from collections import defaultdict

from necrocode.review_pr_service.models import PullRequest, PRMetrics, PRState, CIStatus
from necrocode.review_pr_service.exceptions import PRServiceError


logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collects and manages PR metrics.
    
    Tracks various metrics for PR analysis and reporting including:
    - Time to merge
    - Review comment count
    - CI execution time
    - Merge rate
    
    Requirements: 14.1, 14.2, 14.3, 14.4
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize metrics collector.
        
        Args:
            storage_path: Path to store metrics data (optional)
        """
        self.storage_path = storage_path
        self._metrics_cache: Dict[str, PRMetrics] = {}
        self._ci_start_times: Dict[str, datetime] = {}
        
        # Load existing metrics if storage path is provided
        if self.storage_path:
            self._load_metrics()
        
        logger.info(f"MetricsCollector initialized with storage: {storage_path}")
    
    def _load_metrics(self) -> None:
        """Load metrics from storage."""
        if not self.storage_path or not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                
            for pr_id, metrics_data in data.items():
                self._metrics_cache[pr_id] = PRMetrics.from_dict(metrics_data)
            
            logger.info(f"Loaded {len(self._metrics_cache)} metrics from storage")
        
        except Exception as e:
            logger.error(f"Failed to load metrics from storage: {e}")
    
    def _save_metrics(self) -> None:
        """Save metrics to storage."""
        if not self.storage_path:
            return
        
        try:
            # Ensure parent directory exists
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert metrics to dict
            data = {
                pr_id: metrics.to_dict()
                for pr_id, metrics in self._metrics_cache.items()
            }
            
            # Write to file
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved {len(self._metrics_cache)} metrics to storage")
        
        except Exception as e:
            logger.error(f"Failed to save metrics to storage: {e}")
    
    def record_pr_created(self, pr: PullRequest) -> PRMetrics:
        """
        Record PR creation and initialize metrics.
        
        Args:
            pr: PullRequest object
            
        Returns:
            PRMetrics object
            
        Requirements: 14.1
        """
        metrics = PRMetrics(pr_id=pr.pr_id)
        self._metrics_cache[pr.pr_id] = metrics
        
        logger.info(f"Initialized metrics for PR {pr.pr_number} ({pr.pr_id})")
        
        self._save_metrics()
        return metrics
    
    def record_pr_merged(self, pr: PullRequest) -> None:
        """
        Record PR merge and calculate time to merge.
        
        Args:
            pr: PullRequest object
            
        Requirements: 14.1
        """
        if pr.pr_id not in self._metrics_cache:
            logger.warning(f"No metrics found for PR {pr.pr_id}, initializing")
            self.record_pr_created(pr)
        
        metrics = self._metrics_cache[pr.pr_id]
        
        # Calculate time to merge
        if pr.merged_at and pr.created_at:
            time_to_merge = (pr.merged_at - pr.created_at).total_seconds()
            metrics.time_to_merge = time_to_merge
            
            logger.info(
                f"PR {pr.pr_number} merged in {time_to_merge:.2f} seconds "
                f"({time_to_merge / 3600:.2f} hours)"
            )
        
        self._save_metrics()
    
    def record_review_comment(self, pr_id: str) -> None:
        """
        Record a review comment on a PR.
        
        Args:
            pr_id: Pull request identifier
            
        Requirements: 14.2
        """
        if pr_id not in self._metrics_cache:
            logger.warning(f"No metrics found for PR {pr_id}, initializing")
            metrics = PRMetrics(pr_id=pr_id)
            self._metrics_cache[pr_id] = metrics
        
        metrics = self._metrics_cache[pr_id]
        metrics.review_comment_count += 1
        
        logger.debug(
            f"Recorded review comment for PR {pr_id} "
            f"(total: {metrics.review_comment_count})"
        )
        
        self._save_metrics()
    
    def record_ci_started(self, pr_id: str) -> None:
        """
        Record CI execution start time.
        
        Args:
            pr_id: Pull request identifier
            
        Requirements: 14.3
        """
        self._ci_start_times[pr_id] = datetime.now()
        logger.debug(f"Recorded CI start time for PR {pr_id}")
    
    def record_ci_completed(self, pr_id: str, status: CIStatus) -> None:
        """
        Record CI execution completion and calculate execution time.
        
        Args:
            pr_id: Pull request identifier
            status: CI status
            
        Requirements: 14.3
        """
        if pr_id not in self._metrics_cache:
            logger.warning(f"No metrics found for PR {pr_id}, initializing")
            metrics = PRMetrics(pr_id=pr_id)
            self._metrics_cache[pr_id] = metrics
        
        metrics = self._metrics_cache[pr_id]
        
        # Calculate CI execution time if start time was recorded
        if pr_id in self._ci_start_times:
            start_time = self._ci_start_times[pr_id]
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            metrics.ci_execution_time = execution_time
            
            logger.info(
                f"CI completed for PR {pr_id} with status {status.value} "
                f"in {execution_time:.2f} seconds"
            )
            
            # Clean up start time
            del self._ci_start_times[pr_id]
        else:
            logger.warning(f"No CI start time recorded for PR {pr_id}")
        
        self._save_metrics()
    
    def update_pr_stats(self, pr: PullRequest) -> None:
        """
        Update PR statistics (commits, files, lines).
        
        Args:
            pr: PullRequest object with updated metadata
            
        Requirements: 14.1
        """
        if pr.pr_id not in self._metrics_cache:
            logger.warning(f"No metrics found for PR {pr.pr_id}, initializing")
            self.record_pr_created(pr)
        
        metrics = self._metrics_cache[pr.pr_id]
        
        # Update from PR metadata if available
        if "commits_count" in pr.metadata:
            metrics.commits_count = pr.metadata["commits_count"]
        
        if "files_changed" in pr.metadata:
            metrics.files_changed = pr.metadata["files_changed"]
        
        if "lines_added" in pr.metadata:
            metrics.lines_added = pr.metadata["lines_added"]
        
        if "lines_deleted" in pr.metadata:
            metrics.lines_deleted = pr.metadata["lines_deleted"]
        
        logger.debug(
            f"Updated stats for PR {pr.pr_number}: "
            f"{metrics.commits_count} commits, {metrics.files_changed} files, "
            f"+{metrics.lines_added}/-{metrics.lines_deleted} lines"
        )
        
        self._save_metrics()
    
    def get_metrics(self, pr_id: str) -> Optional[PRMetrics]:
        """
        Get metrics for a specific PR.
        
        Args:
            pr_id: Pull request identifier
            
        Returns:
            PRMetrics object or None if not found
        """
        return self._metrics_cache.get(pr_id)
    
    def get_all_metrics(self) -> List[PRMetrics]:
        """
        Get all collected metrics.
        
        Returns:
            List of PRMetrics objects
        """
        return list(self._metrics_cache.values())
    
    def calculate_merge_rate(self, prs: List[PullRequest]) -> float:
        """
        Calculate merge rate from a list of PRs.
        
        Merge rate is the percentage of PRs that were merged vs closed/open.
        
        Args:
            prs: List of PullRequest objects
            
        Returns:
            Merge rate as a percentage (0-100)
            
        Requirements: 14.4
        """
        if not prs:
            return 0.0
        
        merged_count = sum(1 for pr in prs if pr.state == PRState.MERGED)
        total_count = len(prs)
        
        merge_rate = (merged_count / total_count) * 100
        
        logger.info(
            f"Calculated merge rate: {merge_rate:.2f}% "
            f"({merged_count}/{total_count} PRs merged)"
        )
        
        return merge_rate
    
    def get_aggregate_stats(self) -> Dict[str, Any]:
        """
        Get aggregate statistics across all PRs.
        
        Returns:
            Dictionary containing aggregate statistics
            
        Requirements: 14.1, 14.2, 14.3, 14.4
        """
        metrics_list = self.get_all_metrics()
        
        if not metrics_list:
            return {
                "total_prs": 0,
                "avg_time_to_merge": 0.0,
                "avg_review_comments": 0.0,
                "avg_ci_execution_time": 0.0,
                "total_commits": 0,
                "total_files_changed": 0,
                "total_lines_added": 0,
                "total_lines_deleted": 0,
            }
        
        # Calculate averages
        merge_times = [m.time_to_merge for m in metrics_list if m.time_to_merge is not None]
        ci_times = [m.ci_execution_time for m in metrics_list if m.ci_execution_time is not None]
        
        stats = {
            "total_prs": len(metrics_list),
            "avg_time_to_merge": sum(merge_times) / len(merge_times) if merge_times else 0.0,
            "avg_review_comments": sum(m.review_comment_count for m in metrics_list) / len(metrics_list),
            "avg_ci_execution_time": sum(ci_times) / len(ci_times) if ci_times else 0.0,
            "total_commits": sum(m.commits_count for m in metrics_list),
            "total_files_changed": sum(m.files_changed for m in metrics_list),
            "total_lines_added": sum(m.lines_added for m in metrics_list),
            "total_lines_deleted": sum(m.lines_deleted for m in metrics_list),
        }
        
        logger.info(f"Calculated aggregate stats for {len(metrics_list)} PRs")
        
        return stats
    
    def export_metrics(self, output_path: Path) -> None:
        """
        Export all metrics to a JSON file.
        
        Args:
            output_path: Path to export metrics to
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "metrics": [m.to_dict() for m in self.get_all_metrics()],
                "aggregate_stats": self.get_aggregate_stats(),
                "exported_at": datetime.now().isoformat(),
            }
            
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Exported metrics to {output_path}")
        
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
            raise PRServiceError(f"Metrics export failed: {e}") from e


class PrometheusExporter:
    """
    Exports PR metrics in Prometheus format.
    
    Provides metrics in a format compatible with Prometheus monitoring system.
    
    Requirements: 14.5
    """
    
    def __init__(self, metrics_collector: MetricsCollector):
        """
        Initialize Prometheus exporter.
        
        Args:
            metrics_collector: MetricsCollector instance
        """
        self.metrics_collector = metrics_collector
        logger.info("PrometheusExporter initialized")
    
    def export_metrics(self) -> str:
        """
        Export metrics in Prometheus text format.
        
        Returns:
            Metrics in Prometheus exposition format
            
        Requirements: 14.5
        """
        lines = []
        
        # Get aggregate stats
        stats = self.metrics_collector.get_aggregate_stats()
        
        # Total PRs
        lines.append("# HELP pr_total Total number of pull requests")
        lines.append("# TYPE pr_total counter")
        lines.append(f"pr_total {stats['total_prs']}")
        lines.append("")
        
        # Average time to merge
        lines.append("# HELP pr_time_to_merge_seconds Average time to merge PRs in seconds")
        lines.append("# TYPE pr_time_to_merge_seconds gauge")
        lines.append(f"pr_time_to_merge_seconds {stats['avg_time_to_merge']:.2f}")
        lines.append("")
        
        # Average review comments
        lines.append("# HELP pr_review_comments_avg Average number of review comments per PR")
        lines.append("# TYPE pr_review_comments_avg gauge")
        lines.append(f"pr_review_comments_avg {stats['avg_review_comments']:.2f}")
        lines.append("")
        
        # Average CI execution time
        lines.append("# HELP pr_ci_execution_seconds Average CI execution time in seconds")
        lines.append("# TYPE pr_ci_execution_seconds gauge")
        lines.append(f"pr_ci_execution_seconds {stats['avg_ci_execution_time']:.2f}")
        lines.append("")
        
        # Total commits
        lines.append("# HELP pr_commits_total Total number of commits across all PRs")
        lines.append("# TYPE pr_commits_total counter")
        lines.append(f"pr_commits_total {stats['total_commits']}")
        lines.append("")
        
        # Total files changed
        lines.append("# HELP pr_files_changed_total Total number of files changed across all PRs")
        lines.append("# TYPE pr_files_changed_total counter")
        lines.append(f"pr_files_changed_total {stats['total_files_changed']}")
        lines.append("")
        
        # Total lines added
        lines.append("# HELP pr_lines_added_total Total number of lines added across all PRs")
        lines.append("# TYPE pr_lines_added_total counter")
        lines.append(f"pr_lines_added_total {stats['total_lines_added']}")
        lines.append("")
        
        # Total lines deleted
        lines.append("# HELP pr_lines_deleted_total Total number of lines deleted across all PRs")
        lines.append("# TYPE pr_lines_deleted_total counter")
        lines.append(f"pr_lines_deleted_total {stats['total_lines_deleted']}")
        lines.append("")
        
        # Per-PR metrics (individual gauges)
        all_metrics = self.metrics_collector.get_all_metrics()
        
        if all_metrics:
            lines.append("# HELP pr_individual_time_to_merge_seconds Time to merge for individual PRs")
            lines.append("# TYPE pr_individual_time_to_merge_seconds gauge")
            for metrics in all_metrics:
                if metrics.time_to_merge is not None:
                    lines.append(
                        f'pr_individual_time_to_merge_seconds{{pr_id="{metrics.pr_id}"}} '
                        f'{metrics.time_to_merge:.2f}'
                    )
            lines.append("")
            
            lines.append("# HELP pr_individual_review_comments Number of review comments for individual PRs")
            lines.append("# TYPE pr_individual_review_comments gauge")
            for metrics in all_metrics:
                lines.append(
                    f'pr_individual_review_comments{{pr_id="{metrics.pr_id}"}} '
                    f'{metrics.review_comment_count}'
                )
            lines.append("")
            
            lines.append("# HELP pr_individual_ci_execution_seconds CI execution time for individual PRs")
            lines.append("# TYPE pr_individual_ci_execution_seconds gauge")
            for metrics in all_metrics:
                if metrics.ci_execution_time is not None:
                    lines.append(
                        f'pr_individual_ci_execution_seconds{{pr_id="{metrics.pr_id}"}} '
                        f'{metrics.ci_execution_time:.2f}'
                    )
            lines.append("")
        
        result = "\n".join(lines)
        logger.debug(f"Exported Prometheus metrics ({len(lines)} lines)")
        
        return result
    
    def export_to_file(self, output_path: Path) -> None:
        """
        Export metrics to a file in Prometheus format.
        
        Args:
            output_path: Path to export metrics to
            
        Requirements: 14.5
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            metrics_text = self.export_metrics()
            
            with open(output_path, 'w') as f:
                f.write(metrics_text)
            
            logger.info(f"Exported Prometheus metrics to {output_path}")
        
        except Exception as e:
            logger.error(f"Failed to export Prometheus metrics: {e}")
            raise PRServiceError(f"Prometheus export failed: {e}") from e

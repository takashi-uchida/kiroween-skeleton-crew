"""
Example demonstrating PR metrics collection and Prometheus export.

This example shows how to:
1. Initialize metrics collector
2. Record PR metrics (creation, merge, comments, CI)
3. Get aggregate statistics
4. Export metrics in JSON and Prometheus formats
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from necrocode.review_pr_service.models import PullRequest, PRState, CIStatus
from necrocode.review_pr_service.metrics_collector import MetricsCollector, PrometheusExporter


def main():
    """Demonstrate metrics collection functionality."""
    
    print("=" * 80)
    print("PR Metrics Collection Example")
    print("=" * 80)
    print()
    
    # Initialize metrics collector with storage
    storage_path = Path("/tmp/pr_metrics_example.json")
    collector = MetricsCollector(storage_path=storage_path)
    print(f"✓ Initialized MetricsCollector with storage: {storage_path}")
    print()
    
    # Create sample PRs
    print("Creating sample PRs...")
    print("-" * 80)
    
    prs = []
    
    # PR 1: Merged successfully
    pr1 = PullRequest(
        pr_id="pr-001",
        pr_number=101,
        title="Add user authentication",
        description="Implements JWT authentication",
        source_branch="feature/auth",
        target_branch="main",
        url="https://github.com/example/repo/pull/101",
        state=PRState.MERGED,
        draft=False,
        created_at=datetime.now() - timedelta(hours=24),
        merged_at=datetime.now() - timedelta(hours=2),
        metadata={
            "commits_count": 5,
            "files_changed": 8,
            "lines_added": 250,
            "lines_deleted": 30,
        }
    )
    prs.append(pr1)
    
    # Record PR 1 metrics
    collector.record_pr_created(pr1)
    collector.update_pr_stats(pr1)
    
    # Simulate CI execution
    collector.record_ci_started(pr1.pr_id)
    collector.record_ci_completed(pr1.pr_id, CIStatus.SUCCESS)
    
    # Simulate review comments
    for _ in range(3):
        collector.record_review_comment(pr1.pr_id)
    
    # Record merge
    collector.record_pr_merged(pr1)
    
    print(f"✓ PR #{pr1.pr_number}: {pr1.title}")
    print(f"  State: {pr1.state.value}")
    print(f"  Time to merge: {(pr1.merged_at - pr1.created_at).total_seconds() / 3600:.2f} hours")
    print()
    
    # PR 2: Open with CI running
    pr2 = PullRequest(
        pr_id="pr-002",
        pr_number=102,
        title="Update frontend components",
        description="Refactors React components",
        source_branch="feature/frontend-refactor",
        target_branch="main",
        url="https://github.com/example/repo/pull/102",
        state=PRState.OPEN,
        draft=False,
        created_at=datetime.now() - timedelta(hours=6),
        metadata={
            "commits_count": 12,
            "files_changed": 15,
            "lines_added": 450,
            "lines_deleted": 200,
        }
    )
    prs.append(pr2)
    
    # Record PR 2 metrics
    collector.record_pr_created(pr2)
    collector.update_pr_stats(pr2)
    
    # Simulate CI execution
    collector.record_ci_started(pr2.pr_id)
    collector.record_ci_completed(pr2.pr_id, CIStatus.SUCCESS)
    
    # Simulate review comments
    for _ in range(5):
        collector.record_review_comment(pr2.pr_id)
    
    print(f"✓ PR #{pr2.pr_number}: {pr2.title}")
    print(f"  State: {pr2.state.value}")
    print(f"  Review comments: 5")
    print()
    
    # PR 3: Merged with longer review cycle
    pr3 = PullRequest(
        pr_id="pr-003",
        pr_number=103,
        title="Database schema migration",
        description="Adds new tables for analytics",
        source_branch="feature/db-migration",
        target_branch="main",
        url="https://github.com/example/repo/pull/103",
        state=PRState.MERGED,
        draft=False,
        created_at=datetime.now() - timedelta(days=3),
        merged_at=datetime.now() - timedelta(hours=12),
        metadata={
            "commits_count": 3,
            "files_changed": 4,
            "lines_added": 120,
            "lines_deleted": 10,
        }
    )
    prs.append(pr3)
    
    # Record PR 3 metrics
    collector.record_pr_created(pr3)
    collector.update_pr_stats(pr3)
    
    # Simulate CI execution
    collector.record_ci_started(pr3.pr_id)
    collector.record_ci_completed(pr3.pr_id, CIStatus.SUCCESS)
    
    # Simulate many review comments
    for _ in range(8):
        collector.record_review_comment(pr3.pr_id)
    
    # Record merge
    collector.record_pr_merged(pr3)
    
    print(f"✓ PR #{pr3.pr_number}: {pr3.title}")
    print(f"  State: {pr3.state.value}")
    print(f"  Time to merge: {(pr3.merged_at - pr3.created_at).total_seconds() / 3600:.2f} hours")
    print()
    
    # Get individual PR metrics
    print("=" * 80)
    print("Individual PR Metrics")
    print("=" * 80)
    print()
    
    for pr in prs:
        metrics = collector.get_metrics(pr.pr_id)
        if metrics:
            print(f"PR #{pr.pr_number} ({pr.pr_id}):")
            print(f"  Time to merge: {metrics.time_to_merge / 3600:.2f} hours" if metrics.time_to_merge else "  Time to merge: N/A")
            print(f"  Review comments: {metrics.review_comment_count}")
            print(f"  CI execution time: {metrics.ci_execution_time:.2f}s" if metrics.ci_execution_time else "  CI execution time: N/A")
            print(f"  Commits: {metrics.commits_count}")
            print(f"  Files changed: {metrics.files_changed}")
            print(f"  Lines: +{metrics.lines_added}/-{metrics.lines_deleted}")
            print()
    
    # Get aggregate statistics
    print("=" * 80)
    print("Aggregate Statistics")
    print("=" * 80)
    print()
    
    stats = collector.get_aggregate_stats()
    print(f"Total PRs: {stats['total_prs']}")
    print(f"Average time to merge: {stats['avg_time_to_merge'] / 3600:.2f} hours")
    print(f"Average review comments: {stats['avg_review_comments']:.2f}")
    print(f"Average CI execution time: {stats['avg_ci_execution_time']:.2f}s")
    print(f"Total commits: {stats['total_commits']}")
    print(f"Total files changed: {stats['total_files_changed']}")
    print(f"Total lines added: {stats['total_lines_added']}")
    print(f"Total lines deleted: {stats['total_lines_deleted']}")
    print()
    
    # Calculate merge rate
    print("=" * 80)
    print("Merge Rate")
    print("=" * 80)
    print()
    
    merge_rate = collector.calculate_merge_rate(prs)
    print(f"Merge rate: {merge_rate:.2f}%")
    print(f"({sum(1 for pr in prs if pr.state == PRState.MERGED)}/{len(prs)} PRs merged)")
    print()
    
    # Export metrics to JSON
    print("=" * 80)
    print("Exporting Metrics")
    print("=" * 80)
    print()
    
    json_output = Path("/tmp/pr_metrics_export.json")
    collector.export_metrics(json_output)
    print(f"✓ Exported metrics to JSON: {json_output}")
    print()
    
    # Export metrics to Prometheus format
    prometheus_exporter = PrometheusExporter(collector)
    
    prometheus_output = Path("/tmp/pr_metrics.prom")
    prometheus_exporter.export_to_file(prometheus_output)
    print(f"✓ Exported metrics to Prometheus format: {prometheus_output}")
    print()
    
    # Display Prometheus metrics
    print("=" * 80)
    print("Prometheus Metrics (sample)")
    print("=" * 80)
    print()
    
    prometheus_text = prometheus_exporter.export_metrics()
    # Show first 20 lines
    lines = prometheus_text.split('\n')[:20]
    for line in lines:
        print(line)
    print("...")
    print(f"(Total: {len(prometheus_text.split(chr(10)))} lines)")
    print()
    
    print("=" * 80)
    print("Example Complete!")
    print("=" * 80)
    print()
    print("Files created:")
    print(f"  - {storage_path} (metrics storage)")
    print(f"  - {json_output} (JSON export)")
    print(f"  - {prometheus_output} (Prometheus export)")
    print()
    print("You can:")
    print("  1. View the JSON export for detailed metrics")
    print("  2. Use the Prometheus export with Prometheus/Grafana")
    print("  3. Integrate metrics collection into your PR workflow")


if __name__ == "__main__":
    main()

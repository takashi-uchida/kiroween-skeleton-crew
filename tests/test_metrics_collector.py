"""
Tests for PR metrics collection functionality.
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
import tempfile
import json

from necrocode.review_pr_service.models import PullRequest, PRState, CIStatus, PRMetrics
from necrocode.review_pr_service.metrics_collector import MetricsCollector, PrometheusExporter


class TestPRMetrics:
    """Test PRMetrics data model."""
    
    def test_metrics_creation(self):
        """Test creating PRMetrics instance."""
        metrics = PRMetrics(
            pr_id="pr-001",
            time_to_merge=3600.0,
            review_comment_count=5,
            ci_execution_time=120.0,
            commits_count=3,
            files_changed=10,
            lines_added=150,
            lines_deleted=50,
        )
        
        assert metrics.pr_id == "pr-001"
        assert metrics.time_to_merge == 3600.0
        assert metrics.review_comment_count == 5
        assert metrics.ci_execution_time == 120.0
    
    def test_metrics_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = PRMetrics(pr_id="pr-001", review_comment_count=3)
        data = metrics.to_dict()
        
        assert isinstance(data, dict)
        assert data["pr_id"] == "pr-001"
        assert data["review_comment_count"] == 3
    
    def test_metrics_from_dict(self):
        """Test creating metrics from dictionary."""
        data = {
            "pr_id": "pr-001",
            "time_to_merge": 1800.0,
            "review_comment_count": 2,
        }
        
        metrics = PRMetrics.from_dict(data)
        
        assert metrics.pr_id == "pr-001"
        assert metrics.time_to_merge == 1800.0
        assert metrics.review_comment_count == 2


class TestMetricsCollector:
    """Test MetricsCollector functionality."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)
        yield temp_path
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()
    
    @pytest.fixture
    def collector(self, temp_storage):
        """Create MetricsCollector instance."""
        return MetricsCollector(storage_path=temp_storage)
    
    @pytest.fixture
    def sample_pr(self):
        """Create sample PullRequest."""
        return PullRequest(
            pr_id="pr-001",
            pr_number=101,
            title="Test PR",
            description="Test description",
            source_branch="feature/test",
            target_branch="main",
            url="https://github.com/test/repo/pull/101",
            state=PRState.OPEN,
            draft=False,
            created_at=datetime.now() - timedelta(hours=2),
        )
    
    def test_collector_initialization(self, temp_storage):
        """Test initializing metrics collector."""
        collector = MetricsCollector(storage_path=temp_storage)
        
        assert collector.storage_path == temp_storage
        assert isinstance(collector._metrics_cache, dict)
    
    def test_record_pr_created(self, collector, sample_pr):
        """Test recording PR creation."""
        metrics = collector.record_pr_created(sample_pr)
        
        assert metrics.pr_id == sample_pr.pr_id
        assert sample_pr.pr_id in collector._metrics_cache
    
    def test_record_pr_merged(self, collector, sample_pr):
        """Test recording PR merge."""
        # First create the PR
        collector.record_pr_created(sample_pr)
        
        # Mark as merged
        sample_pr.mark_as_merged()
        
        # Record merge
        collector.record_pr_merged(sample_pr)
        
        metrics = collector.get_metrics(sample_pr.pr_id)
        assert metrics is not None
        assert metrics.time_to_merge is not None
        assert metrics.time_to_merge > 0
    
    def test_record_review_comment(self, collector):
        """Test recording review comments."""
        pr_id = "pr-001"
        
        # Record multiple comments
        collector.record_review_comment(pr_id)
        collector.record_review_comment(pr_id)
        collector.record_review_comment(pr_id)
        
        metrics = collector.get_metrics(pr_id)
        assert metrics is not None
        assert metrics.review_comment_count == 3
    
    def test_record_ci_execution(self, collector):
        """Test recording CI execution time."""
        pr_id = "pr-001"
        
        # Record CI start
        collector.record_ci_started(pr_id)
        
        # Simulate some time passing
        import time
        time.sleep(0.1)
        
        # Record CI completion
        collector.record_ci_completed(pr_id, CIStatus.SUCCESS)
        
        metrics = collector.get_metrics(pr_id)
        assert metrics is not None
        assert metrics.ci_execution_time is not None
        assert metrics.ci_execution_time > 0
    
    def test_update_pr_stats(self, collector, sample_pr):
        """Test updating PR statistics."""
        # Add metadata
        sample_pr.metadata = {
            "commits_count": 5,
            "files_changed": 10,
            "lines_added": 200,
            "lines_deleted": 50,
        }
        
        # Record and update
        collector.record_pr_created(sample_pr)
        collector.update_pr_stats(sample_pr)
        
        metrics = collector.get_metrics(sample_pr.pr_id)
        assert metrics.commits_count == 5
        assert metrics.files_changed == 10
        assert metrics.lines_added == 200
        assert metrics.lines_deleted == 50
    
    def test_get_all_metrics(self, collector, sample_pr):
        """Test getting all metrics."""
        # Create multiple PRs
        collector.record_pr_created(sample_pr)
        
        pr2 = PullRequest(
            pr_id="pr-002",
            pr_number=102,
            title="Test PR 2",
            description="Test description 2",
            source_branch="feature/test2",
            target_branch="main",
            url="https://github.com/test/repo/pull/102",
            state=PRState.OPEN,
            draft=False,
            created_at=datetime.now(),
        )
        collector.record_pr_created(pr2)
        
        all_metrics = collector.get_all_metrics()
        assert len(all_metrics) == 2
    
    def test_calculate_merge_rate(self, collector):
        """Test calculating merge rate."""
        prs = []
        
        # Create merged PRs
        for i in range(3):
            pr = PullRequest(
                pr_id=f"pr-{i}",
                pr_number=100 + i,
                title=f"PR {i}",
                description="Test",
                source_branch=f"feature/{i}",
                target_branch="main",
                url=f"https://github.com/test/repo/pull/{100+i}",
                state=PRState.MERGED,
                draft=False,
                created_at=datetime.now(),
            )
            prs.append(pr)
        
        # Create open PR
        pr_open = PullRequest(
            pr_id="pr-open",
            pr_number=104,
            title="Open PR",
            description="Test",
            source_branch="feature/open",
            target_branch="main",
            url="https://github.com/test/repo/pull/104",
            state=PRState.OPEN,
            draft=False,
            created_at=datetime.now(),
        )
        prs.append(pr_open)
        
        merge_rate = collector.calculate_merge_rate(prs)
        assert merge_rate == 75.0  # 3 out of 4 merged
    
    def test_get_aggregate_stats(self, collector, sample_pr):
        """Test getting aggregate statistics."""
        # Create PR with metrics
        sample_pr.metadata = {
            "commits_count": 5,
            "files_changed": 10,
            "lines_added": 200,
            "lines_deleted": 50,
        }
        
        collector.record_pr_created(sample_pr)
        collector.update_pr_stats(sample_pr)
        collector.record_review_comment(sample_pr.pr_id)
        collector.record_review_comment(sample_pr.pr_id)
        
        stats = collector.get_aggregate_stats()
        
        assert stats["total_prs"] == 1
        assert stats["avg_review_comments"] == 2.0
        assert stats["total_commits"] == 5
        assert stats["total_files_changed"] == 10
        assert stats["total_lines_added"] == 200
        assert stats["total_lines_deleted"] == 50
    
    def test_metrics_persistence(self, temp_storage):
        """Test metrics persistence to storage."""
        # Create collector and add metrics
        collector1 = MetricsCollector(storage_path=temp_storage)
        
        pr = PullRequest(
            pr_id="pr-001",
            pr_number=101,
            title="Test PR",
            description="Test",
            source_branch="feature/test",
            target_branch="main",
            url="https://github.com/test/repo/pull/101",
            state=PRState.OPEN,
            draft=False,
            created_at=datetime.now(),
        )
        
        collector1.record_pr_created(pr)
        collector1.record_review_comment(pr.pr_id)
        
        # Create new collector and verify metrics loaded
        collector2 = MetricsCollector(storage_path=temp_storage)
        
        metrics = collector2.get_metrics(pr.pr_id)
        assert metrics is not None
        assert metrics.pr_id == pr.pr_id
        assert metrics.review_comment_count == 1
    
    def test_export_metrics(self, collector, sample_pr, temp_storage):
        """Test exporting metrics to JSON."""
        collector.record_pr_created(sample_pr)
        
        export_path = temp_storage.parent / "export.json"
        collector.export_metrics(export_path)
        
        assert export_path.exists()
        
        # Verify export content
        with open(export_path, 'r') as f:
            data = json.load(f)
        
        assert "metrics" in data
        assert "aggregate_stats" in data
        assert "exported_at" in data
        assert len(data["metrics"]) == 1
        
        # Cleanup
        export_path.unlink()


class TestPrometheusExporter:
    """Test Prometheus metrics export."""
    
    @pytest.fixture
    def collector_with_data(self):
        """Create collector with sample data."""
        collector = MetricsCollector()
        
        # Add sample metrics
        pr = PullRequest(
            pr_id="pr-001",
            pr_number=101,
            title="Test PR",
            description="Test",
            source_branch="feature/test",
            target_branch="main",
            url="https://github.com/test/repo/pull/101",
            state=PRState.MERGED,
            draft=False,
            created_at=datetime.now() - timedelta(hours=2),
            merged_at=datetime.now(),
        )
        
        collector.record_pr_created(pr)
        collector.record_pr_merged(pr)
        collector.record_review_comment(pr.pr_id)
        
        return collector
    
    def test_prometheus_exporter_initialization(self, collector_with_data):
        """Test initializing Prometheus exporter."""
        exporter = PrometheusExporter(collector_with_data)
        
        assert exporter.metrics_collector == collector_with_data
    
    def test_export_prometheus_format(self, collector_with_data):
        """Test exporting metrics in Prometheus format."""
        exporter = PrometheusExporter(collector_with_data)
        
        metrics_text = exporter.export_metrics()
        
        assert isinstance(metrics_text, str)
        assert len(metrics_text) > 0
        
        # Check for expected metric names
        assert "pr_total" in metrics_text
        assert "pr_time_to_merge_seconds" in metrics_text
        assert "pr_review_comments_avg" in metrics_text
        assert "pr_ci_execution_seconds" in metrics_text
        
        # Check for HELP and TYPE comments
        assert "# HELP" in metrics_text
        assert "# TYPE" in metrics_text
    
    def test_export_to_file(self, collector_with_data):
        """Test exporting Prometheus metrics to file."""
        exporter = PrometheusExporter(collector_with_data)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.prom', delete=False) as f:
            output_path = Path(f.name)
        
        try:
            exporter.export_to_file(output_path)
            
            assert output_path.exists()
            
            # Verify file content
            with open(output_path, 'r') as f:
                content = f.read()
            
            assert len(content) > 0
            assert "pr_total" in content
        
        finally:
            if output_path.exists():
                output_path.unlink()
    
    def test_prometheus_metrics_format(self, collector_with_data):
        """Test Prometheus metrics format compliance."""
        exporter = PrometheusExporter(collector_with_data)
        
        metrics_text = exporter.export_metrics()
        lines = metrics_text.split('\n')
        
        # Check format compliance
        for line in lines:
            if line.strip() and not line.startswith('#'):
                # Metric lines should have format: metric_name{labels} value
                # or: metric_name value
                parts = line.split()
                assert len(parts) >= 2, f"Invalid metric line: {line}"
                
                # Value should be numeric
                try:
                    float(parts[-1])
                except ValueError:
                    pytest.fail(f"Non-numeric value in metric line: {line}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

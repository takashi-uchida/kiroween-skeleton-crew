"""
Unit tests for PRTemplateEngine.

Tests template loading, generation, and formatting functionality.
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

# Mock jinja2 before importing PRTemplateEngine
jinja2_mock = MagicMock()
jinja2_mock.Environment = MagicMock
jinja2_mock.FileSystemLoader = MagicMock
jinja2_mock.Template = MagicMock
jinja2_mock.TemplateNotFound = Exception

import sys
sys.modules['jinja2'] = jinja2_mock

from necrocode.review_pr_service.pr_template_engine import PRTemplateEngine
from necrocode.review_pr_service.config import PRServiceConfig, TemplateConfig
from necrocode.task_registry.models import Task, TaskState, Artifact, ArtifactType


class TestPRTemplateEngine:
    """Test suite for PRTemplateEngine."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return PRServiceConfig(
            repository="test/repo",
            template=TemplateConfig(
                template_path="templates/pr-template.md",
                include_test_results=True,
                include_artifact_links=True,
                include_execution_logs=True
            )
        )
    
    @pytest.fixture
    def engine(self, config):
        """Create PRTemplateEngine instance."""
        with patch('necrocode.review_pr_service.pr_template_engine.Environment'):
            return PRTemplateEngine(config)
    
    @pytest.fixture
    def sample_task(self):
        """Create sample task."""
        return Task(
            id="2.1",
            title="Implement Authentication",
            description="Add JWT authentication endpoints",
            state=TaskState.DONE,
            dependencies=["1.1"]
        )
    
    @pytest.fixture
    def sample_artifacts(self):
        """Create sample artifacts."""
        return [
            Artifact(
                type=ArtifactType.DIFF,
                uri="https://example.com/diff.patch",
                size_bytes=4096
            ),
            Artifact(
                type=ArtifactType.TEST_RESULT,
                uri="https://example.com/test.json",
                size_bytes=2048,
                metadata={
                    "total_tests": 10,
                    "passed": 9,
                    "failed": 1,
                    "skipped": 0,
                    "duration": 5.2
                }
            ),
            Artifact(
                type=ArtifactType.LOG,
                uri="https://example.com/log.txt",
                size_bytes=8192,
                metadata={
                    "name": "Execution Log",
                    "execution_time": 30.5,
                    "has_errors": False
                }
            )
        ]
    
    def test_initialization(self, config):
        """Test PRTemplateEngine initialization."""
        with patch('necrocode.review_pr_service.pr_template_engine.Environment'):
            engine = PRTemplateEngine(config)
            assert engine.config == config
            assert engine.template_config == config.template
    
    def test_format_test_results_with_data(self, engine, sample_artifacts):
        """Test formatting test results with complete data."""
        result = engine._format_test_results(sample_artifacts)
        
        assert result is not None
        assert "Total: 10" in result
        assert "Passed: 9" in result
        assert "Failed: 1" in result
        assert "Pass Rate: 90.0%" in result
        assert "Duration: 5.20s" in result
        assert "View Full Test Results" in result
    
    def test_format_test_results_no_artifacts(self, engine):
        """Test formatting test results with no artifacts."""
        result = engine._format_test_results([])
        assert result is None
    
    def test_format_test_results_no_test_artifacts(self, engine):
        """Test formatting test results with no test artifacts."""
        artifacts = [
            Artifact(
                type=ArtifactType.DIFF,
                uri="https://example.com/diff.patch"
            )
        ]
        result = engine._format_test_results(artifacts)
        assert result is None
    
    def test_format_artifact_links_single_type(self, engine):
        """Test formatting artifact links with single artifact per type."""
        artifacts = [
            Artifact(
                type=ArtifactType.DIFF,
                uri="https://example.com/diff.patch",
                size_bytes=4096
            )
        ]
        
        result = engine._format_artifact_links(artifacts)
        
        assert result is not None
        assert "Code Changes" in result
        assert "https://example.com/diff.patch" in result
        assert "4.0 KB" in result
    
    def test_format_artifact_links_multiple_types(self, engine, sample_artifacts):
        """Test formatting artifact links with multiple types."""
        result = engine._format_artifact_links(sample_artifacts)
        
        assert result is not None
        assert "Code Changes" in result
        assert "Test Results" in result
        assert "Execution Logs" in result
    
    def test_format_artifact_links_no_artifacts(self, engine):
        """Test formatting artifact links with no artifacts."""
        result = engine._format_artifact_links([])
        assert result is None
    
    def test_format_artifact_links_large_file(self, engine):
        """Test formatting artifact links with large file."""
        artifacts = [
            Artifact(
                type=ArtifactType.LOG,
                uri="https://example.com/large.log",
                size_bytes=5 * 1024 * 1024  # 5 MB
            )
        ]
        
        result = engine._format_artifact_links(artifacts)
        
        assert result is not None
        assert "5.0 MB" in result
    
    def test_format_execution_logs_with_data(self, engine, sample_artifacts):
        """Test formatting execution logs with data."""
        result = engine._format_execution_logs(sample_artifacts)
        
        assert result is not None
        assert "Execution Log" in result
        assert "Duration: 30.50s" in result
        assert "View Log" in result
    
    def test_format_execution_logs_with_errors(self, engine):
        """Test formatting execution logs with errors."""
        artifacts = [
            Artifact(
                type=ArtifactType.LOG,
                uri="https://example.com/error.log",
                metadata={
                    "name": "Error Log",
                    "has_errors": True,
                    "error_count": 3
                }
            )
        ]
        
        result = engine._format_execution_logs(artifacts)
        
        assert result is not None
        assert "Contains 3 error(s)" in result
    
    def test_format_execution_logs_no_artifacts(self, engine):
        """Test formatting execution logs with no artifacts."""
        result = engine._format_execution_logs([])
        assert result is None
    
    def test_set_custom_section(self, engine):
        """Test adding custom section."""
        engine.set_custom_section("Breaking Changes", "None")
        
        assert "Breaking Changes" in engine.template_config.custom_sections
        assert engine.template_config.custom_sections["Breaking Changes"] == "None"
    
    def test_remove_custom_section(self, engine):
        """Test removing custom section."""
        engine.set_custom_section("Test Section", "Content")
        engine.remove_custom_section("Test Section")
        
        assert "Test Section" not in engine.template_config.custom_sections
    
    def test_clear_custom_sections(self, engine):
        """Test clearing all custom sections."""
        engine.set_custom_section("Section 1", "Content 1")
        engine.set_custom_section("Section 2", "Content 2")
        
        engine.clear_custom_sections()
        
        assert len(engine.template_config.custom_sections) == 0
    
    def test_load_custom_template_file_not_found(self, engine):
        """Test loading custom template with non-existent file."""
        from necrocode.review_pr_service.exceptions import PRServiceError
        
        with pytest.raises(PRServiceError, match="not found"):
            engine.load_custom_template("/nonexistent/template.md")
    
    def test_validate_template_file_not_found(self, engine):
        """Test validating non-existent template."""
        errors = engine.validate_template("/nonexistent/template.md")
        
        assert len(errors) > 0
        assert "not found" in errors[0]
    
    def test_generate_comment_simple(self, engine):
        """Test generating simple comment."""
        with patch.object(engine, 'jinja_env') as mock_env:
            mock_template = MagicMock()
            mock_template.render.return_value = "Test comment"
            mock_env.from_string.return_value = mock_template
            
            comment = engine.generate_comment("Test message")
            
            assert comment == "Test comment"
            mock_template.render.assert_called_once()
    
    def test_generate_comment_with_details(self, engine):
        """Test generating comment with details."""
        with patch.object(engine, 'jinja_env') as mock_env:
            mock_template = MagicMock()
            mock_template.render.return_value = "Test comment with details"
            mock_env.from_string.return_value = mock_template
            
            details = {"Error": "Test error", "File": "test.py"}
            comment = engine.generate_comment("Test message", details=details)
            
            assert comment == "Test comment with details"
            call_args = mock_template.render.call_args
            assert call_args[1]["details"] == details
    
    def test_generate_comment_fallback_on_error(self, engine):
        """Test comment generation fallback on error."""
        with patch.object(engine, 'jinja_env') as mock_env:
            mock_env.from_string.side_effect = Exception("Template error")
            
            comment = engine.generate_comment("Test message")
            
            # Should fallback to simple message
            assert comment == "Test message"


class TestPRTemplateEngineIntegration:
    """Integration tests for PRTemplateEngine."""
    
    def test_template_file_creation(self):
        """Test creating and using a custom template file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "test-template.md"
            template_content = "# {{title}}\n{{description}}"
            
            with open(template_path, "w") as f:
                f.write(template_content)
            
            assert template_path.exists()
            assert template_path.read_text() == template_content
    
    def test_default_template_structure(self):
        """Test default template has required sections."""
        from necrocode.review_pr_service.pr_template_engine import PRTemplateEngine
        
        template = PRTemplateEngine.DEFAULT_TEMPLATE
        
        assert "{{task_id}}" in template
        assert "{{title}}" in template
        assert "{{description}}" in template
        assert "acceptance_criteria" in template
        assert "test_results" in template
        assert "artifact_links" in template
        assert "NecroCode" in template


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Tests for PlaybookEngine.

Tests Playbook loading, execution, conditional logic, and error handling.
"""

import tempfile
from pathlib import Path

import pytest

from necrocode.agent_runner import PlaybookEngine, Playbook, PlaybookStep
from necrocode.agent_runner.exceptions import PlaybookExecutionError


class TestPlaybookEngine:
    """Test PlaybookEngine functionality."""
    
    def test_init(self):
        """Test PlaybookEngine initialization."""
        engine = PlaybookEngine()
        assert engine is not None
    
    def test_get_default_playbook(self):
        """Test getting default Playbook."""
        engine = PlaybookEngine()
        playbook = engine.get_default_playbook()
        
        assert playbook is not None
        assert playbook.name == "Default Task Playbook"
        assert len(playbook.steps) > 0
        assert playbook.metadata["source"] == "default"
    
    def test_load_playbook_success(self):
        """Test loading a valid Playbook from YAML."""
        playbook_yaml = """
name: Test Playbook
steps:
  - name: Step 1
    command: echo "test"
  - name: Step 2
    command: ls
    condition: test_enabled == true
    timeout_seconds: 60
    retry_count: 2
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(playbook_yaml)
            playbook_path = Path(f.name)
        
        try:
            engine = PlaybookEngine()
            playbook = engine.load_playbook(playbook_path)
            
            assert playbook.name == "Test Playbook"
            assert len(playbook.steps) == 2
            
            # Check first step
            step1 = playbook.steps[0]
            assert step1.name == "Step 1"
            assert step1.command == 'echo "test"'
            assert step1.condition is None
            
            # Check second step
            step2 = playbook.steps[1]
            assert step2.name == "Step 2"
            assert step2.command == "ls"
            assert step2.condition == "test_enabled == true"
            assert step2.timeout_seconds == 60
            assert step2.retry_count == 2
            
        finally:
            playbook_path.unlink()
    
    def test_load_playbook_file_not_found(self):
        """Test loading Playbook from non-existent file."""
        engine = PlaybookEngine()
        
        with pytest.raises(PlaybookExecutionError, match="not found"):
            engine.load_playbook(Path("/nonexistent/playbook.yaml"))
    
    def test_load_playbook_invalid_yaml(self):
        """Test loading Playbook with invalid YAML."""
        playbook_yaml = """
name: Test
steps: [
  invalid yaml
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(playbook_yaml)
            playbook_path = Path(f.name)
        
        try:
            engine = PlaybookEngine()
            
            with pytest.raises(PlaybookExecutionError, match="parse YAML"):
                engine.load_playbook(playbook_path)
        
        finally:
            playbook_path.unlink()
    
    def test_load_playbook_missing_name(self):
        """Test loading Playbook without name field."""
        playbook_yaml = """
steps:
  - name: Step 1
    command: echo "test"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(playbook_yaml)
            playbook_path = Path(f.name)
        
        try:
            engine = PlaybookEngine()
            
            with pytest.raises(PlaybookExecutionError, match="name"):
                engine.load_playbook(playbook_path)
        
        finally:
            playbook_path.unlink()
    
    def test_load_playbook_or_default_with_none(self):
        """Test load_playbook_or_default with None path."""
        engine = PlaybookEngine()
        playbook = engine.load_playbook_or_default(None)
        
        assert playbook.name == "Default Task Playbook"
        assert playbook.metadata["source"] == "default"
    
    def test_load_playbook_or_default_with_nonexistent(self):
        """Test load_playbook_or_default with non-existent file."""
        engine = PlaybookEngine()
        playbook = engine.load_playbook_or_default(Path("/nonexistent/playbook.yaml"))
        
        assert playbook.name == "Default Task Playbook"
        assert playbook.metadata["source"] == "default"
    
    def test_load_playbook_or_default_with_valid_file(self):
        """Test load_playbook_or_default with valid file."""
        playbook_yaml = """
name: Custom Playbook
steps:
  - name: Step 1
    command: echo "custom"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(playbook_yaml)
            playbook_path = Path(f.name)
        
        try:
            engine = PlaybookEngine()
            playbook = engine.load_playbook_or_default(playbook_path)
            
            assert playbook.name == "Custom Playbook"
            assert playbook.metadata["source"] == "file"
        
        finally:
            playbook_path.unlink()
    
    def test_execute_playbook_simple(self):
        """Test executing a simple Playbook."""
        engine = PlaybookEngine()
        
        playbook = Playbook(
            name="Test Playbook",
            steps=[
                PlaybookStep(
                    name="Echo test",
                    command='echo "Hello World"',
                    timeout_seconds=10
                )
            ]
        )
        
        context = {}
        cwd = Path.cwd()
        
        result = engine.execute_playbook(playbook, context, cwd)
        
        assert result.success is True
        assert len(result.step_results) == 1
        assert result.step_results[0].success is True
        assert "Hello World" in result.step_results[0].stdout
    
    def test_execute_playbook_with_failure(self):
        """Test executing Playbook with failing step."""
        engine = PlaybookEngine()
        
        playbook = Playbook(
            name="Test Playbook",
            steps=[
                PlaybookStep(
                    name="Failing command",
                    command="exit 1",
                    timeout_seconds=10,
                    fail_fast=True
                )
            ]
        )
        
        context = {}
        cwd = Path.cwd()
        
        result = engine.execute_playbook(playbook, context, cwd)
        
        assert result.success is False
        assert len(result.step_results) == 1
        assert result.step_results[0].success is False
        assert result.step_results[0].exit_code == 1
    
    def test_execute_playbook_with_skip(self):
        """Test executing Playbook with skipped step."""
        engine = PlaybookEngine()
        
        playbook = Playbook(
            name="Test Playbook",
            steps=[
                PlaybookStep(
                    name="Always runs",
                    command='echo "runs"',
                    timeout_seconds=10
                ),
                PlaybookStep(
                    name="Skipped step",
                    command='echo "skipped"',
                    condition="skip_this == true",
                    timeout_seconds=10
                )
            ]
        )
        
        context = {"skip_this": False}
        cwd = Path.cwd()
        
        result = engine.execute_playbook(playbook, context, cwd)
        
        assert result.success is True
        assert len(result.step_results) == 2
        assert result.step_results[0].success is True
        assert result.step_results[0].skipped is False
        assert result.step_results[1].skipped is True
    
    def test_should_execute_step_no_condition(self):
        """Test step execution with no condition."""
        engine = PlaybookEngine()
        step = PlaybookStep(name="Test", command="echo test")
        
        assert engine._should_execute_step(step, {}) is True
    
    def test_should_execute_step_boolean_true(self):
        """Test step execution with boolean true condition."""
        engine = PlaybookEngine()
        step = PlaybookStep(name="Test", command="echo test", condition="true")
        
        assert engine._should_execute_step(step, {}) is True
    
    def test_should_execute_step_boolean_false(self):
        """Test step execution with boolean false condition."""
        engine = PlaybookEngine()
        step = PlaybookStep(name="Test", command="echo test", condition="false")
        
        assert engine._should_execute_step(step, {}) is False
    
    def test_should_execute_step_equality(self):
        """Test step execution with equality condition."""
        engine = PlaybookEngine()
        step = PlaybookStep(name="Test", command="echo test", condition="env == production")
        
        assert engine._should_execute_step(step, {"env": "production"}) is True
        assert engine._should_execute_step(step, {"env": "development"}) is False
    
    def test_should_execute_step_inequality(self):
        """Test step execution with inequality condition."""
        engine = PlaybookEngine()
        step = PlaybookStep(name="Test", command="echo test", condition="count > 5")
        
        assert engine._should_execute_step(step, {"count": 10}) is True
        assert engine._should_execute_step(step, {"count": 3}) is False
    
    def test_substitute_variables(self):
        """Test variable substitution in text."""
        engine = PlaybookEngine()
        
        text = "Hello ${name}, you have ${count} messages"
        context = {"name": "Alice", "count": 5}
        
        result = engine._substitute_variables(text, context)
        
        assert result == "Hello Alice, you have 5 messages"
    
    def test_substitute_variables_missing(self):
        """Test variable substitution with missing variable."""
        engine = PlaybookEngine()
        
        text = "Hello ${name}, you have ${missing} messages"
        context = {"name": "Alice"}
        
        result = engine._substitute_variables(text, context)
        
        # Missing variable should be left as-is
        assert result == "Hello Alice, you have ${missing} messages"
    
    def test_evaluate_condition_comparison_operators(self):
        """Test condition evaluation with various operators."""
        engine = PlaybookEngine()
        context = {"x": 10, "y": 5, "name": "test"}
        
        # Equality
        assert engine._evaluate_condition("x == 10", context) is True
        assert engine._evaluate_condition("x == 5", context) is False
        
        # Inequality
        assert engine._evaluate_condition("x != 5", context) is True
        assert engine._evaluate_condition("x != 10", context) is False
        
        # Greater than
        assert engine._evaluate_condition("x > 5", context) is True
        assert engine._evaluate_condition("y > 10", context) is False
        
        # Less than
        assert engine._evaluate_condition("y < 10", context) is True
        assert engine._evaluate_condition("x < 5", context) is False
        
        # Greater than or equal
        assert engine._evaluate_condition("x >= 10", context) is True
        assert engine._evaluate_condition("x >= 11", context) is False
        
        # Less than or equal
        assert engine._evaluate_condition("y <= 5", context) is True
        assert engine._evaluate_condition("y <= 4", context) is False
    
    def test_resolve_value_types(self):
        """Test resolving different value types."""
        engine = PlaybookEngine()
        context = {"var": "value", "num": 42}
        
        # String literal
        assert engine._resolve_value('"hello"', context) == "hello"
        assert engine._resolve_value("'world'", context) == "world"
        
        # Boolean literal
        assert engine._resolve_value("true", context) is True
        assert engine._resolve_value("false", context) is False
        
        # Numeric literal
        assert engine._resolve_value("42", context) == 42
        assert engine._resolve_value("3.14", context) == 3.14
        
        # Variable lookup
        assert engine._resolve_value("var", context) == "value"
        assert engine._resolve_value("num", context) == 42
    
    def test_execute_step_with_retry(self):
        """Test step execution with retry on failure."""
        engine = PlaybookEngine()
        
        # This will fail but should retry
        step = PlaybookStep(
            name="Retry test",
            command="exit 1",
            timeout_seconds=10,
            retry_count=2
        )
        
        context = {}
        cwd = Path.cwd()
        
        result = engine._execute_step(step, context, cwd)
        
        assert result.success is False
        assert result.retry_count == 2  # Should have retried 2 times


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

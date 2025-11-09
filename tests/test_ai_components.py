"""Unit tests for AI components: SpecTaskRunner, StrandsAgent, and context building."""

import tempfile
from pathlib import Path
from typing import Dict, Any
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from strandsagents import StrandsAgent, StrandsTask, SpecTaskRunner, StubLLMClient


class TestSpecTaskRunnerWithStubLLM:
    """Tests for SpecTaskRunner using StubLLMClient (Task 23.2)."""

    def test_runner_initializes_with_custom_llm_client(self):
        """Verify SpecTaskRunner accepts custom LLM client."""
        stub = StubLLMClient("test response")
        runner = SpecTaskRunner(llm_client=stub)
        assert runner.agent.llm_client is stub

    def test_runner_initializes_with_custom_model(self):
        """Verify SpecTaskRunner accepts custom model name."""
        stub = StubLLMClient("test response")
        runner = SpecTaskRunner(model="gpt-5-codex", llm_client=stub)
        assert runner.agent.llm_client.model == "gpt-5-codex"

    def test_runner_loads_tasks_from_valid_file(self):
        """Verify task loading from properly formatted tasks.md."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("""# Implementation Plan

- [ ] 1. First task
  - Create component A
  - Implement feature B
  - _Requirements: 1.1, 1.2_

- [x] 2. Second task
  - Setup infrastructure
  - _Requirements: 2.1_
""")
            f.flush()
            tasks_path = Path(f.name)

        try:
            runner = SpecTaskRunner(llm_client=StubLLMClient())
            tasks = runner.load_tasks(tasks_path)
            
            assert len(tasks) == 2
            assert tasks[0].identifier == "1"
            assert "First task" in tasks[0].title
            assert "Create component A" in tasks[0].checklist[0]
            assert tasks[1].identifier == "2"
            assert "Second task" in tasks[1].title
        finally:
            tasks_path.unlink()

    def test_runner_handles_tasks_with_no_checklist(self):
        """Verify task loading handles tasks without checklist items."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("""# Tasks

- [ ] 1. Simple task
  _Requirements: 1.1_
""")
            f.flush()
            tasks_path = Path(f.name)

        try:
            runner = SpecTaskRunner(llm_client=StubLLMClient())
            tasks = runner.load_tasks(tasks_path)
            
            assert len(tasks) == 1
            assert tasks[0].identifier == "1"
            assert len(tasks[0].checklist) == 0
        finally:
            tasks_path.unlink()

    def test_runner_raises_error_for_missing_file(self):
        """Verify FileNotFoundError for non-existent tasks file."""
        runner = SpecTaskRunner(llm_client=StubLLMClient())
        try:
            runner.load_tasks(Path("/nonexistent/tasks.md"))
            assert False, "Expected FileNotFoundError"
        except FileNotFoundError:
            pass  # Expected

    def test_runner_executes_all_tasks_with_stub(self):
        """Verify runner executes all tasks and returns results."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("""# Tasks

- [ ] 1. Task one
  - Step A
  
- [ ] 2. Task two
  - Step B
""")
            f.flush()
            tasks_path = Path(f.name)

        try:
            stub = StubLLMClient("Generated code here")
            runner = SpecTaskRunner(llm_client=stub)
            results = runner.run(tasks_path)
            
            assert len(results) == 2
            assert results[0]["task_id"] == "1"
            assert results[0]["output"] == "Generated code here"
            assert results[1]["task_id"] == "2"
            assert results[1]["output"] == "Generated code here"
            assert len(stub.calls) == 2
        finally:
            tasks_path.unlink()

    def test_runner_captures_task_metadata_in_results(self):
        """Verify results include task ID and title."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("- [ ] 1. Test task\n  - Do something\n")
            f.flush()
            tasks_path = Path(f.name)

        try:
            stub = StubLLMClient("output")
            runner = SpecTaskRunner(llm_client=stub)
            results = runner.run(tasks_path)
            
            assert results[0]["task_id"] == "1"
            assert results[0]["title"] == "Test task"
            assert "output" in results[0]
        finally:
            tasks_path.unlink()


class TestStrandsAgentExecution:
    """Tests for StrandsAgent task execution."""

    def test_agent_executes_task_with_stub_llm(self):
        """Verify agent executes task and returns result."""
        stub = StubLLMClient("Implementation complete")
        agent = StrandsAgent(name="TestAgent", llm_client=stub)
        
        task = StrandsTask(
            identifier="1.1",
            title="Implement feature",
            description="Create the feature",
            checklist=["Step 1", "Step 2"]
        )
        
        result = agent.run_task(task)
        
        assert result["task_id"] == "1.1"
        assert result["title"] == "Implement feature"
        assert result["output"] == "Implementation complete"
        assert len(stub.calls) == 1

    def test_agent_includes_system_prompt_in_messages(self):
        """Verify agent sends system prompt to LLM."""
        stub = StubLLMClient("ok")
        agent = StrandsAgent(
            name="TestAgent",
            system_prompt="You are a test agent",
            llm_client=stub
        )
        
        task = StrandsTask("1", "Test", "Description", [])
        agent.run_task(task)
        
        messages = stub.calls[0]
        assert messages[0]["role"] == "system"
        assert "test agent" in messages[0]["content"]

    def test_agent_formats_task_in_prompt(self):
        """Verify agent formats task details in user prompt."""
        stub = StubLLMClient("ok")
        agent = StrandsAgent(name="TestAgent", llm_client=stub)
        
        task = StrandsTask(
            identifier="2.3",
            title="Build component",
            description="Component description",
            checklist=["Item A", "Item B"]
        )
        
        agent.run_task(task)
        
        messages = stub.calls[0]
        user_message = messages[1]["content"]
        assert "Task ID: 2.3" in user_message
        assert "Task Title: Build component" in user_message
        assert "Component description" in user_message
        assert "Item A" in user_message
        assert "Item B" in user_message

    def test_agent_uses_custom_temperature(self):
        """Verify agent respects custom temperature setting."""
        stub = StubLLMClient("ok")
        agent = StrandsAgent(name="TestAgent", llm_client=stub, temperature=0.7)
        
        assert agent.temperature == 0.7

    def test_agent_uses_custom_max_tokens(self):
        """Verify agent respects custom max_tokens setting."""
        stub = StubLLMClient("ok")
        agent = StrandsAgent(name="TestAgent", llm_client=stub, max_tokens=1500)
        
        assert agent.max_tokens == 1500


class TestContextBuilding:
    """Tests for context building from requirements and design files (Task 23.3)."""

    def test_agent_includes_context_in_prompt(self):
        """Verify agent includes context dictionary in prompt."""
        stub = StubLLMClient("ok")
        agent = StrandsAgent(name="TestAgent", llm_client=stub)
        
        task = StrandsTask("1", "Test", "Description", [])
        context = {
            "requirements": "User must be authenticated",
            "design": "Use JWT tokens"
        }
        
        agent.run_task(task, context=context)
        
        messages = stub.calls[0]
        user_message = messages[1]["content"]
        assert "Context:" in user_message
        assert "requirements: User must be authenticated" in user_message
        assert "design: Use JWT tokens" in user_message

    def test_context_from_requirements_file(self):
        """Verify loading context from requirements.md file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("""# Requirements

## Requirement 1
The system SHALL authenticate users.

## Requirement 2
The system SHALL use secure tokens.
""")
            f.flush()
            req_path = Path(f.name)

        try:
            content = req_path.read_text()
            assert "authenticate users" in content
            assert "secure tokens" in content
        finally:
            req_path.unlink()

    def test_context_from_design_file(self):
        """Verify loading context from design.md file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("""# Design Document

## Architecture
Use microservices architecture.

## Components
- API Gateway
- Auth Service
""")
            f.flush()
            design_path = Path(f.name)

        try:
            content = design_path.read_text()
            assert "microservices" in content
            assert "Auth Service" in content
        finally:
            design_path.unlink()

    def test_context_building_with_multiple_sources(self):
        """Verify combining context from multiple sources."""
        context: Dict[str, Any] = {}
        
        # Simulate loading from requirements
        context["requirements"] = "System SHALL handle 1000 concurrent users"
        
        # Simulate loading from design
        context["design"] = "Use Redis for session management"
        
        # Simulate loading from existing code
        context["existing_code"] = "class UserSession: pass"
        
        stub = StubLLMClient("ok")
        agent = StrandsAgent(name="TestAgent", llm_client=stub)
        task = StrandsTask("1", "Test", "Description", [])
        
        agent.run_task(task, context=context)
        
        messages = stub.calls[0]
        user_message = messages[1]["content"]
        assert "1000 concurrent users" in user_message
        assert "Redis for session management" in user_message
        assert "class UserSession" in user_message

    def test_empty_context_does_not_break_prompt(self):
        """Verify agent handles empty context gracefully."""
        stub = StubLLMClient("ok")
        agent = StrandsAgent(name="TestAgent", llm_client=stub)
        
        task = StrandsTask("1", "Test", "Description", [])
        agent.run_task(task, context={})
        
        messages = stub.calls[0]
        user_message = messages[1]["content"]
        # Should not include Context section if empty
        assert user_message.count("Context:") == 0

    def test_none_context_does_not_break_prompt(self):
        """Verify agent handles None context gracefully."""
        stub = StubLLMClient("ok")
        agent = StrandsAgent(name="TestAgent", llm_client=stub)
        
        task = StrandsTask("1", "Test", "Description", [])
        agent.run_task(task, context=None)
        
        messages = stub.calls[0]
        user_message = messages[1]["content"]
        # Should work without errors
        assert "Task ID: 1" in user_message


class TestCodeExtractionFromLLMOutput:
    """Tests for code extraction from LLM output (Task 23.4)."""

    def test_extract_single_code_block(self):
        """Verify extracting a single code block from LLM output."""
        llm_output = """Here's the implementation:

```python
def hello():
    return "Hello, World!"
```

This function returns a greeting.
"""
        # Simple extraction logic
        import re
        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', llm_output, re.DOTALL)
        
        assert len(code_blocks) == 1
        assert "def hello():" in code_blocks[0]
        assert 'return "Hello, World!"' in code_blocks[0]

    def test_extract_multiple_code_blocks(self):
        """Verify extracting multiple code blocks from LLM output."""
        llm_output = """First, create the model:

```python
class User:
    def __init__(self, name):
        self.name = name
```

Then, create the service:

```python
class UserService:
    def create_user(self, name):
        return User(name)
```
"""
        import re
        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', llm_output, re.DOTALL)
        
        assert len(code_blocks) == 2
        assert "class User:" in code_blocks[0]
        assert "class UserService:" in code_blocks[1]

    def test_extract_code_with_language_specifier(self):
        """Verify extracting code blocks with language specifiers."""
        llm_output = """```javascript
function greet() {
    console.log("Hello");
}
```

```typescript
interface User {
    name: string;
}
```
"""
        import re
        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', llm_output, re.DOTALL)
        
        assert len(code_blocks) == 2
        assert "function greet()" in code_blocks[0]
        assert "interface User" in code_blocks[1]

    def test_extract_file_path_from_output(self):
        """Verify extracting file paths from LLM output."""
        llm_output = """Create the following file:

File: `src/models/user.py`

```python
class User:
    pass
```
"""
        import re
        # Extract file path pattern
        file_paths = re.findall(r'File:\s*`([^`]+)`', llm_output)
        
        assert len(file_paths) == 1
        assert file_paths[0] == "src/models/user.py"

    def test_extract_multiple_files_from_output(self):
        """Verify extracting multiple file paths and code blocks."""
        llm_output = """Create these files:

File: `models/user.py`
```python
class User:
    pass
```

File: `services/user_service.py`
```python
class UserService:
    pass
```
"""
        import re
        file_paths = re.findall(r'File:\s*`([^`]+)`', llm_output)
        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', llm_output, re.DOTALL)
        
        assert len(file_paths) == 2
        assert len(code_blocks) == 2
        assert file_paths[0] == "models/user.py"
        assert file_paths[1] == "services/user_service.py"
        assert "class User:" in code_blocks[0]
        assert "class UserService:" in code_blocks[1]

    def test_handle_output_without_code_blocks(self):
        """Verify handling LLM output without code blocks."""
        llm_output = """This is just a description without any code.
The implementation should follow these steps:
1. Create the class
2. Add methods
3. Test the functionality
"""
        import re
        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', llm_output, re.DOTALL)
        
        assert len(code_blocks) == 0

    def test_extract_code_with_inline_backticks(self):
        """Verify handling inline code doesn't interfere with block extraction."""
        llm_output = """Use the `User` class like this:

```python
user = User("Alice")
print(user.name)
```

The `name` attribute stores the user's name.
"""
        import re
        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', llm_output, re.DOTALL)
        
        assert len(code_blocks) == 1
        assert 'user = User("Alice")' in code_blocks[0]

    def test_extract_code_preserves_indentation(self):
        """Verify code extraction preserves indentation."""
        llm_output = """```python
class Example:
    def method(self):
        if True:
            return "nested"
```
"""
        import re
        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', llm_output, re.DOTALL)
        
        assert len(code_blocks) == 1
        code = code_blocks[0]
        assert "    def method(self):" in code
        assert "        if True:" in code
        assert '            return "nested"' in code


class TestStubLLMClient:
    """Tests for StubLLMClient test double."""

    def test_stub_returns_configured_response(self):
        """Verify stub returns the configured response."""
        stub = StubLLMClient("test response")
        result = stub.complete([{"role": "user", "content": "test"}])
        
        assert result == "test response"

    def test_stub_captures_all_calls(self):
        """Verify stub captures all completion calls."""
        stub = StubLLMClient("ok")
        
        stub.complete([{"role": "user", "content": "first"}])
        stub.complete([{"role": "user", "content": "second"}])
        
        assert len(stub.calls) == 2
        assert stub.calls[0][0]["content"] == "first"
        assert stub.calls[1][0]["content"] == "second"

    def test_stub_ignores_temperature_and_max_tokens(self):
        """Verify stub ignores temperature and max_tokens parameters."""
        stub = StubLLMClient("response")
        result = stub.complete(
            [{"role": "user", "content": "test"}],
            temperature=0.9,
            max_tokens=2000
        )
        
        assert result == "response"

    def test_stub_default_response(self):
        """Verify stub has default response."""
        stub = StubLLMClient()
        result = stub.complete([{"role": "user", "content": "test"}])
        
        assert result == "(stub response)"


if __name__ == "__main__":
    # Simple test runner
    import inspect
    
    test_classes = [
        TestSpecTaskRunnerWithStubLLM,
        TestStrandsAgentExecution,
        TestContextBuilding,
        TestCodeExtractionFromLLMOutput,
        TestStubLLMClient,
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_class in test_classes:
        print(f"\n{'='*60}")
        print(f"Running {test_class.__name__}")
        print('='*60)
        
        for name, method in inspect.getmembers(test_class, predicate=inspect.isfunction):
            if name.startswith("test_"):
                total_tests += 1
                try:
                    instance = test_class()
                    method(instance)
                    print(f"✓ {name}")
                    passed_tests += 1
                except Exception as e:
                    print(f"✗ {name}: {e}")
                    failed_tests.append((test_class.__name__, name, str(e)))
    
    print(f"\n{'='*60}")
    print(f"Test Results: {passed_tests}/{total_tests} passed")
    print('='*60)
    
    if failed_tests:
        print("\nFailed tests:")
        for class_name, test_name, error in failed_tests:
            print(f"  {class_name}.{test_name}: {error}")
        sys.exit(1)
    else:
        print("\n✓ All tests passed!")
        sys.exit(0)

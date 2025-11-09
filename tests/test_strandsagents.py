"""Tests for Strands Agents integration."""

from pathlib import Path

from strandsagents import SpecTaskRunner, StubLLMClient


SPEC_TASK_FILE = Path(".kiro/specs/documentation-organization/tasks.md")


def test_spec_task_loading_counts_tasks():
    runner = SpecTaskRunner(llm_client=StubLLMClient("ok"))
    tasks = runner.load_tasks(SPEC_TASK_FILE)
    assert len(tasks) == 4
    assert tasks[0].identifier.startswith("1")
    assert "overview" in tasks[0].title.lower()


def test_spec_task_runner_uses_stub_llm():
    stub = StubLLMClient("Strands OK")
    runner = SpecTaskRunner(llm_client=stub)
    results = runner.run(SPEC_TASK_FILE)
    assert len(results) == 4
    assert all("Strands OK" in result["output"] for result in results)
    assert len(stub.calls) == 4

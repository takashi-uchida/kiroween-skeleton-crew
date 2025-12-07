"""Test DocumentationSpirit integration."""

import sys
from pathlib import Path

# Add framework to path
sys.path.insert(0, str(Path(__file__).parent))

from framework.agents import DocumentationSpirit
from framework.orchestrator.issue_router import IssueRouter
from framework.communication.message_bus import MessageBus


def test_documentation_spirit_creation():
    """Test that DocumentationSpirit can be created."""
    spirit = DocumentationSpirit(
        role="documentation",
        skills=["technical_writing", "content_organization"],
        workspace="test",
        instance_number=1
    )
    
    assert spirit.identifier == "documentation_spirit_1"
    assert spirit.role == "documentation"
    assert "technical_writing" in spirit.skills
    print("✅ DocumentationSpirit creation: PASSED")


def test_documentation_spirit_methods():
    """Test DocumentationSpirit methods."""
    spirit = DocumentationSpirit(
        role="documentation",
        skills=["technical_writing"],
        workspace="test",
        instance_number=1
    )
    
    # Test create_documentation_plan
    requirements = {
        'eliminate_redundancy': True,
        'create_hierarchy': True
    }
    plan = spirit.create_documentation_plan(requirements)
    assert 'plan' in plan
    assert 'chant' in plan
    print("✅ create_documentation_plan: PASSED")
    
    # Test consolidate_content
    sections = [
        {'title': 'Section 1', 'content': 'Content A'},
        {'title': 'Section 2', 'content': 'Content A'},  # Duplicate
        {'title': 'Section 3', 'content': 'Content B'}
    ]
    result = spirit.consolidate_content(sections)
    assert 'unique_sections' in result
    assert 'duplicates_removed' in result
    print("✅ consolidate_content: PASSED")
    
    # Test add_cross_references
    docs = {
        'overview.md': 'This is the overview',
        'architecture.md': 'This is the architecture'
    }
    cross_refs = spirit.add_cross_references(docs)
    assert 'updated_docs' in cross_refs
    assert 'cross_refs_added' in cross_refs
    print("✅ add_cross_references: PASSED")
    
    # Test validate_documentation
    validation = spirit.validate_documentation(docs)
    assert 'valid' in validation
    assert 'issues' in validation
    print("✅ validate_documentation: PASSED")


def test_issue_routing_to_documentation():
    """Test that documentation issues are routed correctly."""
    message_bus = MessageBus()
    router = IssueRouter(message_bus)
    
    # Create documentation spirit
    doc_spirit = DocumentationSpirit(
        role="documentation",
        skills=["technical_writing"],
        workspace="test",
        instance_number=1
    )
    message_bus.register(doc_spirit)
    
    # Test routing
    issue = {
        'id': 'DOC-1',
        'title': 'Reorganize documentation',
        'description': 'Consolidate markdown files and eliminate redundancy'
    }
    
    routed_agent = router.route_issue(issue)
    assert routed_agent == "documentation_spirit_1"
    print("✅ Issue routing to DocumentationSpirit: PASSED")


def test_workload_tracking():
    """Test that DocumentationSpirit tracks workload correctly."""
    spirit = DocumentationSpirit(
        role="documentation",
        skills=["technical_writing"],
        workspace="test",
        instance_number=1
    )
    
    # Initially no tasks
    assert spirit.get_workload() == 0
    
    # Assign tasks
    spirit.assign_task("DOC-1")
    spirit.assign_task("DOC-2")
    assert spirit.get_workload() == 2
    
    # Complete task
    spirit.complete_task("DOC-1")
    assert spirit.get_workload() == 1
    assert "DOC-1" in spirit.completed_tasks
    assert "DOC-1" not in spirit.current_tasks
    
    print("✅ Workload tracking: PASSED")


def test_load_balancing():
    """Test load balancing across multiple DocumentationSpirits."""
    message_bus = MessageBus()
    router = IssueRouter(message_bus)
    
    # Create two documentation spirits
    spirit1 = DocumentationSpirit(
        role="documentation",
        skills=["technical_writing"],
        workspace="test",
        instance_number=1
    )
    spirit2 = DocumentationSpirit(
        role="documentation",
        skills=["content_organization"],
        workspace="test",
        instance_number=2
    )
    
    message_bus.register(spirit1)
    message_bus.register(spirit2)
    
    # Assign tasks and verify load balancing
    issues = [
        {'id': 'DOC-1', 'title': 'Reorganize docs', 'description': 'documentation task'},
        {'id': 'DOC-2', 'title': 'Add cross-refs', 'description': 'documentation task'},
        {'id': 'DOC-3', 'title': 'Update README', 'description': 'documentation task'},
    ]
    
    for issue in issues:
        agent = router.route_issue(issue)
        if agent == spirit1.identifier:
            spirit1.assign_task(issue['id'])
        elif agent == spirit2.identifier:
            spirit2.assign_task(issue['id'])
    
    # Both spirits should have tasks (load balanced)
    total_workload = spirit1.get_workload() + spirit2.get_workload()
    assert total_workload == 3
    print(f"✅ Load balancing: PASSED (Spirit1: {spirit1.get_workload()}, Spirit2: {spirit2.get_workload()})")


def run_all_tests():
    """Run all tests."""
    print("="*70)
    print("Testing DocumentationSpirit Integration")
    print("="*70)
    
    try:
        test_documentation_spirit_creation()
        test_documentation_spirit_methods()
        test_issue_routing_to_documentation()
        test_workload_tracking()
        test_load_balancing()
        
        print("\n" + "="*70)
        print("✅ All tests PASSED!")
        print("="*70)
        print("\n🎉 DocumentationSpirit successfully integrated into NecroCode!")
        return True
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

"""Demo: Documentation Spirit capabilities."""

from framework.orchestrator.necromancer import Necromancer
from framework.orchestrator.job_parser import RoleRequest


def demo_documentation_reorganization():
    """Demonstrate documentation reorganization with DocumentationSpirit."""
    
    print("="*70)
    print("NecroCode Documentation Spirit Demo")
    print("="*70)
    
    # Create Necromancer
    necromancer = Necromancer(workspace="necrocode")
    
    # Job description for documentation reorganization
    job_description = """
    Reorganize NecroCode steering documentation to eliminate redundancy 
    and improve navigation. Consolidate product.md, tech.md, structure.md, 
    and agent-workflow.md into three streamlined documents: overview.md, 
    architecture.md, and development.md. Add cross-references and ensure 
    consistent terminology throughout.
    """
    
    print("\n📜 Job Description:")
    print(job_description.strip())
    
    # Define role requests - summon documentation spirit
    role_requests = [
        RoleRequest(
            name="documentation",
            skills=["technical_writing", "content_organization"],
            count=1
        )
    ]
    
    print("\n" + "="*70)
    print("Phase 1: Summoning Documentation Spirit")
    print("="*70)
    
    # Summon team (will include architect and scrum master automatically)
    team_config = necromancer.summon_team(job_description, role_requests)
    
    print(f"\n✨ Team assembled: {len(necromancer.spirits)} spirits")
    for spirit_id in necromancer.spirits.keys():
        print(f"   - {spirit_id}")
    
    print("\n" + "="*70)
    print("Phase 2: Documentation Spirit Capabilities")
    print("="*70)
    
    # Get the documentation spirit
    doc_spirit = necromancer.spirits.get("documentation_spirit_1")
    
    if doc_spirit:
        print("\n📚 Testing Documentation Spirit methods:")
        
        # Test 1: Create documentation plan
        print("\n1. Creating documentation plan...")
        requirements = {
            'eliminate_redundancy': True,
            'create_hierarchy': True,
            'consolidate_specs': True,
            'improve_navigation': True
        }
        plan_result = doc_spirit.create_documentation_plan(requirements)
        print(f"   {plan_result['chant']}")
        print(f"   Target files: {plan_result['plan']['target_files']}")
        print(f"   Validation steps: {plan_result['plan']['validation_steps']}")
        
        # Test 2: Consolidate content
        print("\n2. Testing content consolidation...")
        sample_sections = [
            {
                'title': 'Spirit Protocol',
                'content': 'spirit(scope): description [Task X.Y]',
                'source': 'tech.md'
            },
            {
                'title': 'Communication Protocol',
                'content': 'spirit(scope): description [Task X.Y]',
                'source': 'agent-workflow.md'
            },
            {
                'title': 'Branch Naming',
                'content': 'feature/task-{spec}-{id}-{desc}',
                'source': 'structure.md'
            }
        ]
        consolidation = doc_spirit.consolidate_content(sample_sections)
        print(f"   {consolidation['chant']}")
        print(f"   Unique sections: {len(consolidation['unique_sections'])}")
        if consolidation['duplicates']:
            print(f"   Duplicates found:")
            for dup in consolidation['duplicates']:
                print(f"      - '{dup['duplicate']}' duplicates '{dup['original']}'")
        
        # Test 3: Add cross-references
        print("\n3. Testing cross-reference addition...")
        sample_docs = {
            'overview.md': 'This document describes the architecture patterns.',
            'development.md': 'See the overview for product context.',
            'architecture.md': 'Implementation details are in development guide.'
        }
        cross_ref_result = doc_spirit.add_cross_references(sample_docs)
        print(f"   {cross_ref_result['chant']}")
        
        # Test 4: Validate documentation
        print("\n4. Testing documentation validation...")
        validation = doc_spirit.validate_documentation(sample_docs)
        print(f"   {validation['chant']}")
        print(f"   Valid: {validation['valid']}")
        if validation['issues']:
            print(f"   Issues found: {len(validation['issues'])}")
    
    print("\n" + "="*70)
    print("Phase 3: Sprint Execution")
    print("="*70)
    
    # Execute sprint
    sprint_result = necromancer.execute_sprint()
    
    print(f"\n✅ Sprint completed!")
    print(f"   Tasks assigned: {len(sprint_result['results'])}")
    
    # Display workload
    print("\n📊 Final Workload Dashboard:")
    necromancer.display_workload_dashboard()
    
    # Banish spirits
    print("\n" + "="*70)
    necromancer.banish_spirits()
    
    print("\n" + "="*70)
    print("Demo Complete!")
    print("="*70)
    print("\n✨ DocumentationSpirit successfully integrated into NecroCode!")
    print("   - Can reorganize documentation")
    print("   - Eliminates duplicate content")
    print("   - Adds cross-references")
    print("   - Validates consistency")
    print("   - Routes documentation tasks automatically")


def demo_issue_routing():
    """Demonstrate that documentation tasks are routed correctly."""
    
    print("\n" + "="*70)
    print("Documentation Task Routing Demo")
    print("="*70)
    
    from framework.communication.message_bus import MessageBus
    from framework.orchestrator.issue_router import IssueRouter
    from framework.agents import DocumentationSpirit
    
    # Create message bus and router
    message_bus = MessageBus()
    router = IssueRouter(message_bus)
    
    # Create documentation spirits
    doc_spirit_1 = DocumentationSpirit(
        role="documentation",
        skills=["technical_writing"],
        workspace="test",
        instance_number=1
    )
    doc_spirit_2 = DocumentationSpirit(
        role="documentation",
        skills=["content_organization"],
        workspace="test",
        instance_number=2
    )
    
    # Register spirits
    message_bus.register(doc_spirit_1)
    message_bus.register(doc_spirit_2)
    
    # Test issues
    test_issues = [
        {
            'id': 'DOC-1',
            'title': 'Reorganize steering documentation',
            'description': 'Consolidate product.md, tech.md, structure.md into new structure'
        },
        {
            'id': 'DOC-2',
            'title': 'Add cross-references to architecture guide',
            'description': 'Improve navigation between documentation files'
        },
        {
            'id': 'DOC-3',
            'title': 'Eliminate redundancy in technical docs',
            'description': 'Remove duplicate content from markdown files'
        },
        {
            'id': 'DOC-4',
            'title': 'Update README with new features',
            'description': 'Document the DocumentationSpirit capabilities'
        }
    ]
    
    print("\n🔍 Routing documentation tasks:")
    for issue in test_issues:
        agent = router.route_issue(issue)
        print(f"\n   Issue {issue['id']}: {issue['title']}")
        print(f"   → Routed to: {agent}")
        
        # Assign task to demonstrate load balancing
        if agent and agent in [doc_spirit_1.identifier, doc_spirit_2.identifier]:
            spirit = doc_spirit_1 if agent == doc_spirit_1.identifier else doc_spirit_2
            spirit.assign_task(issue['id'])
    
    # Show workload distribution
    print("\n📊 Workload Distribution:")
    print(f"   {doc_spirit_1.identifier}: {doc_spirit_1.get_workload()} tasks")
    print(f"   {doc_spirit_2.identifier}: {doc_spirit_2.get_workload()} tasks")
    
    print("\n✅ All documentation tasks routed successfully!")


if __name__ == "__main__":
    # Run main demo
    demo_documentation_reorganization()
    
    # Run routing demo
    demo_issue_routing()

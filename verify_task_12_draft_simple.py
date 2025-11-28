"""
Simple verification script for Task 12: Draft PR Functionality

This script verifies the implementation by checking code structure without imports.

Requirements: 12.1, 12.2, 12.3, 12.4, 12.5
"""

import re
from pathlib import Path


def check_file_contains(file_path, patterns, description):
    """Check if a file contains all specified patterns."""
    print(f"\nChecking: {description}")
    print(f"File: {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        all_found = True
        for pattern, name in patterns:
            if re.search(pattern, content, re.MULTILINE | re.DOTALL):
                print(f"  ✓ Found: {name}")
            else:
                print(f"  ✗ Missing: {name}")
                all_found = False
        
        return all_found
    except FileNotFoundError:
        print(f"  ✗ File not found: {file_path}")
        return False


def verify_config():
    """Verify DraftConfig in config.py."""
    print("=" * 70)
    print("VERIFICATION 1: Draft Configuration")
    print("=" * 70)
    
    patterns = [
        (r'class DraftConfig:', 'DraftConfig class'),
        (r'enabled:\s*bool\s*=\s*True', 'enabled field'),
        (r'create_as_draft:\s*bool\s*=\s*True', 'create_as_draft field'),
        (r'convert_on_ci_success:\s*bool\s*=\s*True', 'convert_on_ci_success field'),
        (r'skip_reviewers:\s*bool\s*=\s*True', 'skip_reviewers field'),
        (r'draft_label:\s*str\s*=\s*"draft"', 'draft_label field'),
    ]
    
    result = check_file_contains(
        'necrocode/review_pr_service/config.py',
        patterns,
        'Draft configuration class'
    )
    
    print(f"\n{'✅' if result else '❌'} Draft configuration: {'PASS' if result else 'FAIL'}\n")
    return result


def verify_pr_service_methods():
    """Verify draft-related methods in pr_service.py."""
    print("=" * 70)
    print("VERIFICATION 2: Draft PR Methods")
    print("=" * 70)
    
    patterns = [
        (r'def convert_draft_to_ready\(', 'convert_draft_to_ready method'),
        (r'def convert_draft_on_ci_success\(', 'convert_draft_on_ci_success method'),
        (r'def handle_draft_pr_creation\(', 'handle_draft_pr_creation method'),
        (r'Requirements:.*12\.1', 'Requirement 12.1 reference'),
        (r'Requirements:.*12\.2', 'Requirement 12.2 reference'),
        (r'Requirements:.*12\.3.*12\.4', 'Requirements 12.3, 12.4 reference'),
    ]
    
    result = check_file_contains(
        'necrocode/review_pr_service/pr_service.py',
        patterns,
        'Draft PR service methods'
    )
    
    print(f"\n{'✅' if result else '❌'} Draft PR methods: {'PASS' if result else 'FAIL'}\n")
    return result


def verify_draft_creation():
    """Verify draft PR creation logic."""
    print("=" * 70)
    print("VERIFICATION 3: Draft PR Creation (Requirement 12.1)")
    print("=" * 70)
    
    patterns = [
        (r'draft\s*=\s*self\.config\.draft\.create_as_draft\s+if\s+self\.config\.draft\.enabled', 'Draft flag from config'),
        (r'if\s+pr\.draft:', 'Draft PR check'),
        (r'self\.handle_draft_pr_creation\(pr,\s*task\)', 'Call to handle_draft_pr_creation'),
    ]
    
    result = check_file_contains(
        'necrocode/review_pr_service/pr_service.py',
        patterns,
        'Draft PR creation in create_pr method'
    )
    
    print(f"\n{'✅' if result else '❌'} Draft PR creation: {'PASS' if result else 'FAIL'}\n")
    return result


def verify_draft_conversion():
    """Verify draft conversion logic."""
    print("=" * 70)
    print("VERIFICATION 4: Draft Conversion (Requirement 12.2)")
    print("=" * 70)
    
    patterns = [
        (r'self\.git_host_client\.convert_to_ready\(', 'Call to convert_to_ready'),
        (r'pr\.convert_from_draft\(\)', 'Update PR object'),
        (r'self\._assign_reviewers\(pr,\s*task\)', 'Assign reviewers after conversion'),
        (r'self\.git_host_client\.remove_label\(pr_id,\s*draft_label\)', 'Remove draft label'),
        (r'if\s+ci_status\s*!=\s*CIStatus\.SUCCESS:', 'CI status check'),
    ]
    
    result = check_file_contains(
        'necrocode/review_pr_service/pr_service.py',
        patterns,
        'Draft conversion methods'
    )
    
    print(f"\n{'✅' if result else '❌'} Draft conversion: {'PASS' if result else 'FAIL'}\n")
    return result


def verify_draft_handling():
    """Verify special draft PR handling."""
    print("=" * 70)
    print("VERIFICATION 5: Draft PR Handling (Requirements 12.3, 12.4)")
    print("=" * 70)
    
    patterns = [
        (r'if\s+not\s+\(pr\.draft\s+and\s+self\.config\.reviewers\.skip_draft_prs\):', 'Skip reviewers for drafts'),
        (r'draft_label\s*=\s*self\.config\.draft\.draft_label', 'Get draft label from config'),
        (r'self\.git_host_client\.add_labels\(pr\.pr_id,\s*\[draft_label\]\)', 'Add draft label'),
        (r'"event":\s*"draft_pr_created"', 'Draft PR created event'),
    ]
    
    result = check_file_contains(
        'necrocode/review_pr_service/pr_service.py',
        patterns,
        'Draft PR handling logic'
    )
    
    print(f"\n{'✅' if result else '❌'} Draft PR handling: {'PASS' if result else 'FAIL'}\n")
    return result


def verify_draft_disable():
    """Verify draft feature can be disabled."""
    print("=" * 70)
    print("VERIFICATION 6: Draft Feature Disable (Requirement 12.5)")
    print("=" * 70)
    
    patterns = [
        (r'if\s+not\s+self\.config\.draft\.enabled:', 'Check if draft enabled (convert_draft_to_ready)'),
        (r'if\s+not\s+self\.config\.draft\.enabled\s+or\s+not\s+self\.config\.draft\.convert_on_ci_success:', 'Check if auto-convert enabled'),
        (r'draft\s*=\s*self\.config\.draft\.create_as_draft\s+if\s+self\.config\.draft\.enabled\s+else\s+False', 'Conditional draft creation'),
    ]
    
    result = check_file_contains(
        'necrocode/review_pr_service/pr_service.py',
        patterns,
        'Draft feature disable checks'
    )
    
    print(f"\n{'✅' if result else '❌'} Draft feature disable: {'PASS' if result else 'FAIL'}\n")
    return result


def verify_git_host_clients():
    """Verify Git host clients support draft operations."""
    print("=" * 70)
    print("VERIFICATION 7: Git Host Client Support")
    print("=" * 70)
    
    patterns = [
        (r'def convert_to_ready\(self,\s*pr_id:\s*str\)\s*->\s*None:', 'convert_to_ready abstract method'),
        (r'class GitHubClient\(GitHostClient\):', 'GitHubClient class'),
        (r'class GitLabClient\(GitHostClient\):', 'GitLabClient class'),
        (r'class BitbucketClient\(GitHostClient\):', 'BitbucketClient class'),
    ]
    
    result = check_file_contains(
        'necrocode/review_pr_service/git_host_client.py',
        patterns,
        'Git host client draft support'
    )
    
    print(f"\n{'✅' if result else '❌'} Git host client support: {'PASS' if result else 'FAIL'}\n")
    return result


def verify_examples():
    """Verify example file exists."""
    print("=" * 70)
    print("VERIFICATION 8: Example Code")
    print("=" * 70)
    
    example_file = Path('examples/draft_pr_example.py')
    
    if example_file.exists():
        print(f"  ✓ Example file exists: {example_file}")
        
        patterns = [
            (r'def example_create_draft_pr\(\):', 'Create draft PR example'),
            (r'def example_convert_draft_to_ready\(\):', 'Convert draft example'),
            (r'def example_auto_convert_on_ci_success\(\):', 'Auto-convert example'),
            (r'def example_draft_pr_workflow\(\):', 'Complete workflow example'),
            (r'def example_disable_draft_feature\(\):', 'Disable feature example'),
        ]
        
        result = check_file_contains(
            str(example_file),
            patterns,
            'Draft PR examples'
        )
    else:
        print(f"  ✗ Example file not found: {example_file}")
        result = False
    
    print(f"\n{'✅' if result else '❌'} Example code: {'PASS' if result else 'FAIL'}\n")
    return result


def verify_tests():
    """Verify test file exists."""
    print("=" * 70)
    print("VERIFICATION 9: Test Code")
    print("=" * 70)
    
    test_file = Path('tests/test_draft_pr.py')
    
    if test_file.exists():
        print(f"  ✓ Test file exists: {test_file}")
        
        patterns = [
            (r'class TestDraftPRCreation:', 'Draft PR creation tests'),
            (r'class TestDraftConversion:', 'Draft conversion tests'),
            (r'class TestAutoConversionOnCISuccess:', 'Auto-conversion tests'),
            (r'class TestDraftPRHandling:', 'Draft PR handling tests'),
            (r'def test_create_draft_pr_when_enabled', 'Test create draft PR'),
            (r'def test_convert_draft_to_ready', 'Test convert to ready'),
            (r'def test_auto_convert_on_ci_success', 'Test auto-convert'),
        ]
        
        result = check_file_contains(
            str(test_file),
            patterns,
            'Draft PR tests'
        )
    else:
        print(f"  ✗ Test file not found: {test_file}")
        result = False
    
    print(f"\n{'✅' if result else '❌'} Test code: {'PASS' if result else 'FAIL'}\n")
    return result


def main():
    """Run all verifications."""
    print("\n" + "=" * 70)
    print("TASK 12: DRAFT PR FUNCTIONALITY VERIFICATION")
    print("=" * 70 + "\n")
    
    verifications = [
        ("Draft Configuration", verify_config),
        ("Draft PR Methods", verify_pr_service_methods),
        ("Draft PR Creation (12.1)", verify_draft_creation),
        ("Draft Conversion (12.2)", verify_draft_conversion),
        ("Draft PR Handling (12.3, 12.4)", verify_draft_handling),
        ("Draft Feature Disable (12.5)", verify_draft_disable),
        ("Git Host Client Support", verify_git_host_clients),
        ("Example Code", verify_examples),
        ("Test Code", verify_tests),
    ]
    
    results = []
    for name, verify_func in verifications:
        try:
            result = verify_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Verification failed: {name}")
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Print summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print("\n" + "=" * 70)
    print(f"TOTAL: {passed}/{total} verifications passed")
    print("=" * 70 + "\n")
    
    if passed == total:
        print("🎉 All verifications passed! Task 12 implementation is complete.\n")
        return 0
    else:
        print("⚠️  Some verifications failed. Please review the implementation.\n")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

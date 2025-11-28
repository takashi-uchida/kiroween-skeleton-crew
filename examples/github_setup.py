#!/usr/bin/env python3
"""
GitHub Setup Example

This example demonstrates how to set up and configure the Review & PR Service
for GitHub, including authentication, configuration options, and best practices.
"""

import os
from necrocode.review_pr_service import (
    PRService,
    PRServiceConfig,
    GitHostType,
)
from necrocode.review_pr_service.config import (
    LabelConfig,
    ReviewerConfig,
    MergeConfig,
    DraftConfig,
    CIConfig,
    ConflictDetectionConfig,
    TemplateConfig,
)


def setup_basic_github_config():
    """Basic GitHub configuration"""
    
    print("=" * 60)
    print("Basic GitHub Configuration")
    print("=" * 60)
    
    # Get token from environment
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("❌ GITHUB_TOKEN not set")
        print("   Create a token at: https://github.com/settings/tokens")
        print("   Required scopes: repo, workflow")
        return None
    
    # Basic configuration
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",  # Replace with your repository
        api_token=github_token,
    )
    
    print("✅ Basic configuration created")
    print(f"   Repository: {config.repository}")
    print(f"   Git Host: GitHub")
    
    return config


def setup_github_with_labels():
    """GitHub configuration with label management"""
    
    print("\n" + "=" * 60)
    print("GitHub Configuration with Labels")
    print("=" * 60)
    
    config = setup_basic_github_config()
    if not config:
        return None
    
    # Configure label management
    config.labels = LabelConfig(
        enabled=True,
        rules={
            # Task type labels
            "backend": ["backend", "api", "server"],
            "frontend": ["frontend", "ui", "client"],
            "database": ["database", "schema", "migration"],
            "devops": ["devops", "ci", "deployment"],
            "documentation": ["docs", "documentation"],
            
            # Priority labels
            "high": ["priority:high", "urgent"],
            "medium": ["priority:medium"],
            "low": ["priority:low"],
            
            # Status labels
            "in-progress": ["status:in-progress"],
            "review-needed": ["status:review-needed"],
            "blocked": ["status:blocked"],
        }
    )
    
    print("✅ Label management configured")
    print(f"   Enabled: {config.labels.enabled}")
    print(f"   Rules defined: {len(config.labels.rules)}")
    
    return config


def setup_github_with_reviewers():
    """GitHub configuration with reviewer assignment"""
    
    print("\n" + "=" * 60)
    print("GitHub Configuration with Reviewers")
    print("=" * 60)
    
    config = setup_basic_github_config()
    if not config:
        return None
    
    # Configure reviewer assignment
    config.reviewers = ReviewerConfig(
        enabled=True,
        strategy="round-robin",  # Options: round-robin, load-balanced, codeowners
        default_reviewers=[
            "backend-team",
            "frontend-team",
            "senior-dev",
        ],
        codeowners_path=".github/CODEOWNERS",  # Optional: use CODEOWNERS file
        max_reviewers=2,  # Maximum reviewers per PR
    )
    
    print("✅ Reviewer assignment configured")
    print(f"   Strategy: {config.reviewers.strategy}")
    print(f"   Default reviewers: {len(config.reviewers.default_reviewers)}")
    print(f"   Max reviewers per PR: {config.reviewers.max_reviewers}")
    
    return config


def setup_github_with_merge_strategy():
    """GitHub configuration with merge strategy"""
    
    print("\n" + "=" * 60)
    print("GitHub Configuration with Merge Strategy")
    print("=" * 60)
    
    config = setup_basic_github_config()
    if not config:
        return None
    
    # Configure merge strategy
    config.merge = MergeConfig(
        strategy="squash",  # Options: merge, squash, rebase
        auto_merge_enabled=False,  # Enable auto-merge after CI success
        delete_branch_after_merge=True,  # Clean up branches
        required_approvals=1,  # Minimum approvals needed
        require_ci_success=True,  # Require CI to pass before merge
    )
    
    print("✅ Merge strategy configured")
    print(f"   Strategy: {config.merge.strategy}")
    print(f"   Auto-merge: {config.merge.auto_merge_enabled}")
    print(f"   Delete branch after merge: {config.merge.delete_branch_after_merge}")
    print(f"   Required approvals: {config.merge.required_approvals}")
    
    return config


def setup_github_with_draft_prs():
    """GitHub configuration with draft PR support"""
    
    print("\n" + "=" * 60)
    print("GitHub Configuration with Draft PRs")
    print("=" * 60)
    
    config = setup_basic_github_config()
    if not config:
        return None
    
    # Configure draft PR settings
    config.draft = DraftConfig(
        enabled=True,
        create_as_draft=True,  # Create PRs as drafts initially
        convert_on_ci_success=True,  # Convert to ready when CI passes
        skip_reviewers_for_draft=True,  # Don't assign reviewers to drafts
        draft_label="draft",  # Label for draft PRs
    )
    
    print("✅ Draft PR support configured")
    print(f"   Create as draft: {config.draft.create_as_draft}")
    print(f"   Convert on CI success: {config.draft.convert_on_ci_success}")
    print(f"   Skip reviewers for draft: {config.draft.skip_reviewers_for_draft}")
    
    return config


def setup_github_with_ci_monitoring():
    """GitHub configuration with CI monitoring"""
    
    print("\n" + "=" * 60)
    print("GitHub Configuration with CI Monitoring")
    print("=" * 60)
    
    config = setup_basic_github_config()
    if not config:
        return None
    
    # Configure CI monitoring
    config.ci = CIConfig(
        enabled=True,
        polling_interval=60,  # Poll every 60 seconds
        timeout=3600,  # 1 hour timeout
        auto_comment_on_failure=True,  # Post comment when CI fails
        auto_convert_draft_on_success=True,  # Convert draft to ready on success
    )
    
    print("✅ CI monitoring configured")
    print(f"   Polling interval: {config.ci.polling_interval}s")
    print(f"   Timeout: {config.ci.timeout}s")
    print(f"   Auto-comment on failure: {config.ci.auto_comment_on_failure}")
    
    return config


def setup_github_with_conflict_detection():
    """GitHub configuration with conflict detection"""
    
    print("\n" + "=" * 60)
    print("GitHub Configuration with Conflict Detection")
    print("=" * 60)
    
    config = setup_basic_github_config()
    if not config:
        return None
    
    # Configure conflict detection
    config.conflict_detection = ConflictDetectionConfig(
        enabled=True,
        check_on_creation=True,  # Check when PR is created
        auto_comment=True,  # Post comment if conflicts found
        periodic_check=True,  # Periodically check for new conflicts
        check_interval=1800,  # Check every 30 minutes
        recheck_on_push=True,  # Re-check when code is pushed
    )
    
    print("✅ Conflict detection configured")
    print(f"   Check on creation: {config.conflict_detection.check_on_creation}")
    print(f"   Auto-comment: {config.conflict_detection.auto_comment}")
    print(f"   Periodic check: {config.conflict_detection.periodic_check}")
    print(f"   Check interval: {config.conflict_detection.check_interval}s")
    
    return config


def setup_github_with_custom_templates():
    """GitHub configuration with custom templates"""
    
    print("\n" + "=" * 60)
    print("GitHub Configuration with Custom Templates")
    print("=" * 60)
    
    config = setup_basic_github_config()
    if not config:
        return None
    
    # Configure custom templates
    config.template = TemplateConfig(
        template_path="templates/pr-template.md",  # Custom PR template
        comment_template_path="templates/comment-template.md",  # Custom comment template
        include_test_results=True,
        include_artifact_links=True,
        include_execution_logs=True,
    )
    
    print("✅ Custom templates configured")
    print(f"   PR template: {config.template.template_path}")
    print(f"   Comment template: {config.template.comment_template_path}")
    print(f"   Include test results: {config.template.include_test_results}")
    
    return config


def setup_github_complete():
    """Complete GitHub configuration with all features"""
    
    print("\n" + "=" * 60)
    print("Complete GitHub Configuration")
    print("=" * 60)
    
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("❌ GITHUB_TOKEN not set")
        return None
    
    # Create comprehensive configuration
    config = PRServiceConfig(
        git_host_type=GitHostType.GITHUB,
        repository="owner/repo",
        api_token=github_token,
        
        # Labels
        labels=LabelConfig(
            enabled=True,
            rules={
                "backend": ["backend", "api"],
                "frontend": ["frontend", "ui"],
                "high": ["priority:high"],
            }
        ),
        
        # Reviewers
        reviewers=ReviewerConfig(
            enabled=True,
            strategy="round-robin",
            default_reviewers=["team-lead", "senior-dev"],
        ),
        
        # Merge strategy
        merge=MergeConfig(
            strategy="squash",
            auto_merge_enabled=False,
            delete_branch_after_merge=True,
            required_approvals=1,
        ),
        
        # Draft PRs
        draft=DraftConfig(
            enabled=True,
            create_as_draft=True,
            convert_on_ci_success=True,
        ),
        
        # CI monitoring
        ci=CIConfig(
            enabled=True,
            polling_interval=60,
            auto_comment_on_failure=True,
        ),
        
        # Conflict detection
        conflict_detection=ConflictDetectionConfig(
            enabled=True,
            check_on_creation=True,
            auto_comment=True,
            periodic_check=True,
        ),
        
        # Templates
        template=TemplateConfig(
            template_path="templates/pr-template.md",
            include_test_results=True,
            include_artifact_links=True,
        ),
    )
    
    print("✅ Complete configuration created")
    print("   All features enabled:")
    print(f"   - Labels: {config.labels.enabled}")
    print(f"   - Reviewers: {config.reviewers.enabled}")
    print(f"   - Draft PRs: {config.draft.enabled}")
    print(f"   - CI Monitoring: {config.ci.enabled}")
    print(f"   - Conflict Detection: {config.conflict_detection.enabled}")
    
    return config


def test_github_connection(config):
    """Test GitHub connection"""
    
    print("\n" + "=" * 60)
    print("Testing GitHub Connection")
    print("=" * 60)
    
    try:
        pr_service = PRService(config)
        print("✅ Successfully connected to GitHub")
        print(f"   Repository: {config.repository}")
        return pr_service
    except Exception as e:
        print(f"❌ Failed to connect to GitHub: {e}")
        return None


def main():
    """Main function demonstrating GitHub setup"""
    
    print("=" * 60)
    print("GitHub Setup Examples")
    print("=" * 60)
    
    # Example 1: Basic configuration
    config1 = setup_basic_github_config()
    
    # Example 2: With labels
    config2 = setup_github_with_labels()
    
    # Example 3: With reviewers
    config3 = setup_github_with_reviewers()
    
    # Example 4: With merge strategy
    config4 = setup_github_with_merge_strategy()
    
    # Example 5: With draft PRs
    config5 = setup_github_with_draft_prs()
    
    # Example 6: With CI monitoring
    config6 = setup_github_with_ci_monitoring()
    
    # Example 7: With conflict detection
    config7 = setup_github_with_conflict_detection()
    
    # Example 8: With custom templates
    config8 = setup_github_with_custom_templates()
    
    # Example 9: Complete configuration
    config9 = setup_github_complete()
    
    # Test connection with complete configuration
    if config9:
        pr_service = test_github_connection(config9)
        if pr_service:
            print("\n✅ GitHub setup complete and tested successfully!")
    
    print("\n" + "=" * 60)
    print("Setup Complete")
    print("=" * 60)
    print("You can now use any of these configurations to create a PR Service.")
    print("\nNext steps:")
    print("1. Set GITHUB_TOKEN environment variable")
    print("2. Update repository name in configuration")
    print("3. Customize labels, reviewers, and other settings")
    print("4. Create your first PR with pr_service.create_pr()")


if __name__ == "__main__":
    main()

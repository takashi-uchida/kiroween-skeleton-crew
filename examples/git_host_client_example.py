"""
Example: Using Git Host Clients

Demonstrates how to use GitHubClient, GitLabClient, and BitbucketClient
to create and manage pull requests across different Git hosting platforms.

Requirements: 3.1, 3.2, 3.3, 3.4
"""

from necrocode.review_pr_service import (
    GitHubClient,
    GitLabClient,
    BitbucketClient,
    PRState,
    CIStatus,
)


def github_example():
    """Example using GitHub client."""
    print("=== GitHub Client Example ===\n")
    
    # Initialize GitHub client
    config = {
        "token": "ghp_your_github_token_here",
        "repo_owner": "your-username",
        "repo_name": "your-repo"
    }
    
    client = GitHubClient(config)
    
    # Create a pull request
    pr = client.create_pull_request(
        title="Add new feature",
        description="This PR adds a new feature to the application.",
        source_branch="feature/new-feature",
        target_branch="main",
        draft=False
    )
    
    print(f"Created PR #{pr.pr_number}: {pr.title}")
    print(f"URL: {pr.url}")
    print(f"State: {pr.state.value}\n")
    
    # Add labels
    client.add_labels(pr.pr_id, ["enhancement", "backend"])
    print("Added labels: enhancement, backend\n")
    
    # Assign reviewers
    client.assign_reviewers(pr.pr_id, ["reviewer1", "reviewer2"])
    print("Assigned reviewers: reviewer1, reviewer2\n")
    
    # Add a comment
    client.add_comment(pr.pr_id, "Please review this PR. Thanks!")
    print("Added comment to PR\n")
    
    # Check CI status
    ci_status = client.get_ci_status(pr.pr_id)
    print(f"CI Status: {ci_status.value}\n")
    
    # Check for conflicts
    has_conflicts = client.check_conflicts(pr.pr_id)
    print(f"Has conflicts: {has_conflicts}\n")
    
    # Update PR description
    client.update_pr_description(
        pr.pr_id,
        "Updated description with more details."
    )
    print("Updated PR description\n")


def gitlab_example():
    """Example using GitLab client."""
    print("=== GitLab Client Example ===\n")
    
    # Initialize GitLab client
    config = {
        "token": "glpat-your_gitlab_token_here",
        "url": "https://gitlab.com",  # or your self-hosted GitLab URL
        "project_id": "12345"
    }
    
    client = GitLabClient(config)
    
    # Create a merge request (GitLab's equivalent of PR)
    mr = client.create_pull_request(
        title="Implement user authentication",
        description="This MR implements JWT-based authentication.",
        source_branch="feature/auth",
        target_branch="main",
        draft=True  # Create as draft
    )
    
    print(f"Created MR !{mr.pr_number}: {mr.title}")
    print(f"URL: {mr.url}")
    print(f"Draft: {mr.draft}\n")
    
    # Add labels
    client.add_labels(mr.pr_id, ["security", "backend"])
    print("Added labels: security, backend\n")
    
    # Assign reviewers
    client.assign_reviewers(mr.pr_id, ["reviewer1"])
    print("Assigned reviewer: reviewer1\n")
    
    # Convert from draft to ready
    client.convert_to_ready(mr.pr_id)
    print("Converted MR from draft to ready\n")
    
    # Check CI status
    ci_status = client.get_ci_status(mr.pr_id)
    print(f"Pipeline Status: {ci_status.value}\n")


def bitbucket_example():
    """Example using Bitbucket client."""
    print("=== Bitbucket Client Example ===\n")
    
    # Initialize Bitbucket client
    config = {
        "username": "your-username",
        "password": "your-app-password",  # Use app password, not account password
        "url": "https://api.bitbucket.org",
        "workspace": "your-workspace",
        "repo_slug": "your-repo"
    }
    
    client = BitbucketClient(config)
    
    # Create a pull request
    pr = client.create_pull_request(
        title="Fix bug in payment processing",
        description="This PR fixes a critical bug in the payment module.",
        source_branch="bugfix/payment-issue",
        target_branch="main",
        draft=False
    )
    
    print(f"Created PR #{pr.pr_number}: {pr.title}")
    print(f"URL: {pr.url}\n")
    
    # Assign reviewers
    client.assign_reviewers(pr.pr_id, ["reviewer1", "reviewer2"])
    print("Assigned reviewers: reviewer1, reviewer2\n")
    
    # Add a comment
    client.add_comment(pr.pr_id, "This fixes issue #123")
    print("Added comment to PR\n")
    
    # Check CI status
    ci_status = client.get_ci_status(pr.pr_id)
    print(f"Build Status: {ci_status.value}\n")
    
    # Check for conflicts
    has_conflicts = client.check_conflicts(pr.pr_id)
    print(f"Has conflicts: {has_conflicts}\n")


def unified_interface_example():
    """
    Example showing how the unified interface allows
    switching between Git hosts easily.
    """
    print("=== Unified Interface Example ===\n")
    
    # You can use the same code with different clients
    def create_and_manage_pr(client, branch_name):
        """Generic function that works with any Git host client."""
        # Create PR
        pr = client.create_pull_request(
            title=f"Feature from {branch_name}",
            description="Implementing new feature",
            source_branch=branch_name,
            target_branch="main"
        )
        
        # Add labels (may not work on all platforms)
        try:
            client.add_labels(pr.pr_id, ["feature"])
        except:
            print("Labels not supported on this platform")
        
        # Assign reviewers
        client.assign_reviewers(pr.pr_id, ["reviewer1"])
        
        # Check status
        ci_status = client.get_ci_status(pr.pr_id)
        
        return pr, ci_status
    
    # This function works with GitHub, GitLab, or Bitbucket
    # Just pass the appropriate client instance
    print("The same code works across all Git hosting platforms!")


if __name__ == "__main__":
    print("Git Host Client Examples")
    print("=" * 50)
    print()
    
    # Note: These examples require valid credentials
    # Uncomment the example you want to run:
    
    # github_example()
    # gitlab_example()
    # bitbucket_example()
    # unified_interface_example()
    
    print("\nNote: Update the configuration with your actual credentials")
    print("before running these examples.")

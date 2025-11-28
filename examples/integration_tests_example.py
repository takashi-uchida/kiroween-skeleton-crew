#!/usr/bin/env python3
"""
Example: Running Integration Tests for Review & PR Service

This example demonstrates how to set up and run integration tests
for the Review & PR Service with actual Git host APIs.

The integration tests verify:
1. PR creation with all features (labels, reviewers, draft mode)
2. PR updates (description, CI status, conflict detection)
3. Webhook reception and processing
4. End-to-end workflows

Requirements:
- Git host credentials (GitHub, GitLab, or Bitbucket)
- Test repository with appropriate permissions
- pytest and required dependencies installed
"""

import os
import sys
import subprocess
from pathlib import Path


def setup_github_credentials():
    """
    Set up GitHub credentials for integration tests.
    
    You can get a GitHub personal access token from:
    https://github.com/settings/tokens
    
    Required scopes:
    - repo (full control of private repositories)
    - workflow (update GitHub Action workflows)
    """
    print("Setting up GitHub credentials...")
    print()
    
    # Check if credentials are already set
    if os.getenv("GITHUB_TOKEN"):
        print("✓ GITHUB_TOKEN already set")
    else:
        print("Please set GITHUB_TOKEN environment variable:")
        print("  export GITHUB_TOKEN='your_github_token'")
        print()
    
    if os.getenv("GITHUB_TEST_REPO"):
        print(f"✓ GITHUB_TEST_REPO already set: {os.getenv('GITHUB_TEST_REPO')}")
    else:
        print("Please set GITHUB_TEST_REPO environment variable:")
        print("  export GITHUB_TEST_REPO='owner/repo'")
        print()


def setup_gitlab_credentials():
    """
    Set up GitLab credentials for integration tests.
    
    You can get a GitLab personal access token from:
    https://gitlab.com/-/profile/personal_access_tokens
    
    Required scopes:
    - api (full API access)
    """
    print("Setting up GitLab credentials...")
    print()
    
    if os.getenv("GITLAB_TOKEN"):
        print("✓ GITLAB_TOKEN already set")
    else:
        print("Please set GITLAB_TOKEN environment variable:")
        print("  export GITLAB_TOKEN='your_gitlab_token'")
        print()
    
    if os.getenv("GITLAB_TEST_PROJECT"):
        print(f"✓ GITLAB_TEST_PROJECT already set: {os.getenv('GITLAB_TEST_PROJECT')}")
    else:
        print("Please set GITLAB_TEST_PROJECT environment variable:")
        print("  export GITLAB_TEST_PROJECT='12345'  # Project ID")
        print()


def setup_bitbucket_credentials():
    """
    Set up Bitbucket credentials for integration tests.
    
    You can create a Bitbucket app password from:
    https://bitbucket.org/account/settings/app-passwords/
    
    Required permissions:
    - Repositories: Read, Write
    - Pull requests: Read, Write
    """
    print("Setting up Bitbucket credentials...")
    print()
    
    if os.getenv("BITBUCKET_USERNAME") and os.getenv("BITBUCKET_APP_PASSWORD"):
        print("✓ Bitbucket credentials already set")
    else:
        print("Please set Bitbucket credentials:")
        print("  export BITBUCKET_USERNAME='your_username'")
        print("  export BITBUCKET_APP_PASSWORD='your_app_password'")
        print("  export BITBUCKET_TEST_REPO='workspace/repo-slug'")
        print()


def run_github_integration_tests():
    """Run GitHub integration tests"""
    print("=" * 70)
    print("Running GitHub Integration Tests")
    print("=" * 70)
    print()
    
    if not os.getenv("GITHUB_TOKEN"):
        print("⚠ GITHUB_TOKEN not set. Skipping GitHub tests.")
        print()
        return
    
    # Run tests
    cmd = [
        "pytest",
        "tests/test_pr_service_integration.py",
        "-m", "integration and github",
        "-v",
        "--tb=short",
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=False)
        if result.returncode == 0:
            print()
            print("✓ GitHub integration tests passed")
        else:
            print()
            print("✗ GitHub integration tests failed")
    except FileNotFoundError:
        print("✗ pytest not found. Please install: pip install pytest")


def run_gitlab_integration_tests():
    """Run GitLab integration tests"""
    print("=" * 70)
    print("Running GitLab Integration Tests")
    print("=" * 70)
    print()
    
    if not os.getenv("GITLAB_TOKEN"):
        print("⚠ GITLAB_TOKEN not set. Skipping GitLab tests.")
        print()
        return
    
    cmd = [
        "pytest",
        "tests/test_pr_service_integration.py",
        "-m", "integration and gitlab",
        "-v",
        "--tb=short",
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=False)
        if result.returncode == 0:
            print()
            print("✓ GitLab integration tests passed")
        else:
            print()
            print("✗ GitLab integration tests failed")
    except FileNotFoundError:
        print("✗ pytest not found. Please install: pip install pytest")


def run_webhook_integration_tests():
    """Run webhook integration tests"""
    print("=" * 70)
    print("Running Webhook Integration Tests")
    print("=" * 70)
    print()
    
    # Set webhook configuration
    os.environ.setdefault("WEBHOOK_SECRET", "test_secret_key_12345")
    os.environ.setdefault("WEBHOOK_PORT", "8080")
    
    cmd = [
        "pytest",
        "tests/test_webhook_integration.py",
        "-m", "integration and webhook",
        "-k", "not live",  # Skip live tests by default
        "-v",
        "--tb=short",
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=False)
        if result.returncode == 0:
            print()
            print("✓ Webhook integration tests passed")
        else:
            print()
            print("✗ Webhook integration tests failed")
    except FileNotFoundError:
        print("✗ pytest not found. Please install: pip install pytest")


def run_end_to_end_tests():
    """Run end-to-end workflow tests"""
    print("=" * 70)
    print("Running End-to-End Workflow Tests")
    print("=" * 70)
    print()
    
    if not os.getenv("GITHUB_TOKEN"):
        print("⚠ GITHUB_TOKEN not set. Skipping E2E tests.")
        print()
        return
    
    cmd = [
        "pytest",
        "tests/test_pr_service_integration.py::TestEndToEndWorkflow",
        "-v",
        "--tb=short",
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=False)
        if result.returncode == 0:
            print()
            print("✓ End-to-end tests passed")
        else:
            print()
            print("✗ End-to-end tests failed")
    except FileNotFoundError:
        print("✗ pytest not found. Please install: pip install pytest")


def show_live_webhook_test_instructions():
    """Show instructions for running live webhook tests"""
    print("=" * 70)
    print("Live Webhook Testing Instructions")
    print("=" * 70)
    print()
    print("Live webhook tests require actual webhook delivery from Git hosts.")
    print()
    print("Setup steps:")
    print("1. Start the webhook server:")
    print("   export WEBHOOK_TEST_MODE=live")
    print("   export WEBHOOK_SECRET='your_secret'")
    print("   pytest tests/test_webhook_integration.py::TestLiveWebhookDelivery -v")
    print()
    print("2. Configure webhook in your Git host:")
    print("   - GitHub: Settings → Webhooks → Add webhook")
    print("   - GitLab: Settings → Webhooks → Add webhook")
    print("   - Bitbucket: Settings → Webhooks → Add webhook")
    print()
    print("3. Set webhook URL to: http://your-server:8080/webhook")
    print("   (Use ngrok or similar for local testing)")
    print()
    print("4. Set webhook secret to match WEBHOOK_SECRET")
    print()
    print("5. Trigger events (create PR, merge PR, etc.)")
    print()
    print("6. Test will report received events after 60 seconds")
    print()


def main():
    """Main example function"""
    print()
    print("=" * 70)
    print("Review & PR Service - Integration Tests Example")
    print("=" * 70)
    print()
    
    # Show credential setup
    print("Step 1: Set up credentials")
    print("-" * 70)
    setup_github_credentials()
    setup_gitlab_credentials()
    setup_bitbucket_credentials()
    
    # Check if any credentials are set
    has_credentials = (
        os.getenv("GITHUB_TOKEN") or
        os.getenv("GITLAB_TOKEN") or
        (os.getenv("BITBUCKET_USERNAME") and os.getenv("BITBUCKET_APP_PASSWORD"))
    )
    
    if not has_credentials:
        print()
        print("⚠ No credentials set. Please set credentials to run integration tests.")
        print()
        print("Example:")
        print("  export GITHUB_TOKEN='ghp_xxxxxxxxxxxx'")
        print("  export GITHUB_TEST_REPO='myorg/myrepo'")
        print("  python examples/integration_tests_example.py")
        print()
        return
    
    print()
    print("Step 2: Run integration tests")
    print("-" * 70)
    print()
    
    # Run tests based on available credentials
    if os.getenv("GITHUB_TOKEN"):
        run_github_integration_tests()
        print()
    
    if os.getenv("GITLAB_TOKEN"):
        run_gitlab_integration_tests()
        print()
    
    # Always run webhook tests (they work without credentials)
    run_webhook_integration_tests()
    print()
    
    # Run E2E tests if GitHub credentials are available
    if os.getenv("GITHUB_TOKEN"):
        run_end_to_end_tests()
        print()
    
    # Show live webhook test instructions
    show_live_webhook_test_instructions()
    
    print("=" * 70)
    print("Integration Tests Example Complete")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()

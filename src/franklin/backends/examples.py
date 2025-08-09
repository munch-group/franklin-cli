#!/usr/bin/env python3
"""
Examples of using the Franklin backend system.

This module demonstrates how to use the abstract backend interface
with both GitLab and GitHub.
"""

import os
from typing import Optional

from franklin.backends import (
    get_backend,
    GitLabBackend,
    GitHubBackend,
    Repository,
    Visibility,
    AccessLevel,
    BackendError,
    AuthenticationError
)


def example_gitlab_usage():
    """Example of using GitLab backend."""
    print("=== GitLab Backend Example ===\n")
    
    # Create GitLab backend
    backend = GitLabBackend(
        url="https://gitlab.com",
        token=os.environ.get("GITLAB_TOKEN")
    )
    
    try:
        # Authenticate
        if not backend.authenticate({"token": os.environ.get("GITLAB_TOKEN")}):
            print("Failed to authenticate with GitLab")
            return
        
        print("✓ Authenticated with GitLab")
        
        # Get current user
        user = backend.get_current_user()
        print(f"✓ Current user: {user.username} ({user.name})")
        
        # Create a repository
        repo = backend.create_repository(
            name="test-franklin-repo",
            visibility=Visibility.PRIVATE,
            description="Test repository created by Franklin",
            init_readme=True
        )
        print(f"✓ Created repository: {repo.full_name}")
        print(f"  - Clone URL: {repo.clone_url}")
        print(f"  - Web URL: {repo.web_url}")
        
        # Create a file
        backend.create_file(
            repo_id=repo.id,
            file_path="hello.txt",
            content="Hello from Franklin!",
            message="Add hello.txt",
            branch="main"
        )
        print("✓ Created file: hello.txt")
        
        # List user's repositories
        repos = backend.list_repositories(owned=True, visibility=Visibility.PRIVATE)
        print(f"✓ Found {len(repos)} private repositories")
        
        # Clean up - delete the test repository
        if input("\nDelete test repository? (y/n): ").lower() == 'y':
            backend.delete_repository(repo.id)
            print("✓ Deleted test repository")
            
    except AuthenticationError as e:
        print(f"✗ Authentication error: {e}")
    except BackendError as e:
        print(f"✗ Backend error: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")


def example_github_usage():
    """Example of using GitHub backend."""
    print("\n=== GitHub Backend Example ===\n")
    
    # Create GitHub backend
    backend = GitHubBackend(token=os.environ.get("GITHUB_TOKEN"))
    
    try:
        # Authenticate
        if not backend.authenticate({"token": os.environ.get("GITHUB_TOKEN")}):
            print("Failed to authenticate with GitHub")
            return
        
        print("✓ Authenticated with GitHub")
        
        # Get current user
        user = backend.get_current_user()
        print(f"✓ Current user: {user.username} ({user.name})")
        
        # Check capabilities
        caps = backend.capabilities
        print(f"✓ Backend capabilities:")
        print(f"  - Can create users: {caps.create_users}")
        print(f"  - Can create groups: {caps.create_groups}")
        print(f"  - Supports nested groups: {caps.nested_groups}")
        print(f"  - Has CI/CD: {caps.ci_cd}")
        
        # Create a repository
        repo = backend.create_repository(
            name="test-franklin-repo",
            visibility=Visibility.PRIVATE,
            description="Test repository created by Franklin",
            init_readme=True
        )
        print(f"✓ Created repository: {repo.full_name}")
        print(f"  - Clone URL: {repo.clone_url}")
        print(f"  - Web URL: {repo.web_url}")
        
        # Create a pull request (after making changes)
        # First create a new branch and file
        backend.create_file(
            repo_id=repo.full_name,
            file_path="feature.txt",
            content="New feature",
            message="Add feature",
            branch="main"
        )
        
        # Note: Creating PRs requires branches to exist
        # This is just an example structure
        
        # List user's organizations
        orgs = backend.list_groups()
        print(f"✓ Found {len(orgs)} organizations")
        for org in orgs:
            print(f"  - {org.name}")
        
        # Clean up - delete the test repository
        if input("\nDelete test repository? (y/n): ").lower() == 'y':
            backend.delete_repository(repo.full_name)
            print("✓ Deleted test repository")
            
    except AuthenticationError as e:
        print(f"✗ Authentication error: {e}")
    except BackendError as e:
        print(f"✗ Backend error: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")


def example_backend_agnostic():
    """Example of backend-agnostic code."""
    print("\n=== Backend-Agnostic Example ===\n")
    
    # Load backend from configuration
    # This will read from ~/.franklin/backend.yaml
    try:
        backend = get_backend()
        
        # Authenticate if needed
        if not backend.is_authenticated:
            # Token should be in config or environment
            backend.authenticate({})
        
        # Now use backend without knowing if it's GitLab or GitHub
        user = backend.get_current_user()
        print(f"Current user: {user.username}")
        
        # List repositories
        repos = backend.list_repositories()
        print(f"Found {len(repos)} repositories")
        
        # The same code works with any backend!
        
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure you have a backend configured in ~/.franklin/backend.yaml")


def example_switching_backends():
    """Example of switching between backends."""
    print("\n=== Backend Switching Example ===\n")
    
    from franklin.backends import BackendFactory
    
    # Get list of available backends
    available = BackendFactory.list_backends()
    print(f"Available backends: {', '.join(available)}")
    
    # Create different backends
    for backend_type in ['gitlab', 'github']:
        print(f"\nUsing {backend_type} backend:")
        
        # Get appropriate token
        if backend_type == 'gitlab':
            token = os.environ.get('GITLAB_TOKEN')
            config = {'url': 'https://gitlab.com', 'token': token}
        else:
            token = os.environ.get('GITHUB_TOKEN')
            config = {'token': token}
        
        if not token:
            print(f"  ✗ No token found for {backend_type} (set {backend_type.upper()}_TOKEN)")
            continue
        
        # Create backend
        backend = BackendFactory.create_backend(backend_type, **config)
        
        # Authenticate
        if backend.authenticate({'token': token}):
            user = backend.get_current_user()
            print(f"  ✓ Authenticated as {user.username}")
        else:
            print(f"  ✗ Failed to authenticate")


def example_configuration():
    """Example of configuration-based backend usage."""
    print("\n=== Configuration Example ===\n")
    
    print("Example configuration file (~/.franklin/backend.yaml):")
    print("""
# For GitLab:
backend:
  type: gitlab
  settings:
    url: https://gitlab.com
    token: ${GITLAB_TOKEN}
  defaults:
    visibility: private
    init_readme: true

# For GitHub:
backend:
  type: github
  settings:
    token: ${GITHUB_TOKEN}
  defaults:
    visibility: private
    org: my-organization  # Optional
""")
    
    print("\nEnvironment variables are expanded automatically!")
    print("Set GITLAB_TOKEN or GITHUB_TOKEN in your environment.")


def main():
    """Run examples based on command line arguments."""
    import sys
    
    if len(sys.argv) > 1:
        example = sys.argv[1]
        if example == 'gitlab':
            example_gitlab_usage()
        elif example == 'github':
            example_github_usage()
        elif example == 'agnostic':
            example_backend_agnostic()
        elif example == 'switch':
            example_switching_backends()
        elif example == 'config':
            example_configuration()
        else:
            print(f"Unknown example: {example}")
            print("Available examples: gitlab, github, agnostic, switch, config")
    else:
        print("Franklin Backend System Examples")
        print("=" * 40)
        print("\nUsage: python examples.py <example>")
        print("\nAvailable examples:")
        print("  gitlab   - GitLab backend usage")
        print("  github   - GitHub backend usage")
        print("  agnostic - Backend-agnostic code")
        print("  switch   - Switching between backends")
        print("  config   - Configuration examples")
        print("\nNote: Set GITLAB_TOKEN and/or GITHUB_TOKEN environment variables first!")


if __name__ == "__main__":
    main()
# Franklin Backend System

This module provides a unified interface for interacting with different git hosting platforms (GitLab, GitHub, etc.) in Franklin.

## Features

- **Platform-agnostic interface** - Write code once, run on any git platform
- **Multiple backend support** - GitLab and GitHub currently implemented
- **Configuration-driven** - Switch backends via configuration without code changes
- **Type-safe** - Full type hints and data models
- **Capability detection** - Automatically handle platform differences

## Installation

The backend system is included with Franklin. To use specific backends, install their dependencies:

```bash
# For GitLab backend
pip install python-gitlab

# For GitHub backend
pip install PyGithub
```

## Quick Start

### Using a specific backend directly

```python
from franklin.backends import GitLabBackend, GitHubBackend

# GitLab
gitlab = GitLabBackend(url="https://gitlab.com", token="your-token")
gitlab.authenticate({"token": "your-token"})
repo = gitlab.create_repository("my-repo", visibility="private")

# GitHub
github = GitHubBackend(token="your-token")
github.authenticate({"token": "your-token"})
repo = github.create_repository("my-repo", visibility="private")
```

### Using the backend factory

```python
from franklin.backends import get_backend

# Automatically loads from configuration
backend = get_backend()
backend.authenticate({"token": "your-token"})
repos = backend.list_repositories()
```

## Configuration

Create a configuration file at `~/.franklin/backend.yaml`:

### GitLab Configuration

```yaml
backend:
  type: gitlab
  settings:
    url: https://gitlab.com  # or your GitLab instance
    token: ${GITLAB_TOKEN}   # Environment variable
  defaults:
    visibility: private
    init_readme: true
    default_branch: main
```

### GitHub Configuration

```yaml
backend:
  type: github
  settings:
    token: ${GITHUB_TOKEN}    # Environment variable
    base_url: null            # Set for GitHub Enterprise
  defaults:
    visibility: private
    init_readme: true
    org: my-organization      # Optional default organization
```

## Backend Capabilities

Different platforms have different capabilities. Check what's supported:

```python
backend = get_backend()
caps = backend.capabilities

if caps.create_users:
    # Platform supports creating users
    user = backend.create_user({"username": "newuser", ...})

if caps.nested_groups:
    # Platform supports nested groups/organizations
    subgroup = backend.create_group("subgroup", parent_id=parent.id)
```

### Capability Matrix

| Feature | GitLab | GitHub |
|---------|--------|--------|
| Create Users | ✅ | ❌ |
| Create Groups | ✅ | ✅* |
| Nested Groups | ✅ | ❌ |
| Fork Repository | ✅ | ✅ |
| Protected Branches | ✅ | ✅ |
| Merge/Pull Requests | ✅ | ✅ |
| CI/CD | ✅ | ✅ |
| Webhooks | ✅ | ✅ |
| Deploy Keys | ✅ | ✅ |
| Issues | ✅ | ✅ |
| Wiki | ✅ | ✅ |
| Snippets/Gists | ✅ | ✅ |
| Package Registry | ✅ | ✅ |
| Pages | ✅ | ✅ |

*GitHub "groups" are organizations

## API Reference

### Core Operations

#### Repository Management

```python
# Create repository
repo = backend.create_repository(
    name="my-repo",
    visibility="private",  # or "public", "internal" (GitLab only)
    description="My repository",
    init_readme=True
)

# Get repository
repo = backend.get_repository("owner/repo")  # or by ID

# Update repository
repo = backend.update_repository(
    "owner/repo",
    description="Updated description",
    default_branch="develop"
)

# Delete repository
backend.delete_repository("owner/repo")

# List repositories
repos = backend.list_repositories(
    owned=True,           # Only owned repos
    visibility="private", # Filter by visibility
    search="keyword"      # Search term
)

# Fork repository
fork = backend.fork_repository(
    "original/repo",
    organization="my-org"  # Optional
)
```

#### User Management

```python
# Get current user
me = backend.get_current_user()

# Get specific user
user = backend.get_user("username")

# List users (limited on some platforms)
users = backend.list_users(search="john")

# Create user (GitLab only)
if backend.capabilities.create_users:
    user = backend.create_user({
        "username": "newuser",
        "email": "user@example.com",
        "name": "New User"
    })
```

#### Group/Organization Management

```python
# Create group/organization
group = backend.create_group(
    "my-group",
    description="My group",
    visibility="private"
)

# Get group
group = backend.get_group("group-name")

# List groups
groups = backend.list_groups()

# Add user to group
backend.add_user_to_group(
    group_id="group-name",
    user_id="username",
    access_level=AccessLevel.DEVELOPER
)

# Remove user from group
backend.remove_user_from_group("group-name", "username")
```

#### File Operations

```python
# Get file content
content = backend.get_file_content(
    repo_id="owner/repo",
    file_path="README.md",
    ref="main"  # branch, tag, or commit
)

# Create file
backend.create_file(
    repo_id="owner/repo",
    file_path="new-file.txt",
    content="File content",
    message="Add new file",
    branch="main"
)

# Update file
backend.update_file(
    repo_id="owner/repo",
    file_path="existing-file.txt",
    content="Updated content",
    message="Update file",
    branch="main"
)

# Delete file
backend.delete_file(
    repo_id="owner/repo",
    file_path="old-file.txt",
    message="Delete file",
    branch="main"
)
```

#### Merge/Pull Requests

```python
# Create merge/pull request
mr = backend.create_merge_request(
    repo_id="owner/repo",
    title="Add new feature",
    source_branch="feature-branch",
    target_branch="main",
    description="This PR adds...",
    assignee_id="username"
)

# Get merge request
mr = backend.get_merge_request("owner/repo", mr_id="123")

# List merge requests
mrs = backend.list_merge_requests(
    repo_id="owner/repo",
    state="open",  # or "closed", "merged"
    author_id="username"
)
```

## Data Models

### Repository

```python
@dataclass
class Repository:
    id: str
    name: str
    full_name: str  # owner/name
    description: Optional[str]
    clone_url: str
    ssh_url: str
    web_url: str
    default_branch: str
    visibility: Visibility
    owner: str
    created_at: datetime
    updated_at: datetime
    # ... more fields
```

### User

```python
@dataclass
class User:
    id: str
    username: str
    email: Optional[str]
    name: Optional[str]
    avatar_url: Optional[str]
    web_url: str
    # ... more fields
```

### Group

```python
@dataclass
class Group:
    id: str
    name: str
    full_path: str
    description: Optional[str]
    web_url: str
    visibility: Visibility
    # ... more fields
```

## Error Handling

```python
from franklin.backends import (
    BackendError,
    AuthenticationError,
    RepositoryNotFoundError,
    UserNotFoundError,
    BackendPermissionError
)

try:
    backend.get_repository("nonexistent/repo")
except RepositoryNotFoundError as e:
    print(f"Repository not found: {e}")
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
except BackendError as e:
    print(f"Backend error: {e}")
```

## Examples

See `examples.py` for complete examples:

```bash
# Run examples
python -m franklin.backends.examples gitlab
python -m franklin.backends.examples github
python -m franklin.backends.examples agnostic
```

## Testing

```python
import pytest
from unittest.mock import Mock, patch
from franklin.backends import GitLabBackend, GitHubBackend

def test_backend_interface():
    """Test that backends implement the interface correctly."""
    for BackendClass in [GitLabBackend, GitHubBackend]:
        backend = BackendClass()
        
        # Test required methods exist
        assert hasattr(backend, 'authenticate')
        assert hasattr(backend, 'create_repository')
        assert hasattr(backend, 'get_repository')
        # ... etc
```

## Migration from Direct GitLab Usage

If you have existing code using GitLab directly:

```python
# Old code
import gitlab
gl = gitlab.Gitlab(url, token)
project = gl.projects.create({'name': 'my-repo'})

# New code
from franklin.backends import get_backend
backend = get_backend()  # Automatically uses configured backend
repo = backend.create_repository('my-repo')
```

## Adding New Backends

To add support for a new git platform:

1. Create a new backend class inheriting from `GitBackend`
2. Implement all abstract methods
3. Register with the factory
4. Add configuration support

```python
# my_backend.py
from franklin.backends import GitBackend, BackendFactory

class MyBackend(GitBackend):
    def authenticate(self, credentials):
        # Implementation
        pass
    
    # ... implement all methods

# Register
BackendFactory.register_backend('myplatform', MyBackend)
```

## Troubleshooting

### Authentication Issues

- Ensure your token has the necessary permissions
- For GitLab: api, read_user, read_repository scopes
- For GitHub: repo, user, admin:org scopes (as needed)

### Network Issues

- Check if you're behind a proxy
- Verify the backend URL is correct
- For self-hosted instances, check SSL certificates

### Platform Limitations

- GitHub doesn't support creating users via API
- GitHub doesn't have nested organizations
- GitLab's "internal" visibility maps to "private" on other platforms

## Support

For issues or questions about the backend system, please open an issue on the Franklin repository.
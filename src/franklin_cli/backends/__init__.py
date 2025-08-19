"""
Git backend abstraction layer for Franklin.

This module provides a general interface for git hosting platforms,
allowing Franklin to work with GitLab, GitHub, and other providers
interchangeably.
"""


#   1. Add import hook in franklin/__init__.py:
#   import os
#   if os.environ.get('FRANKLIN_USE_BACKEND'):
#       from franklin_cli.backends.adapter import gitlab
#       sys.modules['franklin.gitlab'] = gitlab
#   2. Test with environment variable:
#   export FRANKLIN_USE_BACKEND=true
#   franklin download https://gitlab.com/course/exercise-1
#   3. Gradually update imports in existing files as needed


# import sys, os
# if os.environ.get('FRANKLIN_USE_BACKEND'):
#     from franklin_cli.backends.adapter import gitlab
#     sys.modules['franklin.gitlab'] = gitlab
# os.environ['FRANKLIN_USE_BACKEND'] = 'true' 
# # Ensure the environment variable is set
# # export FRANKLIN_USE_BACKEND=true


from .base import (
    GitBackend,
    Repository,
    User,
    Group,
    MergeRequest,
    BackendCapabilities,
    Visibility,
    AccessLevel,
    BackendError,
    AuthenticationError,
    RepositoryNotFoundError,
    UserNotFoundError,
    PermissionError as BackendPermissionError
)

from .factory import BackendFactory, get_backend, get_current_backend
from .gitlab_backend import GitLabBackend
from .github_backend import GitHubBackend

__all__ = [
    # Base classes
    'GitBackend',
    
    # Implementations
    'GitLabBackend',
    'GitHubBackend',
    
    # Data models
    'Repository',
    'User',
    'Group',
    'MergeRequest',
    'BackendCapabilities',
    'Visibility',
    'AccessLevel',
    
    # Exceptions
    'BackendError',
    'AuthenticationError',
    'RepositoryNotFoundError',
    'UserNotFoundError',
    'BackendPermissionError',
    
    # Factory
    'BackendFactory',
    'get_backend',
    'get_current_backend',
]
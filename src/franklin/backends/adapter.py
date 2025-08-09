"""
Adapter layer to bridge existing Franklin GitLab code with the new backend system.

This module provides compatibility classes and functions that allow the existing
Franklin codebase to work with the new backend abstraction without modifications.
"""

import os
import sys
import subprocess
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import json
import yaml

from .base import (
    GitBackend, Repository, User, Group,
    Visibility, AccessLevel, BackendError
)
from .factory import get_backend, BackendFactory
from .config import BackendConfig


class GitLabCompatibilityAdapter:
    """
    Adapter that mimics the existing GitLab module interface.
    
    This class provides the same methods and signatures as the existing
    franklin.gitlab module, but uses the new backend system internally.
    """
    
    def __init__(self, backend: Optional[GitBackend] = None):
        """
        Initialize the adapter with a backend.
        
        Parameters
        ----------
        backend : Optional[GitBackend]
            Backend to use. If None, loads from configuration.
        """
        self.backend = backend or get_backend()
        self._gl = None  # Compatibility attribute
        self._config = {}
        
        # Try to authenticate if credentials are available
        self._auto_authenticate()
    
    def _auto_authenticate(self):
        """Attempt automatic authentication using available credentials."""
        if self.backend.is_authenticated:
            return
        
        # Try to get token from environment or config
        token = None
        if hasattr(self.backend, 'token'):
            token = self.backend.token
        elif 'GITLAB_TOKEN' in os.environ:
            token = os.environ['GITLAB_TOKEN']
        elif 'FRANKLIN_GIT_TOKEN' in os.environ:
            token = os.environ['FRANKLIN_GIT_TOKEN']
        
        if token:
            try:
                self.backend.authenticate({'token': token})
            except:
                pass  # Silent fail for auto-auth
    
    # GitLab-specific properties for compatibility
    @property
    def url(self) -> str:
        """Get GitLab URL for compatibility."""
        if hasattr(self.backend, 'url'):
            return self.backend.url
        return 'https://gitlab.com'
    
    @property
    def token(self) -> Optional[str]:
        """Get token for compatibility."""
        if hasattr(self.backend, 'token'):
            return self.backend.token
        return None
    
    @property
    def gl(self):
        """Get GitLab client for compatibility with code that accesses gl directly."""
        if self._gl is None and hasattr(self.backend, 'gl'):
            self._gl = self.backend.gl
        return self._gl
    
    # Project/Repository methods (maintaining GitLab naming)
    def create_project(self, name: str, **kwargs) -> Dict[str, Any]:
        """
        Create a project (GitLab terminology for repository).
        
        Maintains compatibility with existing create_project calls.
        """
        # Map GitLab-specific parameters to backend-agnostic ones
        repo_kwargs = self._map_project_kwargs(kwargs)
        repo = self.backend.create_repository(name, **repo_kwargs)
        return self._repository_to_project(repo)
    
    def get_project(self, project_id: Union[str, int]) -> Dict[str, Any]:
        """Get project by ID or path."""
        repo = self.backend.get_repository(str(project_id))
        return self._repository_to_project(repo)
    
    def delete_project(self, project_id: Union[str, int]) -> bool:
        """Delete a project."""
        return self.backend.delete_repository(str(project_id))
    
    def list_projects(self, **kwargs) -> List[Dict[str, Any]]:
        """List projects with GitLab-style filters."""
        # Map GitLab filters to backend filters
        backend_filters = {}
        if 'owned' in kwargs:
            backend_filters['owned'] = kwargs['owned']
        if 'visibility' in kwargs:
            backend_filters['visibility'] = kwargs['visibility']
        if 'search' in kwargs:
            backend_filters['search'] = kwargs['search']
        if 'archived' in kwargs:
            backend_filters['archived'] = kwargs['archived']
        
        repos = self.backend.list_repositories(**backend_filters)
        return [self._repository_to_project(r) for r in repos]
    
    def fork_project(self, project_id: Union[str, int], **kwargs) -> Dict[str, Any]:
        """Fork a project."""
        repo = self.backend.fork_repository(str(project_id), **kwargs)
        return self._repository_to_project(repo)
    
    # User methods
    def get_user(self, user_id: Optional[Union[str, int]] = None) -> Dict[str, Any]:
        """Get user (current user if no ID provided)."""
        if user_id is None:
            user = self.backend.get_current_user()
        else:
            user = self.backend.get_user(str(user_id))
        return self._user_to_gitlab_user(user)
    
    def list_users(self, **kwargs) -> List[Dict[str, Any]]:
        """List users."""
        users = self.backend.list_users(**kwargs)
        return [self._user_to_gitlab_user(u) for u in users]
    
    def create_user(self, username: str, email: str, name: str, 
                    password: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Create a user (GitLab only)."""
        if not self.backend.capabilities.create_users:
            raise NotImplementedError("Current backend doesn't support user creation")
        
        user_data = {
            'username': username,
            'email': email,
            'name': name,
            'password': password,
            **kwargs
        }
        user = self.backend.create_user(user_data)
        return self._user_to_gitlab_user(user)
    
    # Group methods
    def create_group(self, name: str, path: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Create a group."""
        if path:
            kwargs['path'] = path
        group = self.backend.create_group(name, **kwargs)
        return self._group_to_gitlab_group(group)
    
    def get_group(self, group_id: Union[str, int]) -> Dict[str, Any]:
        """Get group."""
        group = self.backend.get_group(str(group_id))
        return self._group_to_gitlab_group(group)
    
    def list_groups(self, **kwargs) -> List[Dict[str, Any]]:
        """List groups."""
        groups = self.backend.list_groups(**kwargs)
        return [self._group_to_gitlab_group(g) for g in groups]
    
    def add_group_member(self, group_id: Union[str, int], user_id: Union[str, int],
                        access_level: int = 30) -> bool:
        """Add member to group with GitLab access level."""
        # Convert numeric GitLab access level to enum
        access = self._convert_access_level(access_level)
        return self.backend.add_user_to_group(str(group_id), str(user_id), access)
    
    # File operations
    def get_file(self, project_id: Union[str, int], file_path: str, 
                ref: str = 'main') -> Dict[str, Any]:
        """Get file from project."""
        content = self.backend.get_file_content(str(project_id), file_path, ref)
        
        # Return GitLab-style file object
        import base64
        return {
            'file_path': file_path,
            'file_name': Path(file_path).name,
            'size': len(content),
            'encoding': 'base64',
            'content': base64.b64encode(content).decode('utf-8'),
            'ref': ref,
        }
    
    def create_file(self, project_id: Union[str, int], file_path: str,
                   content: Union[str, bytes], commit_message: str,
                   branch: str = 'main', **kwargs) -> Dict[str, Any]:
        """Create file in project."""
        return self.backend.create_file(
            str(project_id), file_path, content, commit_message, branch, **kwargs
        )
    
    def update_file(self, project_id: Union[str, int], file_path: str,
                   content: Union[str, bytes], commit_message: str,
                   branch: str = 'main', **kwargs) -> Dict[str, Any]:
        """Update file in project."""
        return self.backend.update_file(
            str(project_id), file_path, content, commit_message, branch, **kwargs
        )
    
    def delete_file(self, project_id: Union[str, int], file_path: str,
                   commit_message: str, branch: str = 'main', **kwargs) -> Dict[str, Any]:
        """Delete file from project."""
        return self.backend.delete_file(
            str(project_id), file_path, commit_message, branch, **kwargs
        )
    
    # Merge request methods
    def create_merge_request(self, project_id: Union[str, int], source_branch: str,
                           target_branch: str, title: str, **kwargs) -> Dict[str, Any]:
        """Create merge request."""
        mr = self.backend.create_merge_request(
            str(project_id), title, source_branch, target_branch, **kwargs
        )
        return self._merge_request_to_gitlab_mr(mr)
    
    def get_merge_request(self, project_id: Union[str, int], 
                         mr_iid: Union[str, int]) -> Dict[str, Any]:
        """Get merge request."""
        mr = self.backend.get_merge_request(str(project_id), str(mr_iid))
        return self._merge_request_to_gitlab_mr(mr)
    
    def list_merge_requests(self, project_id: Union[str, int], **kwargs) -> List[Dict[str, Any]]:
        """List merge requests."""
        mrs = self.backend.list_merge_requests(str(project_id), **kwargs)
        return [self._merge_request_to_gitlab_mr(mr) for mr in mrs]
    
    # Clone/Git operations
    def clone_project(self, project_id: Union[str, int], target_dir: Optional[Path] = None,
                     use_ssh: bool = False) -> Path:
        """Clone a project to local directory."""
        repo = self.backend.get_repository(str(project_id))
        
        # Determine target directory
        if target_dir is None:
            target_dir = Path.cwd() / repo.name
        
        # Get clone URL
        clone_url = repo.ssh_url if use_ssh else repo.clone_url
        
        # Add authentication to HTTPS URL if needed
        if not use_ssh and self.backend.token and 'gitlab' in clone_url:
            # Insert token into URL for GitLab
            clone_url = clone_url.replace('https://', f'https://oauth2:{self.backend.token}@')
        
        # Clone using git
        subprocess.run(['git', 'clone', clone_url, str(target_dir)], check=True)
        
        return target_dir
    
    # Conversion methods
    def _map_project_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Map GitLab project parameters to backend repository parameters."""
        mapped = {}
        
        # Direct mappings
        if 'description' in kwargs:
            mapped['description'] = kwargs['description']
        if 'visibility' in kwargs:
            mapped['visibility'] = kwargs['visibility']
        if 'namespace_id' in kwargs:
            mapped['namespace_id'] = kwargs['namespace_id']
        if 'namespace' in kwargs:
            mapped['namespace'] = kwargs['namespace']
        if 'initialize_with_readme' in kwargs:
            mapped['init_readme'] = kwargs['initialize_with_readme']
        elif 'init_readme' in kwargs:
            mapped['init_readme'] = kwargs['init_readme']
        
        # Add any other kwargs that might be backend-specific
        for key, value in kwargs.items():
            if key not in mapped:
                mapped[key] = value
        
        return mapped
    
    def _repository_to_project(self, repo: Repository) -> Dict[str, Any]:
        """Convert Repository to GitLab project format."""
        return {
            'id': repo.id,
            'name': repo.name,
            'path': repo.name,
            'path_with_namespace': repo.full_name,
            'description': repo.description,
            'http_url_to_repo': repo.clone_url,
            'ssh_url_to_repo': repo.ssh_url,
            'web_url': repo.web_url,
            'default_branch': repo.default_branch,
            'visibility': repo.visibility.value,
            'namespace': {
                'name': repo.owner,
                'path': repo.owner,
                'full_path': repo.owner,
            },
            'created_at': repo.created_at.isoformat() if repo.created_at else None,
            'last_activity_at': repo.updated_at.isoformat() if repo.updated_at else None,
            'archived': repo.archived,
            'star_count': repo.stars_count or 0,
            'forks_count': repo.forks_count or 0,
            'open_issues_count': repo.open_issues_count or 0,
            # Include original metadata if from GitLab
            **repo.metadata.get('gitlab_project', {})
        }
    
    def _user_to_gitlab_user(self, user: User) -> Dict[str, Any]:
        """Convert User to GitLab user format."""
        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'name': user.name,
            'avatar_url': user.avatar_url,
            'web_url': user.web_url,
            'bio': user.bio,
            'location': user.location,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'is_admin': user.is_admin,
            'can_create_group': user.can_create_group,
            'can_create_project': user.can_create_project,
            'two_factor_enabled': user.two_factor_enabled,
            # Include original metadata if from GitLab
            **user.metadata.get('gitlab_user', {})
        }
    
    def _group_to_gitlab_group(self, group: Group) -> Dict[str, Any]:
        """Convert Group to GitLab group format."""
        return {
            'id': group.id,
            'name': group.name,
            'path': group.name.lower().replace(' ', '-'),
            'full_path': group.full_path,
            'description': group.description,
            'visibility': group.visibility.value,
            'web_url': group.web_url,
            'avatar_url': group.avatar_url,
            'parent_id': group.parent_id,
            'created_at': group.created_at.isoformat() if group.created_at else None,
            # Include original metadata if from GitLab
            **group.metadata.get('gitlab_group', {})
        }
    
    def _merge_request_to_gitlab_mr(self, mr) -> Dict[str, Any]:
        """Convert MergeRequest to GitLab merge request format."""
        return {
            'id': mr.id,
            'iid': mr.iid,
            'title': mr.title,
            'description': mr.description,
            'state': mr.state,
            'source_branch': mr.source_branch,
            'target_branch': mr.target_branch,
            'author': self._user_to_gitlab_user(mr.author),
            'web_url': mr.web_url,
            'created_at': mr.created_at.isoformat() if mr.created_at else None,
            'updated_at': mr.updated_at.isoformat() if mr.updated_at else None,
            'merged_at': mr.merged_at.isoformat() if mr.merged_at else None,
            'draft': mr.draft,
            'work_in_progress': mr.draft,  # Compatibility
            'labels': mr.labels,
            # Include original metadata if from GitLab
            **mr.metadata.get('gitlab_mr', {})
        }
    
    def _convert_access_level(self, level: int) -> AccessLevel:
        """Convert GitLab numeric access level to AccessLevel enum."""
        if level >= 50:
            return AccessLevel.OWNER
        elif level >= 40:
            return AccessLevel.MAINTAINER
        elif level >= 30:
            return AccessLevel.DEVELOPER
        elif level >= 20:
            return AccessLevel.REPORTER
        else:
            return AccessLevel.GUEST


class ExerciseAdapter:
    """
    Adapter for exercise management operations.
    
    Provides compatibility for Franklin exercise-related operations
    with the new backend system.
    """
    
    def __init__(self, backend: Optional[GitBackend] = None):
        """Initialize with a backend."""
        self.backend = backend or get_backend()
        self.gitlab = GitLabCompatibilityAdapter(self.backend)
    
    def create_exercise(self, name: str, namespace: Optional[str] = None,
                       **kwargs) -> Dict[str, Any]:
        """Create an exercise repository."""
        # Add exercise prefix if not present
        if not name.startswith('exercise-'):
            name = f'exercise-{name}'
        
        # Create repository
        project = self.gitlab.create_project(
            name,
            namespace=namespace,
            visibility='private',
            initialize_with_readme=False,
            **kwargs
        )
        
        # Add exercise template files
        self._add_exercise_template(project['id'])
        
        return project
    
    def download_exercise(self, url: str, target_dir: Optional[Path] = None) -> Path:
        """Download an exercise from URL."""
        # Parse URL to get project ID
        project_id = self._parse_exercise_url(url)
        
        # Clone the project
        return self.gitlab.clone_project(project_id, target_dir)
    
    def submit_exercise(self, exercise_dir: Path, message: str = "Submit exercise") -> bool:
        """Submit exercise by pushing to remote."""
        # Get git remote URL
        remote_url = subprocess.check_output(
            ['git', 'remote', 'get-url', 'origin'],
            cwd=exercise_dir,
            text=True
        ).strip()
        
        # Add, commit, and push
        subprocess.run(['git', 'add', '-A'], cwd=exercise_dir, check=True)
        subprocess.run(['git', 'commit', '-m', message], cwd=exercise_dir, check=True)
        subprocess.run(['git', 'push'], cwd=exercise_dir, check=True)
        
        return True
    
    def _add_exercise_template(self, project_id: str) -> None:
        """Add template files to exercise repository."""
        # Get template directory
        template_dir = Path(__file__).parent.parent / 'data' / 'templates' / 'exercise'
        
        if template_dir.exists():
            for template_file in template_dir.glob('*'):
                if template_file.is_file():
                    with open(template_file, 'r') as f:
                        content = f.read()
                    
                    self.gitlab.create_file(
                        project_id,
                        template_file.name,
                        content,
                        f"Add {template_file.name}",
                        'main'
                    )
    
    def _parse_exercise_url(self, url: str) -> str:
        """Parse exercise URL to extract project identifier."""
        # Handle different URL formats
        if 'gitlab.com' in url or 'github.com' in url:
            # Extract owner/repo from URL
            parts = url.rstrip('/').split('/')
            if len(parts) >= 2:
                return f"{parts[-2]}/{parts[-1]}"
        
        # Assume it's already a project ID
        return url


def get_gitlab_adapter() -> GitLabCompatibilityAdapter:
    """
    Get a GitLab compatibility adapter instance.
    
    This function provides a drop-in replacement for getting a GitLab client.
    """
    return GitLabCompatibilityAdapter()


def get_exercise_adapter() -> ExerciseAdapter:
    """Get an exercise adapter instance."""
    return ExerciseAdapter()


# Module-level instance for import compatibility
# This allows: from franklin.gitlab_adapter import gitlab
gitlab = GitLabCompatibilityAdapter()


# Compatibility functions that mimic existing GitLab module functions
def authenticate(token: Optional[str] = None, url: str = 'https://gitlab.com') -> bool:
    """Authenticate with GitLab (compatibility function)."""
    global gitlab
    
    # If URL is different, create new backend
    if hasattr(gitlab.backend, 'url') and gitlab.backend.url != url:
        from .gitlab_backend import GitLabBackend
        gitlab.backend = GitLabBackend(url=url, token=token)
    
    return gitlab.backend.authenticate({'token': token or gitlab.token})


def get_project(project_id: Union[str, int]) -> Dict[str, Any]:
    """Get project (compatibility function)."""
    return gitlab.get_project(project_id)


def create_project(name: str, **kwargs) -> Dict[str, Any]:
    """Create project (compatibility function)."""
    return gitlab.create_project(name, **kwargs)


def list_projects(**kwargs) -> List[Dict[str, Any]]:
    """List projects (compatibility function)."""
    return gitlab.list_projects(**kwargs)


def get_user(user_id: Optional[Union[str, int]] = None) -> Dict[str, Any]:
    """Get user (compatibility function)."""
    return gitlab.get_user(user_id)


def clone_project(project_id: Union[str, int], target_dir: Optional[Path] = None) -> Path:
    """Clone project (compatibility function)."""
    return gitlab.clone_project(project_id, target_dir)
"""
GitLab backend implementation.

This module provides a GitLab implementation of the GitBackend interface,
wrapping the existing GitLab functionality in Franklin.
"""

import os
import sys
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import existing franklin modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from .base import (
    GitBackend, Repository, User, Group, MergeRequest,
    BackendCapabilities, Visibility, AccessLevel,
    BackendError, AuthenticationError, RepositoryNotFoundError,
    UserNotFoundError, BackendPermissionError
)


class GitLabBackend(GitBackend):
    """GitLab implementation of GitBackend interface."""
    
    def __init__(self, url: str = "https://gitlab.com", token: Optional[str] = None):
        """
        Initialize GitLab backend.
        
        Parameters
        ----------
        url : str
            GitLab instance URL
        token : Optional[str]
            Personal access token
        """
        super().__init__()
        self.url = url.rstrip('/')
        self.token = token
        self.gl = None  # GitLab API client
        
        # Set GitLab-specific capabilities
        self._capabilities = BackendCapabilities(
            create_users=True,  # GitLab supports user creation
            create_groups=True,
            nested_groups=True,  # GitLab supports nested groups
            fork_repository=True,
            protected_branches=True,
            merge_requests=True,
            ci_cd=True,
            webhooks=True,
            deploy_keys=True,
            issues=True,
            wiki=True,
            snippets=True,  # GitLab has snippets
            packages=True,  # GitLab has package registry
            pages=True,  # GitLab Pages
        )
    
    def authenticate(self, credentials: Dict[str, str]) -> bool:
        """Authenticate with GitLab using token or OAuth."""
        try:
            # Import GitLab module
            import gitlab
            
            # Get token from credentials or instance
            token = credentials.get('token', self.token)
            if not token:
                raise AuthenticationError("No GitLab token provided")
            
            # Create GitLab client
            self.gl = gitlab.Gitlab(self.url, private_token=token)
            
            # Test authentication
            self.gl.auth()
            self._authenticated = True
            self.token = token
            
            return True
            
        except ImportError:
            raise BackendError("python-gitlab package not installed")
        except gitlab.exceptions.GitlabAuthenticationError as e:
            raise AuthenticationError(f"GitLab authentication failed: {e}")
        except Exception as e:
            raise BackendError(f"Failed to authenticate with GitLab: {e}")
    
    def verify_authentication(self) -> bool:
        """Verify that current authentication is still valid."""
        if not self.gl:
            return False
        
        try:
            # Try to get current user as authentication test
            self.gl.user
            return True
        except Exception:
            return False
    
    # Repository Operations
    def create_repository(self, name: str, **kwargs) -> Repository:
        """Create a new GitLab project."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            # Map kwargs to GitLab project attributes
            visibility = kwargs.get('visibility', 'private')
            if isinstance(visibility, Visibility):
                visibility = visibility.value
            
            project_data = {
                'name': name,
                'visibility': visibility,
                'description': kwargs.get('description', ''),
                'initialize_with_readme': kwargs.get('init_readme', True),
            }
            
            # Add namespace if provided
            if 'namespace_id' in kwargs:
                project_data['namespace_id'] = kwargs['namespace_id']
            elif 'namespace' in kwargs:
                project_data['namespace_id'] = self._get_namespace_id(kwargs['namespace'])
            
            # Create project
            project = self.gl.projects.create(project_data)
            
            return self._convert_project_to_repository(project)
            
        except Exception as e:
            raise BackendError(f"Failed to create repository: {e}")
    
    def get_repository(self, repo_id: str) -> Repository:
        """Get GitLab project information."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            project = self.gl.projects.get(repo_id)
            return self._convert_project_to_repository(project)
        except self.gl.exceptions.GitlabGetError:
            raise RepositoryNotFoundError(f"Repository '{repo_id}' not found")
        except Exception as e:
            raise BackendError(f"Failed to get repository: {e}")
    
    def update_repository(self, repo_id: str, **kwargs) -> Repository:
        """Update GitLab project settings."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            project = self.gl.projects.get(repo_id)
            
            # Update allowed fields
            if 'name' in kwargs:
                project.name = kwargs['name']
            if 'description' in kwargs:
                project.description = kwargs['description']
            if 'visibility' in kwargs:
                visibility = kwargs['visibility']
                if isinstance(visibility, Visibility):
                    visibility = visibility.value
                project.visibility = visibility
            if 'default_branch' in kwargs:
                project.default_branch = kwargs['default_branch']
            if 'archived' in kwargs:
                project.archived = kwargs['archived']
            
            project.save()
            return self._convert_project_to_repository(project)
            
        except Exception as e:
            raise BackendError(f"Failed to update repository: {e}")
    
    def delete_repository(self, repo_id: str) -> bool:
        """Delete a GitLab project."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            project = self.gl.projects.get(repo_id)
            project.delete()
            return True
        except Exception as e:
            raise BackendError(f"Failed to delete repository: {e}")
    
    def list_repositories(self, **filters) -> List[Repository]:
        """List GitLab projects with filters."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            # Map filters to GitLab API parameters
            params = {}
            
            if 'owned' in filters and filters['owned']:
                params['owned'] = True
            if 'visibility' in filters:
                visibility = filters['visibility']
                if isinstance(visibility, Visibility):
                    visibility = visibility.value
                params['visibility'] = visibility
            if 'search' in filters:
                params['search'] = filters['search']
            if 'archived' in filters:
                params['archived'] = filters['archived']
            
            # Get projects
            projects = self.gl.projects.list(all=True, **params)
            
            return [self._convert_project_to_repository(p) for p in projects]
            
        except Exception as e:
            raise BackendError(f"Failed to list repositories: {e}")
    
    def fork_repository(self, repo_id: str, **kwargs) -> Repository:
        """Fork a GitLab project."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            # Get source project
            source_project = self.gl.projects.get(repo_id)
            
            # Fork the project
            fork_data = {}
            if 'namespace' in kwargs:
                fork_data['namespace_id'] = self._get_namespace_id(kwargs['namespace'])
            if 'name' in kwargs:
                fork_data['name'] = kwargs['name']
            if 'path' in kwargs:
                fork_data['path'] = kwargs['path']
            
            forked_project = source_project.forks.create(fork_data)
            
            # Get the full project object
            forked_project = self.gl.projects.get(forked_project.id)
            
            return self._convert_project_to_repository(forked_project)
            
        except Exception as e:
            raise BackendError(f"Failed to fork repository: {e}")
    
    # User Operations
    def get_current_user(self) -> User:
        """Get current authenticated GitLab user."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            user = self.gl.user
            return self._convert_gitlab_user_to_user(user)
        except Exception as e:
            raise BackendError(f"Failed to get current user: {e}")
    
    def get_user(self, user_id: str) -> User:
        """Get GitLab user information."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            user = self.gl.users.get(user_id)
            return self._convert_gitlab_user_to_user(user)
        except self.gl.exceptions.GitlabGetError:
            raise UserNotFoundError(f"User '{user_id}' not found")
        except Exception as e:
            raise BackendError(f"Failed to get user: {e}")
    
    def list_users(self, **filters) -> List[User]:
        """List GitLab users with filters."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            params = {}
            
            if 'search' in filters:
                params['search'] = filters['search']
            if 'active' in filters:
                params['active'] = filters['active']
            if 'blocked' in filters:
                params['blocked'] = filters['blocked']
            
            users = self.gl.users.list(all=True, **params)
            return [self._convert_gitlab_user_to_user(u) for u in users]
            
        except Exception as e:
            raise BackendError(f"Failed to list users: {e}")
    
    def _create_user_impl(self, user_data: Dict[str, Any]) -> User:
        """Create a new GitLab user (admin only)."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            # Map user data to GitLab format
            gitlab_user_data = {
                'email': user_data['email'],
                'username': user_data['username'],
                'name': user_data.get('name', user_data['username']),
                'password': user_data.get('password'),
                'skip_confirmation': user_data.get('skip_confirmation', True),
            }
            
            user = self.gl.users.create(gitlab_user_data)
            return self._convert_gitlab_user_to_user(user)
            
        except Exception as e:
            raise BackendError(f"Failed to create user: {e}")
    
    # Group Operations
    def create_group(self, name: str, **kwargs) -> Group:
        """Create a GitLab group."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            group_data = {
                'name': name,
                'path': kwargs.get('path', name.lower().replace(' ', '-')),
                'description': kwargs.get('description', ''),
            }
            
            if 'visibility' in kwargs:
                visibility = kwargs['visibility']
                if isinstance(visibility, Visibility):
                    visibility = visibility.value
                group_data['visibility'] = visibility
            
            if 'parent_id' in kwargs:
                group_data['parent_id'] = kwargs['parent_id']
            
            group = self.gl.groups.create(group_data)
            return self._convert_gitlab_group_to_group(group)
            
        except Exception as e:
            raise BackendError(f"Failed to create group: {e}")
    
    def get_group(self, group_id: str) -> Group:
        """Get GitLab group information."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            group = self.gl.groups.get(group_id)
            return self._convert_gitlab_group_to_group(group)
        except Exception as e:
            raise BackendError(f"Failed to get group: {e}")
    
    def list_groups(self, **filters) -> List[Group]:
        """List GitLab groups with filters."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            params = {}
            
            if 'search' in filters:
                params['search'] = filters['search']
            if 'owned' in filters:
                params['owned'] = filters['owned']
            
            groups = self.gl.groups.list(all=True, **params)
            return [self._convert_gitlab_group_to_group(g) for g in groups]
            
        except Exception as e:
            raise BackendError(f"Failed to list groups: {e}")
    
    def add_user_to_group(self, group_id: str, user_id: str,
                         access_level: AccessLevel = AccessLevel.DEVELOPER) -> bool:
        """Add user to GitLab group."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            group = self.gl.groups.get(group_id)
            group.members.create({'user_id': user_id, 'access_level': access_level.value})
            return True
        except Exception as e:
            raise BackendError(f"Failed to add user to group: {e}")
    
    def remove_user_from_group(self, group_id: str, user_id: str) -> bool:
        """Remove user from GitLab group."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            group = self.gl.groups.get(group_id)
            group.members.delete(user_id)
            return True
        except Exception as e:
            raise BackendError(f"Failed to remove user from group: {e}")
    
    # File Operations
    def get_file_content(self, repo_id: str, file_path: str, ref: str = 'main') -> bytes:
        """Get file content from GitLab repository."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            project = self.gl.projects.get(repo_id)
            file = project.files.get(file_path, ref=ref)
            
            # Decode content (GitLab returns base64 encoded)
            import base64
            return base64.b64decode(file.content)
            
        except Exception as e:
            raise BackendError(f"Failed to get file content: {e}")
    
    def create_file(self, repo_id: str, file_path: str, content: Union[str, bytes],
                   message: str, branch: str = 'main', **kwargs) -> Dict[str, Any]:
        """Create file in GitLab repository."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            project = self.gl.projects.get(repo_id)
            
            # Encode content if bytes
            if isinstance(content, bytes):
                import base64
                content = base64.b64encode(content).decode('utf-8')
                encoding = 'base64'
            else:
                encoding = 'text'
            
            file_data = {
                'file_path': file_path,
                'branch': branch,
                'content': content,
                'commit_message': message,
                'encoding': encoding,
            }
            
            if 'author_email' in kwargs:
                file_data['author_email'] = kwargs['author_email']
            if 'author_name' in kwargs:
                file_data['author_name'] = kwargs['author_name']
            
            result = project.files.create(file_data)
            return {'file_path': result['file_path'], 'branch': branch}
            
        except Exception as e:
            raise BackendError(f"Failed to create file: {e}")
    
    def update_file(self, repo_id: str, file_path: str, content: Union[str, bytes],
                   message: str, branch: str = 'main', **kwargs) -> Dict[str, Any]:
        """Update file in GitLab repository."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            project = self.gl.projects.get(repo_id)
            file = project.files.get(file_path, ref=branch)
            
            # Encode content if bytes
            if isinstance(content, bytes):
                import base64
                content = base64.b64encode(content).decode('utf-8')
                encoding = 'base64'
            else:
                encoding = 'text'
            
            file.content = content
            file.encoding = encoding
            file.commit_message = message
            
            if 'author_email' in kwargs:
                file.author_email = kwargs['author_email']
            if 'author_name' in kwargs:
                file.author_name = kwargs['author_name']
            
            file.save(branch=branch)
            return {'file_path': file_path, 'branch': branch}
            
        except Exception as e:
            raise BackendError(f"Failed to update file: {e}")
    
    def delete_file(self, repo_id: str, file_path: str, message: str,
                   branch: str = 'main', **kwargs) -> Dict[str, Any]:
        """Delete file from GitLab repository."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            project = self.gl.projects.get(repo_id)
            project.files.delete(file_path, commit_message=message, branch=branch)
            return {'file_path': file_path, 'branch': branch}
            
        except Exception as e:
            raise BackendError(f"Failed to delete file: {e}")
    
    # Merge Request Operations
    def create_merge_request(self, repo_id: str, title: str, source_branch: str,
                           target_branch: str = 'main', **kwargs) -> MergeRequest:
        """Create GitLab merge request."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            project = self.gl.projects.get(repo_id)
            
            mr_data = {
                'source_branch': source_branch,
                'target_branch': target_branch,
                'title': title,
            }
            
            if 'description' in kwargs:
                mr_data['description'] = kwargs['description']
            if 'assignee_id' in kwargs:
                mr_data['assignee_id'] = kwargs['assignee_id']
            if 'labels' in kwargs:
                mr_data['labels'] = kwargs['labels']
            
            mr = project.mergerequests.create(mr_data)
            return self._convert_gitlab_mr_to_merge_request(mr)
            
        except Exception as e:
            raise BackendError(f"Failed to create merge request: {e}")
    
    def get_merge_request(self, repo_id: str, mr_id: str) -> MergeRequest:
        """Get GitLab merge request information."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            project = self.gl.projects.get(repo_id)
            mr = project.mergerequests.get(mr_id)
            return self._convert_gitlab_mr_to_merge_request(mr)
        except Exception as e:
            raise BackendError(f"Failed to get merge request: {e}")
    
    def list_merge_requests(self, repo_id: str, **filters) -> List[MergeRequest]:
        """List GitLab merge requests."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            project = self.gl.projects.get(repo_id)
            
            params = {}
            if 'state' in filters:
                params['state'] = filters['state']
            if 'author_id' in filters:
                params['author_id'] = filters['author_id']
            if 'assignee_id' in filters:
                params['assignee_id'] = filters['assignee_id']
            
            mrs = project.mergerequests.list(all=True, **params)
            return [self._convert_gitlab_mr_to_merge_request(mr) for mr in mrs]
            
        except Exception as e:
            raise BackendError(f"Failed to list merge requests: {e}")
    
    # Helper Methods
    def _convert_project_to_repository(self, project) -> Repository:
        """Convert GitLab project to Repository model."""
        # Parse timestamps
        created_at = datetime.fromisoformat(project.created_at.replace('Z', '+00:00'))
        updated_at = datetime.fromisoformat(project.last_activity_at.replace('Z', '+00:00'))
        
        return Repository(
            id=str(project.id),
            name=project.name,
            full_name=project.path_with_namespace,
            description=project.description or "",
            clone_url=project.http_url_to_repo,
            ssh_url=project.ssh_url_to_repo,
            web_url=project.web_url,
            default_branch=project.default_branch or 'main',
            visibility=self.normalize_visibility(project.visibility),
            owner=project.namespace['name'],
            created_at=created_at,
            updated_at=updated_at,
            size=project.statistics.get('repository_size', 0) if hasattr(project, 'statistics') else None,
            stars_count=project.star_count,
            forks_count=project.forks_count,
            open_issues_count=project.open_issues_count if hasattr(project, 'open_issues_count') else 0,
            archived=project.archived if hasattr(project, 'archived') else False,
            metadata={'gitlab_project': project.attributes}
        )
    
    def _convert_gitlab_user_to_user(self, gitlab_user) -> User:
        """Convert GitLab user to User model."""
        created_at = None
        if hasattr(gitlab_user, 'created_at'):
            created_at = datetime.fromisoformat(gitlab_user.created_at.replace('Z', '+00:00'))
        
        return User(
            id=str(gitlab_user.id),
            username=gitlab_user.username,
            email=gitlab_user.email if hasattr(gitlab_user, 'email') else None,
            name=gitlab_user.name,
            avatar_url=gitlab_user.avatar_url if hasattr(gitlab_user, 'avatar_url') else None,
            web_url=gitlab_user.web_url,
            bio=gitlab_user.bio if hasattr(gitlab_user, 'bio') else None,
            location=gitlab_user.location if hasattr(gitlab_user, 'location') else None,
            created_at=created_at,
            is_admin=gitlab_user.is_admin if hasattr(gitlab_user, 'is_admin') else False,
            can_create_group=gitlab_user.can_create_group if hasattr(gitlab_user, 'can_create_group') else False,
            can_create_project=gitlab_user.can_create_project if hasattr(gitlab_user, 'can_create_project') else False,
            two_factor_enabled=gitlab_user.two_factor_enabled if hasattr(gitlab_user, 'two_factor_enabled') else None,
            metadata={'gitlab_user': gitlab_user.attributes if hasattr(gitlab_user, 'attributes') else {}}
        )
    
    def _convert_gitlab_group_to_group(self, gitlab_group) -> Group:
        """Convert GitLab group to Group model."""
        created_at = None
        if hasattr(gitlab_group, 'created_at'):
            created_at = datetime.fromisoformat(gitlab_group.created_at.replace('Z', '+00:00'))
        
        return Group(
            id=str(gitlab_group.id),
            name=gitlab_group.name,
            full_path=gitlab_group.full_path,
            description=gitlab_group.description or "",
            web_url=gitlab_group.web_url,
            avatar_url=gitlab_group.avatar_url if hasattr(gitlab_group, 'avatar_url') else None,
            visibility=self.normalize_visibility(gitlab_group.visibility),
            parent_id=str(gitlab_group.parent_id) if hasattr(gitlab_group, 'parent_id') and gitlab_group.parent_id else None,
            created_at=created_at,
            members_count=len(gitlab_group.members.list()) if hasattr(gitlab_group, 'members') else 0,
            projects_count=len(gitlab_group.projects.list()) if hasattr(gitlab_group, 'projects') else 0,
            subgroups_count=len(gitlab_group.subgroups.list()) if hasattr(gitlab_group, 'subgroups') else 0,
            metadata={'gitlab_group': gitlab_group.attributes if hasattr(gitlab_group, 'attributes') else {}}
        )
    
    def _convert_gitlab_mr_to_merge_request(self, gitlab_mr) -> MergeRequest:
        """Convert GitLab merge request to MergeRequest model."""
        # Parse timestamps
        created_at = datetime.fromisoformat(gitlab_mr.created_at.replace('Z', '+00:00'))
        updated_at = datetime.fromisoformat(gitlab_mr.updated_at.replace('Z', '+00:00'))
        merged_at = None
        if gitlab_mr.merged_at:
            merged_at = datetime.fromisoformat(gitlab_mr.merged_at.replace('Z', '+00:00'))
        
        # Convert author
        author = User(
            id=str(gitlab_mr.author['id']),
            username=gitlab_mr.author['username'],
            name=gitlab_mr.author['name'],
            email=None,
            avatar_url=gitlab_mr.author.get('avatar_url'),
            web_url=gitlab_mr.author.get('web_url', ''),
        )
        
        return MergeRequest(
            id=str(gitlab_mr.id),
            iid=str(gitlab_mr.iid),
            title=gitlab_mr.title,
            description=gitlab_mr.description,
            state=gitlab_mr.state,
            source_branch=gitlab_mr.source_branch,
            target_branch=gitlab_mr.target_branch,
            author=author,
            web_url=gitlab_mr.web_url,
            created_at=created_at,
            updated_at=updated_at,
            merged_at=merged_at,
            draft=gitlab_mr.draft if hasattr(gitlab_mr, 'draft') else gitlab_mr.work_in_progress,
            labels=gitlab_mr.labels,
            metadata={'gitlab_mr': gitlab_mr.attributes}
        )
    
    def _get_namespace_id(self, namespace: str) -> int:
        """Get namespace ID from namespace path or name."""
        try:
            # Try to get group by path
            group = self.gl.groups.get(namespace)
            return group.id
        except:
            # Try to find in user's namespaces
            user = self.gl.user
            if user.username == namespace:
                return user.namespace['id']
            
            # Search for namespace
            groups = self.gl.groups.list(search=namespace)
            if groups:
                return groups[0].id
            
            raise BackendError(f"Namespace '{namespace}' not found")
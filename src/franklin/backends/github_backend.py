"""
GitHub backend implementation.

This module provides a GitHub implementation of the GitBackend interface,
using the PyGithub library to interact with GitHub's API.
"""

import os
import base64
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pathlib import Path

from .base import (
    GitBackend, Repository, User, Group, MergeRequest,
    BackendCapabilities, Visibility, AccessLevel,
    BackendError, AuthenticationError, RepositoryNotFoundError,
    UserNotFoundError, BackendPermissionError
)


class GitHubBackend(GitBackend):
    """GitHub implementation of GitBackend interface."""
    
    def __init__(self, token: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize GitHub backend.
        
        Parameters
        ----------
        token : Optional[str]
            Personal access token or GitHub App token
        base_url : Optional[str]
            GitHub Enterprise base URL (if not using github.com)
        """
        super().__init__()
        self.token = token
        self.base_url = base_url  # For GitHub Enterprise
        self.gh = None  # GitHub client
        self.current_user = None  # Cached current user
        
        # Set GitHub-specific capabilities
        self._capabilities = BackendCapabilities(
            create_users=False,  # GitHub doesn't support user creation via API
            create_groups=True,  # Organizations can be created
            nested_groups=False,  # No nested organizations
            fork_repository=True,
            protected_branches=True,
            merge_requests=True,  # Pull requests
            ci_cd=True,  # GitHub Actions
            webhooks=True,
            deploy_keys=True,
            issues=True,
            wiki=True,
            snippets=True,  # Gists
            packages=True,  # GitHub Packages
            pages=True,  # GitHub Pages
        )
    
    def authenticate(self, credentials: Dict[str, str]) -> bool:
        """Authenticate with GitHub using token."""
        try:
            # Import GitHub module
            from github import Github, GithubException
            
            # Get token from credentials or instance
            token = credentials.get('token', self.token)
            if not token:
                raise AuthenticationError("No GitHub token provided")
            
            # Create GitHub client
            if self.base_url:
                # GitHub Enterprise
                self.gh = Github(base_url=self.base_url, login_or_token=token)
            else:
                # GitHub.com
                self.gh = Github(login_or_token=token)
            
            # Test authentication by getting current user
            self.current_user = self.gh.get_user()
            _ = self.current_user.login  # Force API call
            
            self._authenticated = True
            self.token = token
            
            return True
            
        except ImportError:
            raise BackendError("PyGithub package not installed. Install with: pip install PyGithub")
        except GithubException as e:
            if e.status == 401:
                raise AuthenticationError(f"GitHub authentication failed: Invalid token")
            else:
                raise AuthenticationError(f"GitHub authentication failed: {e}")
        except Exception as e:
            raise BackendError(f"Failed to authenticate with GitHub: {e}")
    
    def verify_authentication(self) -> bool:
        """Verify that current authentication is still valid."""
        if not self.gh:
            return False
        
        try:
            # Try to get current user as authentication test
            user = self.gh.get_user()
            _ = user.login
            return True
        except Exception:
            return False
    
    # Repository Operations
    def create_repository(self, name: str, **kwargs) -> Repository:
        """Create a new GitHub repository."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            from github import GithubException
            
            # Determine where to create the repository
            org_name = kwargs.get('organization') or kwargs.get('org')
            namespace = kwargs.get('namespace')
            
            # Map visibility
            visibility = kwargs.get('visibility', 'private')
            if isinstance(visibility, Visibility):
                visibility = visibility.value
            
            # GitHub uses 'private' boolean instead of visibility string
            private = visibility != 'public'
            
            # Prepare repository data
            repo_data = {
                'name': name,
                'private': private,
                'description': kwargs.get('description', ''),
                'auto_init': kwargs.get('init_readme', True),
                'gitignore_template': kwargs.get('gitignore_template'),
                'license_template': kwargs.get('license_template'),
            }
            
            # Remove None values
            repo_data = {k: v for k, v in repo_data.items() if v is not None}
            
            # Create in organization or user account
            if org_name or namespace:
                org_name = org_name or namespace
                org = self.gh.get_organization(org_name)
                repo = org.create_repo(**repo_data)
            else:
                # Create in user's account
                user = self.gh.get_user()
                repo = user.create_repo(**repo_data)
            
            return self._convert_github_repo_to_repository(repo)
            
        except GithubException as e:
            if e.status == 422:
                raise BackendError(f"Repository '{name}' already exists or invalid name")
            else:
                raise BackendError(f"Failed to create repository: {e}")
        except Exception as e:
            raise BackendError(f"Failed to create repository: {e}")
    
    def get_repository(self, repo_id: str) -> Repository:
        """Get GitHub repository information."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            # repo_id can be numeric ID or full name (owner/repo)
            if '/' in str(repo_id):
                repo = self.gh.get_repo(repo_id)
            else:
                # Try to get by ID
                repo = self.gh.get_repo(int(repo_id))
            
            return self._convert_github_repo_to_repository(repo)
            
        except ValueError:
            raise RepositoryNotFoundError(f"Invalid repository ID: '{repo_id}'")
        except Exception as e:
            if '404' in str(e):
                raise RepositoryNotFoundError(f"Repository '{repo_id}' not found")
            raise BackendError(f"Failed to get repository: {e}")
    
    def update_repository(self, repo_id: str, **kwargs) -> Repository:
        """Update GitHub repository settings."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            repo = self.gh.get_repo(repo_id) if '/' in str(repo_id) else self.gh.get_repo(int(repo_id))
            
            # Update allowed fields
            if 'name' in kwargs:
                repo.edit(name=kwargs['name'])
            if 'description' in kwargs:
                repo.edit(description=kwargs['description'])
            if 'visibility' in kwargs:
                visibility = kwargs['visibility']
                if isinstance(visibility, Visibility):
                    visibility = visibility.value
                private = visibility != 'public'
                repo.edit(private=private)
            if 'default_branch' in kwargs:
                repo.edit(default_branch=kwargs['default_branch'])
            if 'archived' in kwargs:
                repo.edit(archived=kwargs['archived'])
            if 'homepage' in kwargs:
                repo.edit(homepage=kwargs['homepage'])
            
            # Refresh repo data
            repo = self.gh.get_repo(repo.full_name)
            return self._convert_github_repo_to_repository(repo)
            
        except Exception as e:
            raise BackendError(f"Failed to update repository: {e}")
    
    def delete_repository(self, repo_id: str) -> bool:
        """Delete a GitHub repository."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            repo = self.gh.get_repo(repo_id) if '/' in str(repo_id) else self.gh.get_repo(int(repo_id))
            repo.delete()
            return True
        except Exception as e:
            if '404' in str(e):
                raise RepositoryNotFoundError(f"Repository '{repo_id}' not found")
            raise BackendError(f"Failed to delete repository: {e}")
    
    def list_repositories(self, **filters) -> List[Repository]:
        """List GitHub repositories with filters."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            repos = []
            
            # Determine what to list
            if filters.get('organization') or filters.get('org'):
                # List organization repositories
                org_name = filters.get('organization') or filters.get('org')
                org = self.gh.get_organization(org_name)
                repo_list = org.get_repos()
            elif filters.get('user'):
                # List specific user's repositories
                user = self.gh.get_user(filters['user'])
                repo_list = user.get_repos()
            else:
                # List authenticated user's repositories
                user = self.gh.get_user()
                if filters.get('owned'):
                    repo_list = user.get_repos(affiliation='owner')
                else:
                    repo_list = user.get_repos()
            
            # Apply filters
            for repo in repo_list:
                # Visibility filter
                if 'visibility' in filters:
                    visibility = filters['visibility']
                    if isinstance(visibility, Visibility):
                        visibility = visibility.value
                    
                    if visibility == 'public' and repo.private:
                        continue
                    elif visibility == 'private' and not repo.private:
                        continue
                
                # Archived filter
                if 'archived' in filters and repo.archived != filters['archived']:
                    continue
                
                # Search filter (simple name matching)
                if 'search' in filters:
                    search_term = filters['search'].lower()
                    if search_term not in repo.name.lower() and search_term not in (repo.description or '').lower():
                        continue
                
                repos.append(self._convert_github_repo_to_repository(repo))
            
            return repos
            
        except Exception as e:
            raise BackendError(f"Failed to list repositories: {e}")
    
    def fork_repository(self, repo_id: str, **kwargs) -> Repository:
        """Fork a GitHub repository."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            # Get source repository
            source_repo = self.gh.get_repo(repo_id) if '/' in str(repo_id) else self.gh.get_repo(int(repo_id))
            
            # Fork the repository
            org_name = kwargs.get('organization') or kwargs.get('org')
            
            if org_name:
                # Fork to organization
                org = self.gh.get_organization(org_name)
                forked_repo = org.create_fork(source_repo)
            else:
                # Fork to user account
                user = self.gh.get_user()
                forked_repo = user.create_fork(source_repo)
            
            # If custom name requested, rename after forking
            if 'name' in kwargs and kwargs['name'] != source_repo.name:
                forked_repo.edit(name=kwargs['name'])
                # Refresh repo data
                forked_repo = self.gh.get_repo(forked_repo.full_name)
            
            return self._convert_github_repo_to_repository(forked_repo)
            
        except Exception as e:
            if '404' in str(e):
                raise RepositoryNotFoundError(f"Repository '{repo_id}' not found")
            raise BackendError(f"Failed to fork repository: {e}")
    
    # User Operations
    def get_current_user(self) -> User:
        """Get current authenticated GitHub user."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            if not self.current_user:
                self.current_user = self.gh.get_user()
            return self._convert_github_user_to_user(self.current_user)
        except Exception as e:
            raise BackendError(f"Failed to get current user: {e}")
    
    def get_user(self, user_id: str) -> User:
        """Get GitHub user information."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            # user_id can be username or numeric ID
            user = self.gh.get_user(user_id)
            return self._convert_github_user_to_user(user)
        except Exception as e:
            if '404' in str(e):
                raise UserNotFoundError(f"User '{user_id}' not found")
            raise BackendError(f"Failed to get user: {e}")
    
    def list_users(self, **filters) -> List[User]:
        """List GitHub users with filters."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        # GitHub API doesn't support listing all users
        # Can only search or list organization members
        try:
            users = []
            
            if filters.get('organization') or filters.get('org'):
                # List organization members
                org_name = filters.get('organization') or filters.get('org')
                org = self.gh.get_organization(org_name)
                for member in org.get_members():
                    users.append(self._convert_github_user_to_user(member))
            elif filters.get('search'):
                # Search for users
                search_results = self.gh.search_users(filters['search'])
                for user in search_results:
                    users.append(self._convert_github_user_to_user(user))
            else:
                # Can't list all users, return current user only
                users = [self.get_current_user()]
            
            return users
            
        except Exception as e:
            raise BackendError(f"Failed to list users: {e}")
    
    # Group Operations (Organizations in GitHub)
    def create_group(self, name: str, **kwargs) -> Group:
        """Create a GitHub organization (requires special permissions)."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        # Note: Creating organizations via API requires GitHub Enterprise
        # or being an admin. Most users can't create orgs via API.
        raise NotImplementedError(
            "Creating GitHub organizations via API is restricted. "
            "Please create organizations through the GitHub web interface."
        )
    
    def get_group(self, group_id: str) -> Group:
        """Get GitHub organization information."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            org = self.gh.get_organization(group_id)
            return self._convert_github_org_to_group(org)
        except Exception as e:
            if '404' in str(e):
                raise BackendError(f"Organization '{group_id}' not found")
            raise BackendError(f"Failed to get organization: {e}")
    
    def list_groups(self, **filters) -> List[Group]:
        """List GitHub organizations."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            groups = []
            
            # List user's organizations
            user = self.gh.get_user()
            for org in user.get_orgs():
                # Apply search filter if provided
                if 'search' in filters:
                    search_term = filters['search'].lower()
                    if search_term not in org.login.lower() and search_term not in (org.name or '').lower():
                        continue
                
                groups.append(self._convert_github_org_to_group(org))
            
            return groups
            
        except Exception as e:
            raise BackendError(f"Failed to list organizations: {e}")
    
    def add_user_to_group(self, group_id: str, user_id: str,
                         access_level: AccessLevel = AccessLevel.DEVELOPER) -> bool:
        """Add user to GitHub organization."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            org = self.gh.get_organization(group_id)
            user = self.gh.get_user(user_id)
            
            # Map access level to GitHub role
            if access_level == AccessLevel.OWNER:
                # Need to use different API for owner
                org.add_to_members(user, role='admin')
            elif access_level >= AccessLevel.MAINTAINER:
                org.add_to_members(user, role='admin')
            else:
                org.add_to_members(user, role='member')
            
            return True
            
        except Exception as e:
            raise BackendError(f"Failed to add user to organization: {e}")
    
    def remove_user_from_group(self, group_id: str, user_id: str) -> bool:
        """Remove user from GitHub organization."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            org = self.gh.get_organization(group_id)
            user = self.gh.get_user(user_id)
            org.remove_from_members(user)
            return True
        except Exception as e:
            raise BackendError(f"Failed to remove user from organization: {e}")
    
    # File Operations
    def get_file_content(self, repo_id: str, file_path: str, ref: str = 'main') -> bytes:
        """Get file content from GitHub repository."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            repo = self.gh.get_repo(repo_id) if '/' in str(repo_id) else self.gh.get_repo(int(repo_id))
            
            # Try main branch if specified ref doesn't exist
            try:
                contents = repo.get_contents(file_path, ref=ref)
            except:
                # Fallback to master if main doesn't exist
                if ref == 'main':
                    contents = repo.get_contents(file_path, ref='master')
                else:
                    raise
            
            if contents.encoding == 'base64':
                return base64.b64decode(contents.content)
            else:
                return contents.content.encode('utf-8')
            
        except Exception as e:
            if '404' in str(e):
                raise BackendError(f"File '{file_path}' not found in repository")
            raise BackendError(f"Failed to get file content: {e}")
    
    def create_file(self, repo_id: str, file_path: str, content: Union[str, bytes],
                   message: str, branch: str = 'main', **kwargs) -> Dict[str, Any]:
        """Create file in GitHub repository."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            repo = self.gh.get_repo(repo_id) if '/' in str(repo_id) else self.gh.get_repo(int(repo_id))
            
            # Ensure content is string
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            
            # Try main branch, fallback to master
            try:
                result = repo.create_file(
                    path=file_path,
                    message=message,
                    content=content,
                    branch=branch
                )
            except Exception as e:
                if branch == 'main' and '404' in str(e):
                    # Try master branch
                    result = repo.create_file(
                        path=file_path,
                        message=message,
                        content=content,
                        branch='master'
                    )
                else:
                    raise
            
            return {
                'file_path': file_path,
                'branch': branch,
                'commit': result['commit'].sha
            }
            
        except Exception as e:
            if 'already exists' in str(e).lower():
                raise BackendError(f"File '{file_path}' already exists")
            raise BackendError(f"Failed to create file: {e}")
    
    def update_file(self, repo_id: str, file_path: str, content: Union[str, bytes],
                   message: str, branch: str = 'main', **kwargs) -> Dict[str, Any]:
        """Update file in GitHub repository."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            repo = self.gh.get_repo(repo_id) if '/' in str(repo_id) else self.gh.get_repo(int(repo_id))
            
            # Get current file to get its SHA
            try:
                current_file = repo.get_contents(file_path, ref=branch)
            except:
                if branch == 'main':
                    current_file = repo.get_contents(file_path, ref='master')
                    branch = 'master'
                else:
                    raise
            
            # Ensure content is string
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            
            # Update file
            result = repo.update_file(
                path=file_path,
                message=message,
                content=content,
                sha=current_file.sha,
                branch=branch
            )
            
            return {
                'file_path': file_path,
                'branch': branch,
                'commit': result['commit'].sha
            }
            
        except Exception as e:
            if '404' in str(e):
                raise BackendError(f"File '{file_path}' not found")
            raise BackendError(f"Failed to update file: {e}")
    
    def delete_file(self, repo_id: str, file_path: str, message: str,
                   branch: str = 'main', **kwargs) -> Dict[str, Any]:
        """Delete file from GitHub repository."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            repo = self.gh.get_repo(repo_id) if '/' in str(repo_id) else self.gh.get_repo(int(repo_id))
            
            # Get current file to get its SHA
            try:
                current_file = repo.get_contents(file_path, ref=branch)
            except:
                if branch == 'main':
                    current_file = repo.get_contents(file_path, ref='master')
                    branch = 'master'
                else:
                    raise
            
            # Delete file
            result = repo.delete_file(
                path=file_path,
                message=message,
                sha=current_file.sha,
                branch=branch
            )
            
            return {
                'file_path': file_path,
                'branch': branch,
                'commit': result['commit'].sha
            }
            
        except Exception as e:
            if '404' in str(e):
                raise BackendError(f"File '{file_path}' not found")
            raise BackendError(f"Failed to delete file: {e}")
    
    # Pull Request Operations (GitHub's version of Merge Requests)
    def create_merge_request(self, repo_id: str, title: str, source_branch: str,
                           target_branch: str = 'main', **kwargs) -> MergeRequest:
        """Create GitHub pull request."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            repo = self.gh.get_repo(repo_id) if '/' in str(repo_id) else self.gh.get_repo(int(repo_id))
            
            # Handle main/master branch naming
            try:
                repo.get_branch(target_branch)
            except:
                if target_branch == 'main':
                    target_branch = 'master'
            
            # Create pull request
            pr = repo.create_pull(
                title=title,
                body=kwargs.get('description', ''),
                head=source_branch,
                base=target_branch,
                draft=kwargs.get('draft', False)
            )
            
            # Add assignee if provided
            if 'assignee_id' in kwargs:
                try:
                    assignee = self.gh.get_user(kwargs['assignee_id'])
                    pr.add_to_assignees(assignee)
                except:
                    pass  # Ignore if user can't be assigned
            
            # Add labels if provided
            if 'labels' in kwargs:
                for label in kwargs['labels']:
                    try:
                        pr.add_to_labels(label)
                    except:
                        pass  # Ignore if label doesn't exist
            
            return self._convert_github_pr_to_merge_request(pr)
            
        except Exception as e:
            raise BackendError(f"Failed to create pull request: {e}")
    
    def get_merge_request(self, repo_id: str, mr_id: str) -> MergeRequest:
        """Get GitHub pull request information."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            repo = self.gh.get_repo(repo_id) if '/' in str(repo_id) else self.gh.get_repo(int(repo_id))
            pr = repo.get_pull(int(mr_id))
            return self._convert_github_pr_to_merge_request(pr)
        except Exception as e:
            if '404' in str(e):
                raise BackendError(f"Pull request '{mr_id}' not found")
            raise BackendError(f"Failed to get pull request: {e}")
    
    def list_merge_requests(self, repo_id: str, **filters) -> List[MergeRequest]:
        """List GitHub pull requests."""
        if not self._authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            repo = self.gh.get_repo(repo_id) if '/' in str(repo_id) else self.gh.get_repo(int(repo_id))
            
            # Map filters to GitHub API
            state = filters.get('state', 'open')
            if state == 'merged':
                state = 'closed'  # GitHub doesn't have 'merged' state, need to filter later
            
            pulls = repo.get_pulls(state=state)
            
            merge_requests = []
            for pr in pulls:
                # Filter merged if requested
                if filters.get('state') == 'merged' and not pr.merged:
                    continue
                
                # Filter by author
                if 'author_id' in filters:
                    if pr.user.login != filters['author_id']:
                        continue
                
                # Filter by assignee
                if 'assignee_id' in filters:
                    assignee_logins = [a.login for a in pr.assignees]
                    if filters['assignee_id'] not in assignee_logins:
                        continue
                
                merge_requests.append(self._convert_github_pr_to_merge_request(pr))
            
            return merge_requests
            
        except Exception as e:
            raise BackendError(f"Failed to list pull requests: {e}")
    
    # Helper Methods
    def _convert_github_repo_to_repository(self, github_repo) -> Repository:
        """Convert GitHub repository to Repository model."""
        return Repository(
            id=str(github_repo.id),
            name=github_repo.name,
            full_name=github_repo.full_name,
            description=github_repo.description or "",
            clone_url=github_repo.clone_url,
            ssh_url=github_repo.ssh_url,
            web_url=github_repo.html_url,
            default_branch=github_repo.default_branch,
            visibility=Visibility.PRIVATE if github_repo.private else Visibility.PUBLIC,
            owner=github_repo.owner.login,
            created_at=github_repo.created_at,
            updated_at=github_repo.updated_at,
            size=github_repo.size,
            stars_count=github_repo.stargazers_count,
            forks_count=github_repo.forks_count,
            open_issues_count=github_repo.open_issues_count,
            archived=github_repo.archived,
            disabled=getattr(github_repo, 'disabled', False),
            metadata={'github_repo': github_repo.raw_data}
        )
    
    def _convert_github_user_to_user(self, github_user) -> User:
        """Convert GitHub user to User model."""
        # Get more details if possible
        email = None
        name = None
        bio = None
        location = None
        created_at = None
        
        try:
            # These attributes might not be available for all user objects
            email = github_user.email
            name = github_user.name
            bio = github_user.bio
            location = github_user.location
            created_at = github_user.created_at
        except:
            pass  # Some attributes might not be available
        
        return User(
            id=str(github_user.id),
            username=github_user.login,
            email=email,
            name=name,
            avatar_url=github_user.avatar_url,
            web_url=github_user.html_url,
            bio=bio,
            location=location,
            created_at=created_at,
            is_admin=getattr(github_user, 'site_admin', False),
            can_create_group=True,  # Most users can create orgs
            can_create_project=True,  # All users can create repos
            two_factor_enabled=None,  # Not available via API
            metadata={'github_user': github_user.raw_data if hasattr(github_user, 'raw_data') else {}}
        )
    
    def _convert_github_org_to_group(self, github_org) -> Group:
        """Convert GitHub organization to Group model."""
        # Get member count if possible
        members_count = 0
        projects_count = 0
        
        try:
            members_count = github_org.get_members().totalCount
            projects_count = github_org.public_repos + getattr(github_org, 'total_private_repos', 0)
        except:
            pass
        
        return Group(
            id=str(github_org.id),
            name=github_org.login,
            full_path=github_org.login,
            description=github_org.description or "",
            web_url=github_org.html_url,
            avatar_url=github_org.avatar_url,
            visibility=Visibility.PUBLIC,  # Orgs are always visible
            parent_id=None,  # GitHub doesn't have nested orgs
            created_at=github_org.created_at if hasattr(github_org, 'created_at') else None,
            members_count=members_count,
            projects_count=projects_count,
            subgroups_count=0,  # No subgroups in GitHub
            metadata={'github_org': github_org.raw_data if hasattr(github_org, 'raw_data') else {}}
        )
    
    def _convert_github_pr_to_merge_request(self, github_pr) -> MergeRequest:
        """Convert GitHub pull request to MergeRequest model."""
        # Determine state
        if github_pr.merged:
            state = 'merged'
        elif github_pr.state == 'closed':
            state = 'closed'
        else:
            state = 'open'
        
        # Convert author
        author = User(
            id=str(github_pr.user.id),
            username=github_pr.user.login,
            name=None,
            email=None,
            avatar_url=github_pr.user.avatar_url,
            web_url=github_pr.user.html_url,
        )
        
        # Convert assignee if present
        assignee = None
        if github_pr.assignee:
            assignee = User(
                id=str(github_pr.assignee.id),
                username=github_pr.assignee.login,
                name=None,
                email=None,
                avatar_url=github_pr.assignee.avatar_url,
                web_url=github_pr.assignee.html_url,
            )
        
        # Get labels
        labels = [label.name for label in github_pr.labels]
        
        return MergeRequest(
            id=str(github_pr.id),
            iid=str(github_pr.number),
            title=github_pr.title,
            description=github_pr.body,
            state=state,
            source_branch=github_pr.head.ref,
            target_branch=github_pr.base.ref,
            author=author,
            web_url=github_pr.html_url,
            created_at=github_pr.created_at,
            updated_at=github_pr.updated_at,
            merged_at=github_pr.merged_at,
            assignee=assignee,
            labels=labels,
            draft=github_pr.draft if hasattr(github_pr, 'draft') else False,
            metadata={'github_pr': github_pr.raw_data}
        )
"""
Abstract base classes for git backend implementations.

This module defines the interface that all git backend implementations
must follow, along with common data models used across backends.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, IO
from datetime import datetime
from enum import Enum


# Exceptions
class BackendError(Exception):
    """Base exception for backend operations."""
    pass


class AuthenticationError(BackendError):
    """Raised when authentication fails."""
    pass


class RepositoryNotFoundError(BackendError):
    """Raised when a repository cannot be found."""
    pass


class UserNotFoundError(BackendError):
    """Raised when a user cannot be found."""
    pass


class BackendPermissionError(BackendError):
    """Raised when operation lacks required permissions."""
    pass


# Enums
class Visibility(Enum):
    """Repository visibility levels."""
    PUBLIC = "public"
    PRIVATE = "private"
    INTERNAL = "internal"  # GitLab-specific, mapped to private on other platforms


class AccessLevel(Enum):
    """User access levels for repositories/groups."""
    GUEST = 10
    REPORTER = 20
    DEVELOPER = 30
    MAINTAINER = 40
    OWNER = 50


# Data Models
@dataclass
class Repository:
    """Platform-agnostic repository representation."""
    id: str
    name: str
    full_name: str  # namespace/name or owner/name
    description: Optional[str]
    clone_url: str  # HTTPS clone URL
    ssh_url: str  # SSH clone URL
    web_url: str  # Web interface URL
    default_branch: str
    visibility: Visibility
    owner: str  # Owner username or organization
    created_at: datetime
    updated_at: datetime
    size: Optional[int] = None  # Size in bytes
    stars_count: Optional[int] = 0
    forks_count: Optional[int] = 0
    open_issues_count: Optional[int] = 0
    archived: bool = False
    disabled: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)  # Platform-specific data


@dataclass
class User:
    """Platform-agnostic user representation."""
    id: str
    username: str
    email: Optional[str]
    name: Optional[str]
    avatar_url: Optional[str]
    web_url: str
    bio: Optional[str] = None
    location: Optional[str] = None
    created_at: Optional[datetime] = None
    is_admin: bool = False
    can_create_group: bool = False
    can_create_project: bool = False
    two_factor_enabled: Optional[bool] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Group:
    """Platform-agnostic group/organization representation."""
    id: str
    name: str
    full_path: str  # Full path including parent groups
    description: Optional[str]
    web_url: str
    avatar_url: Optional[str] = None
    visibility: Visibility = Visibility.PRIVATE
    parent_id: Optional[str] = None  # For nested groups
    created_at: Optional[datetime] = None
    members_count: Optional[int] = 0
    projects_count: Optional[int] = 0
    subgroups_count: Optional[int] = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MergeRequest:
    """Platform-agnostic merge/pull request representation."""
    id: str
    iid: str  # Internal ID within the project
    title: str
    description: Optional[str]
    state: str  # 'open', 'closed', 'merged'
    source_branch: str
    target_branch: str
    author: User
    web_url: str
    created_at: datetime
    updated_at: datetime
    merged_at: Optional[datetime] = None
    merged_by: Optional[User] = None
    assignee: Optional[User] = None
    reviewers: List[User] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    draft: bool = False
    conflicts: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BackendCapabilities:
    """Describes capabilities of a specific backend."""
    create_users: bool = False  # Can create new users
    create_groups: bool = True  # Can create groups/orgs
    nested_groups: bool = False  # Supports nested groups
    fork_repository: bool = True  # Can fork repositories
    protected_branches: bool = True  # Supports branch protection
    merge_requests: bool = True  # Supports merge/pull requests
    ci_cd: bool = True  # Has CI/CD capabilities
    webhooks: bool = True  # Supports webhooks
    deploy_keys: bool = True  # Supports deploy keys
    issues: bool = True  # Has issue tracking
    wiki: bool = True  # Has wiki functionality
    snippets: bool = False  # Supports code snippets/gists
    packages: bool = False  # Has package registry
    pages: bool = False  # Supports static site hosting


class GitBackend(ABC):
    """Abstract base class for git hosting backends."""
    
    def __init__(self):
        """Initialize backend."""
        self._authenticated = False
        self._capabilities = BackendCapabilities()
    
    @property
    def capabilities(self) -> BackendCapabilities:
        """Get backend capabilities."""
        return self._capabilities
    
    @property
    def is_authenticated(self) -> bool:
        """Check if backend is authenticated."""
        return self._authenticated
    
    # Authentication
    @abstractmethod
    def authenticate(self, credentials: Dict[str, str]) -> bool:
        """
        Authenticate with the git hosting service.
        
        Parameters
        ----------
        credentials : Dict[str, str]
            Authentication credentials (token, username/password, etc.)
        
        Returns
        -------
        bool
            True if authentication successful
        
        Raises
        ------
        AuthenticationError
            If authentication fails
        """
        pass
    
    @abstractmethod
    def verify_authentication(self) -> bool:
        """
        Verify that current authentication is still valid.
        
        Returns
        -------
        bool
            True if authentication is valid
        """
        pass
    
    # Repository Operations
    @abstractmethod
    def create_repository(self, name: str, **kwargs) -> Repository:
        """
        Create a new repository.
        
        Parameters
        ----------
        name : str
            Repository name
        **kwargs
            Platform-specific options (visibility, description, etc.)
        
        Returns
        -------
        Repository
            Created repository
        
        Raises
        ------
        BackendError
            If repository creation fails
        """
        pass
    
    @abstractmethod
    def get_repository(self, repo_id: str) -> Repository:
        """
        Get repository information.
        
        Parameters
        ----------
        repo_id : str
            Repository identifier (ID or full name)
        
        Returns
        -------
        Repository
            Repository information
        
        Raises
        ------
        RepositoryNotFoundError
            If repository not found
        """
        pass
    
    @abstractmethod
    def update_repository(self, repo_id: str, **kwargs) -> Repository:
        """
        Update repository settings.
        
        Parameters
        ----------
        repo_id : str
            Repository identifier
        **kwargs
            Settings to update
        
        Returns
        -------
        Repository
            Updated repository
        """
        pass
    
    @abstractmethod
    def delete_repository(self, repo_id: str) -> bool:
        """
        Delete a repository.
        
        Parameters
        ----------
        repo_id : str
            Repository identifier
        
        Returns
        -------
        bool
            True if deletion successful
        """
        pass
    
    @abstractmethod
    def list_repositories(self, **filters) -> List[Repository]:
        """
        List repositories with optional filters.
        
        Parameters
        ----------
        **filters
            Filter options (owned, member, visibility, etc.)
        
        Returns
        -------
        List[Repository]
            List of repositories
        """
        pass
    
    @abstractmethod
    def fork_repository(self, repo_id: str, **kwargs) -> Repository:
        """
        Fork a repository.
        
        Parameters
        ----------
        repo_id : str
            Repository to fork
        **kwargs
            Fork options (namespace, name, etc.)
        
        Returns
        -------
        Repository
            Forked repository
        """
        pass
    
    # User Operations
    @abstractmethod
    def get_current_user(self) -> User:
        """
        Get current authenticated user.
        
        Returns
        -------
        User
            Current user information
        """
        pass
    
    @abstractmethod
    def get_user(self, user_id: str) -> User:
        """
        Get user information.
        
        Parameters
        ----------
        user_id : str
            User identifier (ID or username)
        
        Returns
        -------
        User
            User information
        
        Raises
        ------
        UserNotFoundError
            If user not found
        """
        pass
    
    @abstractmethod
    def list_users(self, **filters) -> List[User]:
        """
        List users with optional filters.
        
        Parameters
        ----------
        **filters
            Filter options
        
        Returns
        -------
        List[User]
            List of users
        """
        pass
    
    def create_user(self, user_data: Dict[str, Any]) -> User:
        """
        Create a new user (if supported).
        
        Parameters
        ----------
        user_data : Dict[str, Any]
            User creation data
        
        Returns
        -------
        User
            Created user
        
        Raises
        ------
        NotImplementedError
            If backend doesn't support user creation
        """
        if not self.capabilities.create_users:
            raise NotImplementedError(f"{self.__class__.__name__} doesn't support user creation")
        return self._create_user_impl(user_data)
    
    def _create_user_impl(self, user_data: Dict[str, Any]) -> User:
        """Implementation of user creation for backends that support it."""
        raise NotImplementedError
    
    # Group Operations
    @abstractmethod
    def create_group(self, name: str, **kwargs) -> Group:
        """
        Create a group/organization.
        
        Parameters
        ----------
        name : str
            Group name
        **kwargs
            Group options
        
        Returns
        -------
        Group
            Created group
        """
        pass
    
    @abstractmethod
    def get_group(self, group_id: str) -> Group:
        """
        Get group information.
        
        Parameters
        ----------
        group_id : str
            Group identifier
        
        Returns
        -------
        Group
            Group information
        """
        pass
    
    @abstractmethod
    def list_groups(self, **filters) -> List[Group]:
        """
        List groups with optional filters.
        
        Parameters
        ----------
        **filters
            Filter options
        
        Returns
        -------
        List[Group]
            List of groups
        """
        pass
    
    @abstractmethod
    def add_user_to_group(self, group_id: str, user_id: str, 
                         access_level: AccessLevel = AccessLevel.DEVELOPER) -> bool:
        """
        Add user to group with specified role.
        
        Parameters
        ----------
        group_id : str
            Group identifier
        user_id : str
            User identifier
        access_level : AccessLevel
            Access level for the user
        
        Returns
        -------
        bool
            True if successful
        """
        pass
    
    @abstractmethod
    def remove_user_from_group(self, group_id: str, user_id: str) -> bool:
        """
        Remove user from group.
        
        Parameters
        ----------
        group_id : str
            Group identifier
        user_id : str
            User identifier
        
        Returns
        -------
        bool
            True if successful
        """
        pass
    
    # File Operations
    @abstractmethod
    def get_file_content(self, repo_id: str, file_path: str, 
                        ref: str = 'main') -> bytes:
        """
        Get file content from repository.
        
        Parameters
        ----------
        repo_id : str
            Repository identifier
        file_path : str
            Path to file in repository
        ref : str
            Git ref (branch, tag, commit)
        
        Returns
        -------
        bytes
            File content
        """
        pass
    
    @abstractmethod
    def create_file(self, repo_id: str, file_path: str, content: Union[str, bytes],
                   message: str, branch: str = 'main', **kwargs) -> Dict[str, Any]:
        """
        Create a new file in repository.
        
        Parameters
        ----------
        repo_id : str
            Repository identifier
        file_path : str
            Path for new file
        content : Union[str, bytes]
            File content
        message : str
            Commit message
        branch : str
            Target branch
        
        Returns
        -------
        Dict[str, Any]
            Operation result
        """
        pass
    
    @abstractmethod
    def update_file(self, repo_id: str, file_path: str, content: Union[str, bytes],
                   message: str, branch: str = 'main', **kwargs) -> Dict[str, Any]:
        """
        Update file in repository.
        
        Parameters
        ----------
        repo_id : str
            Repository identifier
        file_path : str
            Path to file
        content : Union[str, bytes]
            New content
        message : str
            Commit message
        branch : str
            Target branch
        
        Returns
        -------
        Dict[str, Any]
            Operation result
        """
        pass
    
    @abstractmethod
    def delete_file(self, repo_id: str, file_path: str, message: str,
                   branch: str = 'main', **kwargs) -> Dict[str, Any]:
        """
        Delete file from repository.
        
        Parameters
        ----------
        repo_id : str
            Repository identifier
        file_path : str
            Path to file
        message : str
            Commit message
        branch : str
            Target branch
        
        Returns
        -------
        Dict[str, Any]
            Operation result
        """
        pass
    
    # Merge Request Operations
    @abstractmethod
    def create_merge_request(self, repo_id: str, title: str, source_branch: str,
                           target_branch: str = 'main', **kwargs) -> MergeRequest:
        """
        Create merge/pull request.
        
        Parameters
        ----------
        repo_id : str
            Repository identifier
        title : str
            MR/PR title
        source_branch : str
            Source branch
        target_branch : str
            Target branch
        
        Returns
        -------
        MergeRequest
            Created merge request
        """
        pass
    
    @abstractmethod
    def get_merge_request(self, repo_id: str, mr_id: str) -> MergeRequest:
        """
        Get merge request information.
        
        Parameters
        ----------
        repo_id : str
            Repository identifier
        mr_id : str
            Merge request identifier
        
        Returns
        -------
        MergeRequest
            Merge request information
        """
        pass
    
    @abstractmethod
    def list_merge_requests(self, repo_id: str, **filters) -> List[MergeRequest]:
        """
        List merge requests for repository.
        
        Parameters
        ----------
        repo_id : str
            Repository identifier
        **filters
            Filter options (state, author, etc.)
        
        Returns
        -------
        List[MergeRequest]
            List of merge requests
        """
        pass
    
    # Utility Methods
    def clone_url_with_auth(self, repo: Repository, use_ssh: bool = False) -> str:
        """
        Get clone URL with authentication embedded (if needed).
        
        Parameters
        ----------
        repo : Repository
            Repository to clone
        use_ssh : bool
            Use SSH URL instead of HTTPS
        
        Returns
        -------
        str
            Clone URL with authentication
        """
        if use_ssh:
            return repo.ssh_url
        return repo.clone_url
    
    def normalize_visibility(self, visibility: Union[str, Visibility]) -> Visibility:
        """
        Normalize visibility string to Visibility enum.
        
        Parameters
        ----------
        visibility : Union[str, Visibility]
            Visibility value
        
        Returns
        -------
        Visibility
            Normalized visibility
        """
        if isinstance(visibility, Visibility):
            return visibility
        
        visibility_map = {
            'public': Visibility.PUBLIC,
            'private': Visibility.PRIVATE,
            'internal': Visibility.INTERNAL,
        }
        
        return visibility_map.get(visibility.lower(), Visibility.PRIVATE)
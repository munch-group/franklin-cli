"""Stable interfaces for Franklin plugins.

This module provides facade interfaces that plugins should use instead of
directly importing internal modules. This provides a stable API surface
that can be maintained across Franklin versions.
"""

from typing import Optional, Dict, Any, List, Tuple
import subprocess
from pathlib import Path


class GitLabInterface:
    """Stable interface for GitLab operations.
    
    Plugins should use this interface instead of directly importing
    from franklin.gitlab to ensure compatibility across versions.
    """
    
    @staticmethod
    def get_gitlab_url() -> str:
        """Get the configured GitLab URL."""
        from franklin import config
        return config.gitlab_url()
    
    @staticmethod
    def get_api_token() -> Optional[str]:
        """Get the current GitLab API token."""
        from franklin import config
        return config.gitlab_token()
    
    @staticmethod
    def get_user_info() -> Dict[str, Any]:
        """Get information about the current GitLab user."""
        from franklin import gitlab
        return gitlab.get_user_info()
    
    @staticmethod
    def create_project(name: str, namespace: Optional[str] = None) -> Dict[str, Any]:
        """Create a new GitLab project."""
        from franklin import gitlab
        return gitlab.create_project(name, namespace)
    
    @staticmethod
    def get_project(project_id: str) -> Dict[str, Any]:
        """Get information about a GitLab project."""
        from franklin import gitlab
        return gitlab.get_project(project_id)


class TerminalInterface:
    """Stable interface for terminal operations.
    
    Provides consistent terminal formatting and interaction utilities
    for plugins.
    """
    
    @staticmethod
    def print_success(message: str) -> None:
        """Print a success message."""
        from franklin import terminal
        terminal.print_success(message)
    
    @staticmethod
    def print_error(message: str) -> None:
        """Print an error message."""
        from franklin import terminal
        terminal.print_error(message)
    
    @staticmethod
    def print_warning(message: str) -> None:
        """Print a warning message."""
        from franklin import terminal
        terminal.print_warning(message)
    
    @staticmethod
    def print_info(message: str) -> None:
        """Print an info message."""
        from franklin import terminal
        terminal.print_info(message)
    
    @staticmethod
    def prompt(message: str, default: Optional[str] = None) -> str:
        """Prompt the user for input."""
        from franklin import terminal
        return terminal.prompt(message, default)
    
    @staticmethod
    def confirm(message: str, default: bool = False) -> bool:
        """Ask the user for confirmation."""
        from franklin import terminal
        return terminal.confirm(message, default)


class DockerInterface:
    """Stable interface for Docker operations.
    
    Provides Docker container and image management utilities for plugins.
    """
    
    @staticmethod
    def is_docker_running() -> bool:
        """Check if Docker is running."""
        from franklin import docker
        return docker.is_docker_running()
    
    @staticmethod
    def container_exists(name: str) -> bool:
        """Check if a container exists."""
        from franklin import docker
        return docker.container_exists(name)
    
    @staticmethod
    def start_container(name: str, image: str, **kwargs) -> None:
        """Start a Docker container."""
        from franklin import docker
        docker.start_container(name, image, **kwargs)
    
    @staticmethod
    def stop_container(name: str) -> None:
        """Stop a Docker container."""
        from franklin import docker
        docker.stop_container(name)
    
    @staticmethod
    def remove_container(name: str) -> None:
        """Remove a Docker container."""
        from franklin import docker
        docker.remove_container(name)
    
    @staticmethod
    def get_container_status(name: str) -> str:
        """Get the status of a container."""
        from franklin import docker
        return docker.get_container_status(name)


class JupyterInterface:
    """Stable interface for Jupyter operations.
    
    Provides Jupyter server management utilities for plugins.
    """
    
    @staticmethod
    def start_jupyter_server(container: str, port: int = 8888) -> str:
        """Start a Jupyter server in a container."""
        from franklin import jupyter
        return jupyter.start_server(container, port)
    
    @staticmethod
    def stop_jupyter_server(container: str) -> None:
        """Stop a Jupyter server in a container."""
        from franklin import jupyter
        jupyter.stop_server(container)
    
    @staticmethod
    def get_jupyter_url(container: str) -> Optional[str]:
        """Get the URL of a running Jupyter server."""
        from franklin import jupyter
        return jupyter.get_url(container)
    
    @staticmethod
    def is_jupyter_running(container: str) -> bool:
        """Check if Jupyter is running in a container."""
        from franklin import jupyter
        return jupyter.is_running(container)


class ConfigInterface:
    """Stable interface for configuration management.
    
    Provides configuration access and management utilities for plugins.
    """
    
    @staticmethod
    def get_config_value(key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        from franklin import config
        return config.get(key, default)
    
    @staticmethod
    def set_config_value(key: str, value: Any) -> None:
        """Set a configuration value."""
        from franklin import config
        config.set(key, value)
    
    @staticmethod
    def get_config_path() -> Path:
        """Get the path to the configuration file."""
        from franklin import config
        return Path(config.config_file())
    
    @staticmethod
    def reload_config() -> None:
        """Reload the configuration from disk."""
        from franklin import config
        config.reload()


class UtilsInterface:
    """Stable interface for utility functions.
    
    Provides common utility functions for plugins.
    """
    
    @staticmethod
    def run_command(command: List[str], **kwargs) -> subprocess.CompletedProcess:
        """Run a shell command."""
        from franklin import utils
        return utils.run_command(command, **kwargs)
    
    @staticmethod
    def get_home_directory() -> Path:
        """Get the user's home directory."""
        from franklin import utils
        return Path(utils.home_directory())
    
    @staticmethod
    def ensure_directory(path: Path) -> None:
        """Ensure a directory exists."""
        from franklin import utils
        utils.ensure_directory(str(path))
    
    @staticmethod
    def copy_file(source: Path, dest: Path) -> None:
        """Copy a file."""
        from franklin import utils
        utils.copy_file(str(source), str(dest))
    
    @staticmethod
    def download_file(url: str, dest: Path) -> None:
        """Download a file from a URL."""
        from franklin import utils
        utils.download_file(url, str(dest))
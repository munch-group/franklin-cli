"""
Backend factory for creating and managing git backend instances.

This module provides factory functions and configuration management
for different git backend implementations.
"""

import os
import yaml
import json
from typing import Dict, Type, Optional, Any
from pathlib import Path

from .base import GitBackend, BackendError
from .gitlab_backend import GitLabBackend
from .github_backend import GitHubBackend


class BackendFactory:
    """Factory for creating git backend instances."""
    
    # Registry of available backends
    _backends: Dict[str, Type[GitBackend]] = {
        'gitlab': GitLabBackend,
        'github': GitHubBackend,
    }
    
    # Current backend instance (singleton pattern)
    _current_backend: Optional[GitBackend] = None
    _current_backend_type: Optional[str] = None
    
    @classmethod
    def register_backend(cls, name: str, backend_class: Type[GitBackend]) -> None:
        """
        Register a new backend type.
        
        Parameters
        ----------
        name : str
            Backend type name
        backend_class : Type[GitBackend]
            Backend class implementing GitBackend interface
        """
        if not issubclass(backend_class, GitBackend):
            raise ValueError(f"{backend_class} must inherit from GitBackend")
        cls._backends[name.lower()] = backend_class
    
    @classmethod
    def list_backends(cls) -> list[str]:
        """
        List available backend types.
        
        Returns
        -------
        list[str]
            List of registered backend type names
        """
        return list(cls._backends.keys())
    
    @classmethod
    def create_backend(cls, backend_type: str, **config) -> GitBackend:
        """
        Create backend instance from type and configuration.
        
        Parameters
        ----------
        backend_type : str
            Type of backend to create
        **config
            Backend-specific configuration
        
        Returns
        -------
        GitBackend
            Configured backend instance
        
        Raises
        ------
        ValueError
            If backend type is not registered
        """
        backend_type = backend_type.lower()
        
        if backend_type not in cls._backends:
            available = ', '.join(cls._backends.keys())
            raise ValueError(
                f"Unknown backend type: '{backend_type}'. "
                f"Available backends: {available}"
            )
        
        backend_class = cls._backends[backend_type]
        return backend_class(**config)
    
    @classmethod
    def from_config(cls, config_path: Optional[str] = None) -> GitBackend:
        """
        Create backend from configuration file.
        
        Parameters
        ----------
        config_path : Optional[str]
            Path to configuration file. If None, searches default locations.
        
        Returns
        -------
        GitBackend
            Configured backend instance
        
        Raises
        ------
        BackendError
            If configuration cannot be loaded
        """
        config = load_backend_config(config_path)
        
        if not config or 'backend' not in config:
            raise BackendError("No backend configuration found")
        
        backend_config = config['backend']
        backend_type = backend_config.get('type', 'gitlab')
        settings = backend_config.get('settings', {})
        
        # Expand environment variables in settings
        settings = expand_env_vars(settings)
        
        # Create and configure backend
        backend = cls.create_backend(backend_type, **settings)
        
        # Apply defaults if present
        if 'defaults' in backend_config:
            backend.defaults = backend_config['defaults']
        
        return backend
    
    @classmethod
    def get_current_backend(cls) -> Optional[GitBackend]:
        """
        Get the current backend instance (singleton).
        
        Returns
        -------
        Optional[GitBackend]
            Current backend instance or None
        """
        return cls._current_backend
    
    @classmethod
    def set_current_backend(cls, backend: GitBackend, backend_type: str) -> None:
        """
        Set the current backend instance.
        
        Parameters
        ----------
        backend : GitBackend
            Backend instance to set as current
        backend_type : str
            Type of the backend
        """
        cls._current_backend = backend
        cls._current_backend_type = backend_type
    
    @classmethod
    def clear_current_backend(cls) -> None:
        """Clear the current backend instance."""
        cls._current_backend = None
        cls._current_backend_type = None


def load_backend_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load backend configuration from file.
    
    Parameters
    ----------
    config_path : Optional[str]
        Path to configuration file. If None, searches default locations.
    
    Returns
    -------
    Dict[str, Any]
        Configuration dictionary
    """
    # If specific path provided, use it
    if config_path:
        config_path = Path(config_path)
        if not config_path.exists():
            raise BackendError(f"Configuration file not found: {config_path}")
        
        return _load_config_file(config_path)
    
    # Search default locations
    search_paths = [
        Path.cwd() / '.franklin' / 'backend.yaml',
        Path.cwd() / '.franklin' / 'backend.yml',
        Path.cwd() / '.franklin' / 'backend.json',
        Path.cwd() / 'franklin.yaml',
        Path.cwd() / 'franklin.yml',
        Path.home() / '.franklin' / 'backend.yaml',
        Path.home() / '.franklin' / 'backend.yml',
        Path.home() / '.franklin' / 'backend.json',
        Path.home() / '.config' / 'franklin' / 'backend.yaml',
        Path.home() / '.config' / 'franklin' / 'backend.yml',
    ]
    
    for path in search_paths:
        if path.exists():
            return _load_config_file(path)
    
    # No configuration file found, return defaults
    return get_default_config()


def _load_config_file(path: Path) -> Dict[str, Any]:
    """
    Load configuration from a specific file.
    
    Parameters
    ----------
    path : Path
        Path to configuration file
    
    Returns
    -------
    Dict[str, Any]
        Configuration dictionary
    """
    try:
        with open(path, 'r') as f:
            if path.suffix in ['.yaml', '.yml']:
                return yaml.safe_load(f)
            elif path.suffix == '.json':
                return json.load(f)
            else:
                # Try YAML first, then JSON
                content = f.read()
                try:
                    return yaml.safe_load(content)
                except:
                    return json.loads(content)
    except Exception as e:
        raise BackendError(f"Failed to load configuration from {path}: {e}")


def get_default_config() -> Dict[str, Any]:
    """
    Get default backend configuration.
    
    Returns
    -------
    Dict[str, Any]
        Default configuration
    """
    return {
        'backend': {
            'type': 'gitlab',
            'settings': {
                'url': os.environ.get('GITLAB_URL', 'https://gitlab.com'),
                'token': os.environ.get('GITLAB_TOKEN', os.environ.get('FRANKLIN_GIT_TOKEN')),
            },
            'defaults': {
                'visibility': 'private',
                'init_readme': True,
                'default_branch': 'main',
            }
        }
    }


def expand_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Expand environment variables in configuration values.
    
    Parameters
    ----------
    config : Dict[str, Any]
        Configuration dictionary
    
    Returns
    -------
    Dict[str, Any]
        Configuration with expanded environment variables
    """
    import re
    
    def expand_value(value):
        if isinstance(value, str):
            # Match ${VAR_NAME} or $VAR_NAME
            pattern = r'\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)'
            
            def replace_var(match):
                var_name = match.group(1) or match.group(2)
                return os.environ.get(var_name, match.group(0))
            
            return re.sub(pattern, replace_var, value)
        elif isinstance(value, dict):
            return {k: expand_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [expand_value(item) for item in value]
        else:
            return value
    
    return expand_value(config)


def save_backend_config(config: Dict[str, Any], path: Optional[str] = None) -> None:
    """
    Save backend configuration to file.
    
    Parameters
    ----------
    config : Dict[str, Any]
        Configuration to save
    path : Optional[str]
        Path to save to. If None, saves to default location.
    """
    if path is None:
        path = Path.home() / '.franklin' / 'backend.yaml'
    else:
        path = Path(path)
    
    # Create directory if needed
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save configuration
    with open(path, 'w') as f:
        if path.suffix in ['.yaml', '.yml']:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        else:
            json.dump(config, f, indent=2)


# Convenience functions
def get_backend(backend_type: Optional[str] = None, **config) -> GitBackend:
    """
    Get or create a backend instance.
    
    If no backend_type is provided, tries to load from configuration.
    If a current backend exists and matches the requested type, returns it.
    
    Parameters
    ----------
    backend_type : Optional[str]
        Type of backend to get
    **config
        Backend configuration
    
    Returns
    -------
    GitBackend
        Backend instance
    """
    # If no type specified, load from config
    if backend_type is None:
        return BackendFactory.from_config()
    
    # Check if current backend matches
    current = BackendFactory.get_current_backend()
    if current and BackendFactory._current_backend_type == backend_type:
        return current
    
    # Create new backend
    backend = BackendFactory.create_backend(backend_type, **config)
    BackendFactory.set_current_backend(backend, backend_type)
    return backend


def get_current_backend() -> Optional[GitBackend]:
    """
    Get the current backend instance.
    
    Returns
    -------
    Optional[GitBackend]
        Current backend or None
    """
    return BackendFactory.get_current_backend()
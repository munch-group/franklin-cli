"""
Backend configuration management.

This module handles loading, saving, and validating backend configurations.
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path
import yaml

from .factory import BackendFactory, load_backend_config, save_backend_config


class BackendConfig:
    """Manage backend configuration for Franklin."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize backend configuration.
        
        Parameters
        ----------
        config_path : Optional[str]
            Path to configuration file
        """
        self.config_path = config_path
        self.config = load_backend_config(config_path)
    
    @property
    def backend_type(self) -> str:
        """Get configured backend type."""
        return self.config.get('backend', {}).get('type', 'gitlab')
    
    @property
    def backend_settings(self) -> Dict[str, Any]:
        """Get backend settings."""
        return self.config.get('backend', {}).get('settings', {})
    
    @property
    def backend_defaults(self) -> Dict[str, Any]:
        """Get backend defaults."""
        return self.config.get('backend', {}).get('defaults', {})
    
    def set_backend_type(self, backend_type: str) -> None:
        """
        Set the backend type.
        
        Parameters
        ----------
        backend_type : str
            Backend type to use
        """
        if 'backend' not in self.config:
            self.config['backend'] = {}
        self.config['backend']['type'] = backend_type
    
    def set_backend_setting(self, key: str, value: Any) -> None:
        """
        Set a backend setting.
        
        Parameters
        ----------
        key : str
            Setting key
        value : Any
            Setting value
        """
        if 'backend' not in self.config:
            self.config['backend'] = {}
        if 'settings' not in self.config['backend']:
            self.config['backend']['settings'] = {}
        self.config['backend']['settings'][key] = value
    
    def set_backend_default(self, key: str, value: Any) -> None:
        """
        Set a backend default.
        
        Parameters
        ----------
        key : str
            Default key
        value : Any
            Default value
        """
        if 'backend' not in self.config:
            self.config['backend'] = {}
        if 'defaults' not in self.config['backend']:
            self.config['backend']['defaults'] = {}
        self.config['backend']['defaults'][key] = value
    
    def save(self, path: Optional[str] = None) -> None:
        """
        Save configuration to file.
        
        Parameters
        ----------
        path : Optional[str]
            Path to save to. Uses config_path if not provided.
        """
        save_path = path or self.config_path
        save_backend_config(self.config, save_path)
    
    def validate(self) -> bool:
        """
        Validate configuration.
        
        Returns
        -------
        bool
            True if configuration is valid
        """
        # Check required fields
        if 'backend' not in self.config:
            return False
        
        backend = self.config['backend']
        
        # Check backend type
        if 'type' not in backend:
            return False
        
        # Check if backend type is registered
        if backend['type'] not in BackendFactory.list_backends():
            return False
        
        # Backend-specific validation
        if backend['type'] == 'gitlab':
            settings = backend.get('settings', {})
            # GitLab requires URL and token
            if not settings.get('url'):
                return False
            if not settings.get('token'):
                # Check environment variables
                if not os.environ.get('GITLAB_TOKEN') and not os.environ.get('FRANKLIN_GIT_TOKEN'):
                    return False
        
        return True
    
    def to_yaml(self) -> str:
        """
        Convert configuration to YAML string.
        
        Returns
        -------
        str
            YAML representation of configuration
        """
        return yaml.dump(self.config, default_flow_style=False, sort_keys=False)
    
    @classmethod
    def create_default(cls, backend_type: str = 'gitlab') -> 'BackendConfig':
        """
        Create default configuration for a backend type.
        
        Parameters
        ----------
        backend_type : str
            Backend type to create configuration for
        
        Returns
        -------
        BackendConfig
            Default configuration
        """
        config = BackendConfig()
        
        if backend_type == 'gitlab':
            config.config = {
                'backend': {
                    'type': 'gitlab',
                    'settings': {
                        'url': '${GITLAB_URL:-https://gitlab.com}',
                        'token': '${GITLAB_TOKEN}',
                    },
                    'defaults': {
                        'visibility': 'private',
                        'init_readme': True,
                        'default_branch': 'main',
                    },
                    'features': {
                        'create_users': True,
                        'create_groups': True,
                        'nested_groups': True,
                        'ci_integration': True,
                    }
                }
            }
        elif backend_type == 'github':
            config.config = {
                'backend': {
                    'type': 'github',
                    'settings': {
                        'token': '${GITHUB_TOKEN}',
                    },
                    'defaults': {
                        'visibility': 'private',
                        'init_readme': True,
                        'default_branch': 'main',
                        'org': None,  # Optional organization
                    },
                    'features': {
                        'create_users': False,  # GitHub doesn't support user creation
                        'create_groups': True,  # Organizations
                        'nested_groups': False,  # No nested orgs
                        'ci_integration': True,  # GitHub Actions
                    }
                }
            }
        else:
            raise ValueError(f"Unknown backend type: {backend_type}")
        
        return config


def get_backend_config_path() -> Optional[Path]:
    """
    Get the path to the backend configuration file.
    
    Returns
    -------
    Optional[Path]
        Path to configuration file if it exists
    """
    search_paths = [
        Path.cwd() / '.franklin' / 'backend.yaml',
        Path.home() / '.franklin' / 'backend.yaml',
        Path.home() / '.config' / 'franklin' / 'backend.yaml',
    ]
    
    for path in search_paths:
        if path.exists():
            return path
    
    return None


def init_backend_config(backend_type: str = 'gitlab', interactive: bool = True) -> BackendConfig:
    """
    Initialize backend configuration interactively or with defaults.
    
    Parameters
    ----------
    backend_type : str
        Type of backend to configure
    interactive : bool
        Whether to prompt for configuration values
    
    Returns
    -------
    BackendConfig
        Initialized configuration
    """
    config = BackendConfig.create_default(backend_type)
    
    if interactive:
        import click
        
        click.echo(f"Configuring {backend_type} backend...")
        
        if backend_type == 'gitlab':
            # Prompt for GitLab settings
            url = click.prompt(
                'GitLab URL',
                default='https://gitlab.com',
                type=str
            )
            config.set_backend_setting('url', url)
            
            token = click.prompt(
                'GitLab personal access token',
                hide_input=True,
                type=str
            )
            if token:
                config.set_backend_setting('token', token)
            
            visibility = click.prompt(
                'Default repository visibility',
                type=click.Choice(['public', 'private', 'internal']),
                default='private'
            )
            config.set_backend_default('visibility', visibility)
            
        elif backend_type == 'github':
            # Prompt for GitHub settings
            token = click.prompt(
                'GitHub personal access token',
                hide_input=True,
                type=str
            )
            if token:
                config.set_backend_setting('token', token)
            
            org = click.prompt(
                'Default organization (optional)',
                default='',
                type=str
            )
            if org:
                config.set_backend_default('org', org)
            
            visibility = click.prompt(
                'Default repository visibility',
                type=click.Choice(['public', 'private']),
                default='private'
            )
            config.set_backend_default('visibility', visibility)
    
    # Save configuration
    save_path = Path.home() / '.franklin' / 'backend.yaml'
    save_path.parent.mkdir(parents=True, exist_ok=True)
    config.save(str(save_path))
    
    click.echo(f"Configuration saved to {save_path}")
    
    return config
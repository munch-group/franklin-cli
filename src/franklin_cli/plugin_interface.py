"""Plugin interface for Franklin extensions.

This module defines the base classes and interfaces that plugins should use
to extend Franklin's functionality in a stable, maintainable way.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import click


class FranklinPlugin(ABC):
    """Base class for Franklin plugins.
    
    All Franklin plugins should inherit from this class to ensure
    consistent behavior and maintainable interfaces.
    """
    
    @abstractmethod
    def get_commands(self) -> List[click.Command]:
        """Return a list of Click commands to register with the CLI.
        
        Returns:
            List of Click command objects that will be added to the main CLI.
        """
        pass
    
    def get_config_schema(self) -> Optional[Dict[str, Any]]:
        """Return the configuration schema for this plugin.
        
        Returns:
            Optional dictionary defining the plugin's configuration schema.
            Return None if the plugin doesn't require configuration.
        """
        return None
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the plugin with the provided configuration.
        
        Args:
            config: Configuration dictionary for the plugin.
        """
        pass
    
    def get_version(self) -> str:
        """Return the plugin version.
        
        Returns:
            Version string for the plugin.
        """
        return "0.0.0"
    
    def get_description(self) -> str:
        """Return a brief description of the plugin.
        
        Returns:
            Description string for the plugin.
        """
        return ""
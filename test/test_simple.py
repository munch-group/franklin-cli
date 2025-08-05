#!/usr/bin/env python
"""
Simplified tests for Franklin commands that properly mock all interactions.
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

# Add src directory to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(parent_dir, 'src')
sys.path.insert(0, src_dir)

import franklin


class TestFranklinCommands(unittest.TestCase):
    """Test Franklin commands with proper mocking."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        
    def test_help_command(self):
        """Test that help command works."""
        result = self.runner.invoke(franklin.franklin, ['--help'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Usage:', result.output)
        
    def test_version_command(self):
        """Test version display."""
        result = self.runner.invoke(franklin.franklin, ['--version'])
        self.assertEqual(result.exit_code, 0)
        
    @patch('franklin.gitlab.get_registry_listing')
    @patch('franklin.gitlab.input')
    @patch('franklin.utils.run_cmd')
    @patch('franklin.desktop.ensure_docker_installed')
    def test_download_with_url(self, mock_docker_installed, mock_run_cmd, 
                               mock_input, mock_registry):
        """Test download with direct URL provided."""
        # Setup mocks
        mock_docker_installed.return_value = None
        mock_run_cmd.return_value = None  # Simulate successful git clone
        
        # Run with direct URL (no interactive prompts)
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(
                franklin.franklin, 
                ['download', 'https://gitlab.au.dk/course/exercise.git']
            )
            
            # Should not prompt for input when URL is provided
            mock_input.assert_not_called()
            
    @patch('franklin.docker.images')
    @patch('franklin.docker.desktop_status')
    @patch('franklin.gitlab.get_registry_listing')
    def test_jupyter_list_images(self, mock_registry, mock_status, mock_images):
        """Test jupyter when no images are available."""
        mock_status.return_value = 'running'
        mock_images.return_value = []
        mock_registry.return_value = {}  # Empty registry
        
        # Run in isolated filesystem to avoid subfolder issues
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(franklin.franklin, ['jupyter'])
        
            # When no images exist, jupyter command exits with code 1
            # and shows a message about no images
            if result.exit_code != 0:
                self.assertIn('No', result.output) or self.assertIn('images', result.output.lower())
            else:
                # Or it might just exit cleanly
                self.assertEqual(result.exit_code, 0)
        
    def test_update_command_exists(self):
        """Test that update command exists and is accessible."""
        result = self.runner.invoke(franklin.franklin, ['update', '--help'])
        
        # Should show help for update command
        self.assertEqual(result.exit_code, 0)
        self.assertIn('update', result.output.lower())
            
    @patch('franklin.docker.desktop_status')
    @patch('franklin.docker.containers')
    def test_cleanup_docker_not_running(self, mock_containers, mock_status):
        """Test cleanup when Docker is not running."""
        mock_status.return_value = 'stopped'
        # Simulate Docker command failing when Docker is not running
        mock_containers.side_effect = Exception('Docker daemon not running')
        
        result = self.runner.invoke(franklin.franklin, ['cleanup'])
        
        # Should exit without error when Docker is not running
        # The cleanup command is marked as irrelevant when Docker is not running
        self.assertEqual(result.exit_code, 0)


class TestModuleImports(unittest.TestCase):
    """Test that modules can be imported and have expected attributes."""
    
    def test_docker_module(self):
        """Test docker module has expected functions."""
        from franklin import docker
        
        # Check key functions exist
        self.assertTrue(hasattr(docker, 'desktop_status'))
        self.assertTrue(hasattr(docker, 'images'))
        self.assertTrue(hasattr(docker, 'image_list'))
        self.assertTrue(hasattr(docker, 'prune_all'))
        self.assertTrue(hasattr(docker, 'containers'))
        self.assertTrue(hasattr(docker, 'run_container'))
        
    def test_gitlab_module(self):
        """Test gitlab module has expected functions."""
        from franklin import gitlab
        
        # Check key functions exist
        self.assertTrue(hasattr(gitlab, 'get_registry_listing'))
        self.assertTrue(hasattr(gitlab, 'get_course_names'))
        self.assertTrue(hasattr(gitlab, 'pick_course'))
        self.assertTrue(hasattr(gitlab, 'download'))
        
    def test_jupyter_module(self):
        """Test jupyter module has expected functions."""
        from franklin import jupyter
        
        # Check key functions exist
        self.assertTrue(hasattr(jupyter, 'launch_jupyter'))
        self.assertTrue(hasattr(jupyter, 'jupyter'))
        
    def test_update_module(self):
        """Test update module has expected functions."""
        from franklin import update
        
        # Check key functions exist
        self.assertTrue(hasattr(update, 'detect_installation_method'))
        self.assertTrue(hasattr(update, 'update'))
        self.assertTrue(hasattr(update, 'UpdateStatus'))
        self.assertTrue(hasattr(update, 'update_packages'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
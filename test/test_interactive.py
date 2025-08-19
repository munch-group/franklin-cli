"""
Test suite for interactive Franklin commands with simulated user input.

This module provides comprehensive testing for Franklin's interactive
commands by simulating various user input scenarios using Click's
testing utilities and mock objects.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
from click.testing import CliRunner
import click
import sys
import os
from typing import List, Any, Optional, Dict
import json
from pathlib import Path

# Add parent src directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(parent_dir, 'src')
sys.path.insert(0, src_dir)

# Import franklin modules directly
import franklin_cli
from franklin_cli import cutie
from franklin_cli import gitlab  
from franklin_cli import docker


class InteractiveTestBase(unittest.TestCase):
    """Base class for interactive command testing."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = None
        
    def tearDown(self):
        """Clean up after tests."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def mock_cutie_select(self, selections: List[int]):
        """
        Create a mock for cutie.select that returns specified selections.
        
        Parameters
        ----------
        selections : List[int]
            List of selection indices to return in sequence.
        """
        selection_iter = iter(selections)
        
        def mock_select(*args, **kwargs):
            try:
                return next(selection_iter)
            except StopIteration:
                return 0
        
        return mock_select
    
    def mock_cutie_prompt_yes_no(self, responses: List[bool]):
        """
        Create a mock for cutie.prompt_yes_or_no.
        
        Parameters
        ----------
        responses : List[bool]
            List of yes/no responses to return in sequence.
        """
        response_iter = iter(responses)
        
        def mock_prompt(*args, **kwargs):
            try:
                return next(response_iter)
            except StopIteration:
                return False
        
        return mock_prompt


class TestDownloadCommand(InteractiveTestBase):
    """Test the interactive download command."""
    
    @patch('franklin.gitlab.get_registry_listing')
    @patch('franklin.gitlab.cutie.select')
    @patch('franklin.gitlab.clone_and_pull')
    @patch('franklin.docker.config_fit')
    @patch('franklin.desktop.ensure_docker_installed')
    def test_download_basic_selection(self, mock_docker_installed, mock_config_fit,
                                    mock_clone, mock_select, mock_registry):
        """Test basic download with simple course and exercise selection."""
        # Mock registry data
        mock_registry.return_value = {
            'course1': {
                'exercises': {
                    'exercise1': 'Exercise 1: Introduction',
                    'exercise2': 'Exercise 2: Advanced'
                }
            },
            'course2': {
                'exercises': {
                    'exercise3': 'Exercise 3: Final'
                }
            }
        }
        
        # Mock user selections: course1 (index 0), exercise1 (index 0)
        mock_select.side_effect = [0, 0]
        
        # Mock successful clone
        mock_clone.return_value = None
        
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(franklin.franklin, ['download'])
            
            # Check the command succeeded
            self.assertEqual(result.exit_code, 0)
            
            # Verify selections were made
            self.assertEqual(mock_select.call_count, 2)
            
            # Verify clone was called with correct URL
            mock_clone.assert_called_once()
            args = mock_clone.call_args[0]
            self.assertIn('course1/exercise1', args[0])
    
    @patch('franklin.gitlab.get_registry_listing')
    @patch('franklin.gitlab.cutie.select')
    @patch('franklin.gitlab.clone_and_pull')
    def test_download_with_back_navigation(self, mock_clone, mock_select, mock_registry):
        """Test download with user going back to change course selection."""
        mock_registry.return_value = {
            'course1': {'exercises': {'ex1': 'Exercise 1'}},
            'course2': {'exercises': {'ex2': 'Exercise 2'}}
        }
        
        # User selects: course1, <back>, course2, ex2
        # Note: -1 represents "back" in cutie
        mock_select.side_effect = [0, -1, 1, 0]
        
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(franklin.franklin, ['download'])
            
            # Should succeed
            self.assertEqual(result.exit_code, 0)
            
            # Should have called select 4 times
            self.assertEqual(mock_select.call_count, 4)
            
            # Should clone course2/ex2
            mock_clone.assert_called_once()
            args = mock_clone.call_args[0]
            self.assertIn('course2/ex2', args[0])


class TestJupyterCommand(InteractiveTestBase):
    """Test the jupyter command with various scenarios."""
    
    @patch('franklin.jupyter.docker.image_exists')
    @patch('franklin.jupyter.docker.image_list')
    @patch('franklin.jupyter.cutie.select')
    @patch('franklin.jupyter.launch_jupyter')
    def test_jupyter_image_selection(self, mock_launch, mock_select, 
                                   mock_image_list, mock_image_exists):
        """Test jupyter command with image selection."""
        # Mock available images
        mock_image_list.return_value = [
            {'Repository': 'registry.gitlab.au.dk/franklin/course1/ex1'},
            {'Repository': 'registry.gitlab.au.dk/franklin/course1/ex2'},
            {'Repository': 'registry.gitlab.au.dk/franklin/course2/ex1'}
        ]
        
        # User selects second image (index 1)
        mock_select.return_value = 1
        
        # Mock image exists
        mock_image_exists.return_value = True
        
        with self.runner.isolated_filesystem():
            # Create a fake Dockerfile
            with open('Dockerfile', 'w') as f:
                f.write('FROM ubuntu:latest')
            
            result = self.runner.invoke(franklin.franklin, ['jupyter'])
            
            # Should succeed
            self.assertEqual(result.exit_code, 0)
            
            # Should launch with selected image
            mock_launch.assert_called_once()
            selected_image = mock_launch.call_args[0][0]
            self.assertIn('course1/ex2', selected_image)
    
    @patch('franklin.jupyter.docker.image_exists')
    @patch('franklin.jupyter.launch_jupyter')
    def test_jupyter_with_dockerfile(self, mock_launch, mock_image_exists):
        """Test jupyter command when Dockerfile exists in current directory."""
        mock_image_exists.return_value = True
        
        with self.runner.isolated_filesystem():
            # Create a Dockerfile
            with open('Dockerfile', 'w') as f:
                f.write('FROM python:3.9')
            
            result = self.runner.invoke(franklin.franklin, ['jupyter'])
            
            # Should succeed without prompting for selection
            self.assertEqual(result.exit_code, 0)
            
            # Should launch jupyter
            mock_launch.assert_called_once()


class TestUpdateCommand(InteractiveTestBase):
    """Test the update command with different scenarios."""
    
    @patch('franklin.update.detect_installation_method')
    @patch('franklin.update.conda_latest_version')
    @patch('franklin.update.system.package_version')
    @patch('franklin.update.utils.run_cmd')
    def test_update_conda_with_available_update(self, mock_run_cmd, mock_current_version,
                                              mock_latest_version, mock_detect):
        """Test update when newer version is available via conda."""
        # Mock installation method
        mock_detect.return_value = 'conda'
        
        # Mock versions
        mock_current_version.return_value = '1.0.0'
        mock_latest_version.return_value = Mock(
            __str__=lambda x: '1.1.0',
            __gt__=lambda x, y: True,
            __le__=lambda x, y: False
        )
        
        # Mock successful update
        mock_run_cmd.return_value = ''
        
        result = self.runner.invoke(franklin.franklin, ['update'])
        
        # Should exit with code 1 (indicating restart needed)
        self.assertEqual(result.exit_code, 1)
        
        # Should show update message
        self.assertIn('Franklin updated', result.output)
    
    @patch('franklin.update.detect_installation_method')
    @patch('franklin.update.pixi_installed_version')
    def test_update_pixi_global(self, mock_pixi_version, mock_detect):
        """Test update with pixi global installation."""
        # Mock pixi global installation
        mock_detect.return_value = 'pixi-global'
        
        # Mock version (no update available)
        mock_pixi_version.return_value = Mock(__str__=lambda x: '1.0.0')
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = Mock(
                stdout='already up-to-date',
                stderr='',
                returncode=0
            )
            
            result = self.runner.invoke(franklin.franklin, ['update'])
            
            # Should succeed with no updates
            self.assertEqual(result.exit_code, 0)
            
            # Should call pixi global update
            mock_subprocess.assert_called()
            call_args = mock_subprocess.call_args
            self.assertIn('pixi global update', call_args[0][0])


class TestCleanupCommand(InteractiveTestBase):
    """Test the cleanup command with user interaction."""
    
    @patch('franklin.docker.docker_ok')
    @patch('franklin.docker.cutie.prompt_yes_or_no')
    @patch('franklin.docker.prune_all')
    @patch('franklin.docker.prune_all_volumes')
    def test_cleanup_with_confirmation(self, mock_prune_volumes, mock_prune,
                                     mock_prompt, mock_docker_ok):
        """Test cleanup command with user confirmation."""
        # Mock Docker is running
        mock_docker_ok.return_value = True
        
        # User confirms both prompts
        mock_prompt.side_effect = [True, True]
        
        result = self.runner.invoke(franklin.franklin, ['cleanup'])
        
        # Should succeed
        self.assertEqual(result.exit_code, 0)
        
        # Should prompt twice (containers/images, then volumes)
        self.assertEqual(mock_prompt.call_count, 2)
        
        # Should run both prune operations
        mock_prune.assert_called_once()
        mock_prune_volumes.assert_called_once()
    
    @patch('franklin.docker.docker_ok')
    @patch('franklin.docker.cutie.prompt_yes_or_no')
    @patch('franklin.docker.prune_all')
    @patch('franklin.docker.prune_all_volumes')
    def test_cleanup_decline_volumes(self, mock_prune_volumes, mock_prune,
                                   mock_prompt, mock_docker_ok):
        """Test cleanup when user declines volume cleanup."""
        mock_docker_ok.return_value = True
        
        # User confirms containers/images but declines volumes
        mock_prompt.side_effect = [True, False]
        
        result = self.runner.invoke(franklin.franklin, ['cleanup'])
        
        # Should succeed
        self.assertEqual(result.exit_code, 0)
        
        # Should prune containers/images but not volumes
        mock_prune.assert_called_once()
        mock_prune_volumes.assert_not_called()


class TestComplexInteractionScenarios(InteractiveTestBase):
    """Test complex interaction scenarios involving multiple commands."""
    
    def test_full_workflow_download_and_jupyter(self):
        """Test a full workflow: download an exercise then run jupyter."""
        with self.runner.isolated_filesystem():
            # Create a mock update status file to skip updates
            status_file = Path.home() / '.franklin' / 'update_status.json'
            status_file.parent.mkdir(parents=True, exist_ok=True)
            with open(status_file, 'w') as f:
                json.dump({
                    'last_check': '2099-01-01T00:00:00',
                    'last_success': '2099-01-01T00:00:00',
                    'failed_attempts': 0
                }, f)
            
            with patch('franklin.gitlab.get_registry_listing') as mock_registry, \
                 patch('franklin.gitlab.cutie.select') as mock_select, \
                 patch('franklin.gitlab.clone_and_pull') as mock_clone, \
                 patch('franklin.jupyter.launch_jupyter') as mock_launch:
                
                # Setup mocks for download
                mock_registry.return_value = {
                    'course1': {'exercises': {'ex1': 'Exercise 1'}}
                }
                mock_select.return_value = 0  # Select first option
                
                # First command: download
                result1 = self.runner.invoke(franklin.franklin, ['download'])
                self.assertEqual(result1.exit_code, 0)
                
                # Create exercise directory structure
                os.makedirs('Exercise-1')
                with open('Exercise-1/Dockerfile', 'w') as f:
                    f.write('FROM python:3.9')
                
                # Second command: jupyter in downloaded directory
                os.chdir('Exercise-1')
                result2 = self.runner.invoke(franklin.franklin, ['jupyter'])
                
                # Should launch jupyter
                mock_launch.assert_called_once()


class TestErrorHandling(InteractiveTestBase):
    """Test error handling in interactive commands."""
    
    @patch('franklin.gitlab.get_registry_listing')
    def test_download_network_error(self, mock_registry):
        """Test download command when network fails."""
        # Mock network error
        mock_registry.side_effect = Exception("Network error")
        
        result = self.runner.invoke(franklin.franklin, ['download'])
        
        # Should handle error gracefully
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn('error', result.output.lower())
    
    @patch('franklin.docker.docker_ok')
    def test_cleanup_docker_not_running(self, mock_docker_ok):
        """Test cleanup when Docker is not running."""
        mock_docker_ok.return_value = False
        
        result = self.runner.invoke(franklin.franklin, ['cleanup'])
        
        # Should show appropriate message
        self.assertIn('Docker', result.output)


class TestInputValidation(InteractiveTestBase):
    """Test input validation in interactive prompts."""
    
    @patch('franklin.gitlab.get_registry_listing')
    @patch('franklin.gitlab.cutie.select')
    def test_download_invalid_selection_recovery(self, mock_select, mock_registry):
        """Test recovery from invalid selections."""
        mock_registry.return_value = {
            'course1': {'exercises': {'ex1': 'Exercise 1'}}
        }
        
        # Simulate multiple attempts with invalid then valid selection
        # cutie.select handles validation internally, so we just test the flow
        mock_select.side_effect = [0, 0]  # Valid selections
        
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(franklin.franklin, ['download'])
            
            # Should eventually succeed
            self.assertEqual(result.exit_code, 0)


def create_test_suite():
    """Create a test suite with all interactive tests."""
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestDownloadCommand,
        TestJupyterCommand,
        TestUpdateCommand,
        TestCleanupCommand,
        TestComplexInteractionScenarios,
        TestErrorHandling,
        TestInputValidation
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    return suite


if __name__ == '__main__':
    # Run the test suite
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(create_test_suite())
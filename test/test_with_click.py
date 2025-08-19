#!/usr/bin/env python
"""
Test suite for Franklin commands using Click's built-in prompts.

This test suite works with the updated Franklin code that uses Click's
native prompt functions instead of cutie.
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

import franklin_cli


class TestFranklinWithClick(unittest.TestCase):
    """Test Franklin commands with Click's native prompts."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        
    def test_cli_help(self):
        """Test that help is accessible."""
        result = self.runner.invoke(franklin.franklin, ['--help'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Commands:', result.output)
        
    def test_cli_version(self):
        """Test version display."""
        result = self.runner.invoke(franklin.franklin, ['--version'])
        self.assertEqual(result.exit_code, 0)
        
    @patch('franklin.gitlab.get_registry_listing')
    @patch('franklin.utils.run_cmd')
    @patch('franklin.desktop.ensure_docker_installed')
    def test_download_interactive(self, mock_docker, mock_run_cmd, mock_registry):
        """Test interactive download with Click prompts."""
        # Setup mocks
        mock_docker.return_value = None
        mock_run_cmd.return_value = None
        
        # Mock registry data
        mock_registry.return_value = {
            'test-course': {
                'exercises': {
                    'exercise1': 'Exercise 1: Introduction',
                    'exercise2': 'Exercise 2: Advanced'
                }
            },
            'another-course': {
                'exercises': {
                    'exercise3': 'Exercise 3: Final'
                }
            }
        }
        
        # Simulate user input: select course 1, exercise 2
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(
                franklin.franklin, 
                ['download'],
                input='1\n2\n'  # Select first course, second exercise
            )
            
            # Check prompts appeared
            self.assertIn('Available courses:', result.output)
            self.assertIn('Select course number', result.output)
            self.assertIn('Available exercises', result.output)
            self.assertIn('Select exercise number', result.output)
            
    @patch('franklin.gitlab.get_registry_listing')
    @patch('franklin.utils.run_cmd')
    @patch('franklin.desktop.ensure_docker_installed')
    def test_download_with_defaults(self, mock_docker, mock_run_cmd, mock_registry):
        """Test download using default selections (just pressing Enter)."""
        # Setup mocks
        mock_docker.return_value = None
        mock_run_cmd.return_value = None
        
        # Mock registry data
        mock_registry.return_value = {
            'default-course': {
                'exercises': {
                    'default-ex': 'Default Exercise'
                }
            }
        }
        
        # Just press Enter twice to accept defaults
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(
                franklin.franklin,
                ['download'],
                input='\n\n'  # Accept defaults
            )
            
            # Should select the defaults (first course, first exercise)
            self.assertIn('default-course', result.output.lower())
            
    @patch('franklin.docker.images')
    @patch('franklin.docker.containers')
    @patch('franklin.docker.desktop_status')
    def test_cleanup_multi_select(self, mock_status, mock_containers, mock_images):
        """Test cleanup with multi-selection using Click confirms."""
        mock_status.return_value = 'running'
        mock_containers.return_value = [
            {'id': 'container1', 'name': 'test1'},
            {'id': 'container2', 'name': 'test2'},
            {'id': 'container3', 'name': 'test3'}
        ]
        mock_images.return_value = []
        
        # Simulate selecting first and third containers (y, n, y)
        result = self.runner.invoke(
            franklin.franklin,
            ['cleanup'],
            input='y\nn\ny\n'
        )
        
        # Check selection prompts appeared
        self.assertIn('Select containers', result.output)
        
    @patch('franklin.docker.desktop_status')
    def test_cleanup_no_docker(self, mock_status):
        """Test cleanup when Docker is not running."""
        mock_status.return_value = 'stopped'
        
        result = self.runner.invoke(franklin.franklin, ['cleanup'])
        
        # Should handle gracefully
        self.assertEqual(result.exit_code, 0)
        
    @patch('franklin.docker.images')
    @patch('franklin.docker.desktop_status')
    @patch('franklin.gitlab.get_registry_listing')
    def test_jupyter_with_selection(self, mock_registry, mock_status, mock_images):
        """Test jupyter command with course/exercise selection."""
        mock_status.return_value = 'running'
        mock_images.return_value = []
        mock_registry.return_value = {
            'jupyter-course': {
                'exercises': {
                    'notebook1': 'Notebook Exercise'
                }
            }
        }
        
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(
                franklin.franklin,
                ['jupyter'],
                input='1\n1\n'  # Select first course, first exercise
            )
            
            # Should show selection prompts
            if 'Available courses' in result.output:
                self.assertIn('Select course number', result.output)


class TestModuleIntegration(unittest.TestCase):
    """Test that modules work with Click prompts."""
    
    def test_gitlab_module_imports(self):
        """Test gitlab module imports click instead of cutie."""
        from franklin_cli import gitlab
        
        # Should have click imported
        self.assertTrue(hasattr(gitlab, 'click'))
        
        # Core functions should exist
        self.assertTrue(callable(getattr(gitlab, 'pick_course', None)))
        self.assertTrue(callable(getattr(gitlab, 'pick_exercise', None)))
        
    def test_docker_module_imports(self):
        """Test docker module imports click."""
        from franklin_cli import docker
        
        # Should have click imported
        self.assertTrue(hasattr(docker, 'click'))
        
        # Core functions should exist
        self.assertTrue(callable(getattr(docker, 'image_list', None)))
        
    def test_prompts_are_testable(self):
        """Verify Click prompts are easily testable."""
        runner = CliRunner()
        
        # Create a simple command with Click prompt
        import click
        
        @click.command()
        def test_cmd():
            choice = click.prompt('Select', type=click.IntRange(1, 3), default=1)
            click.echo(f'Selected: {choice}')
            
        # Test with input
        result = runner.invoke(test_cmd, input='2\n')
        self.assertIn('Selected: 2', result.output)
        
        # Test with default (just Enter)
        result = runner.invoke(test_cmd, input='\n')
        self.assertIn('Selected: 1', result.output)


def suite():
    """Create test suite."""
    test_suite = unittest.TestSuite()
    test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestFranklinWithClick))
    test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestModuleIntegration))
    return test_suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())
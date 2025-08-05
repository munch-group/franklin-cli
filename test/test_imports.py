#!/usr/bin/env python
"""
Test basic imports to ensure the package structure is working.
"""

import sys
import os
import unittest

# Add src directory to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(parent_dir, 'src')
sys.path.insert(0, src_dir)


class TestImports(unittest.TestCase):
    """Test that all Franklin modules can be imported."""
    
    def test_franklin_import(self):
        """Test importing main franklin module."""
        import franklin
        self.assertTrue(hasattr(franklin, 'franklin'))
        
    def test_cli_callable(self):
        """Test that franklin CLI is callable."""
        import franklin
        from click.testing import CliRunner
        
        runner = CliRunner()
        result = runner.invoke(franklin.franklin, ['--help'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Usage:', result.output)
        
    def test_submodule_imports(self):
        """Test importing Franklin submodules."""
        from franklin import docker
        from franklin import gitlab
        from franklin import jupyter
        from franklin import update
        from franklin import config
        from franklin import utils
        
        # Verify modules loaded
        self.assertIsNotNone(docker)
        self.assertIsNotNone(gitlab)
        self.assertIsNotNone(jupyter)
        self.assertIsNotNone(update)
        self.assertIsNotNone(config)
        self.assertIsNotNone(utils)


if __name__ == '__main__':
    unittest.main(verbosity=2)
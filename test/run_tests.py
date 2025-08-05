#!/usr/bin/env python
"""
Run the Franklin interactive tests.

This script sets up the proper environment and runs the test suite.
"""

import sys
import os
import unittest

# Add src directory to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(parent_dir, 'src')
sys.path.insert(0, src_dir)

# Import test module
from test_interactive import create_test_suite

if __name__ == '__main__':
    # Run the test suite
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(create_test_suite())
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
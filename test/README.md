# Franklin Interactive Tests

This directory contains comprehensive tests for Franklin's interactive commands using simulated user input.

## Running Tests

### Quick Start

```bash
# From the franklin directory
cd franklin

# Run all tests
python test/test_imports.py      # Basic import tests
python test/test_interactive.py  # Full interactive tests

# Or use unittest discovery
python -m unittest discover test/

# For development installation first
pip install -e .
```

### Test Structure

- `test_imports.py` - Basic import and CLI availability tests
- `test_interactive.py` - Comprehensive interactive command tests
- `test_cutie_mocks.py` - Mock implementations for cutie prompts
- `run_tests.py` - Test runner script

### Writing New Tests

The test framework provides utilities for simulating user interactions:

```python
# Example: Test download with specific selections
@patch('franklin.gitlab.get_registry_listing')
@patch('franklin.gitlab.cutie.select')
def test_download_scenario(self, mock_select, mock_registry):
    # Setup mock data
    mock_registry.return_value = {
        'course1': {'exercises': {'ex1': 'Exercise 1'}}
    }
    
    # Simulate user selecting first option twice
    mock_select.side_effect = [0, 0]
    
    # Run command
    result = self.runner.invoke(franklin.franklin, ['download'])
    
    # Assert success
    self.assertEqual(result.exit_code, 0)
```

### Mock Scenarios

The `test_cutie_mocks.py` provides predefined scenarios:

- `download_simple` - Basic download flow
- `download_with_navigation` - Using back navigation
- `cleanup_confirm_all` - Accepting all cleanup prompts
- `cleanup_selective` - Selective cleanup
- `jupyter_select_image` - Selecting Docker images
- `complex_workflow` - Multi-step workflows

### Troubleshooting

If you get import errors:
1. Ensure you're in the `franklin` directory
2. The tests add `src/` to the Python path automatically
3. For installed packages, use `pip install -e .` first

### Dependencies

The tests require:
- Click (for CLI testing)
- unittest (standard library)
- mock (standard library)
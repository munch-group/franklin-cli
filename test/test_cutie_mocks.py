"""
Mock implementations for cutie interactive prompts.

This module provides sophisticated mocking for the cutie library
used by Franklin for interactive user input.
"""

from typing import List, Optional, Dict, Any, Callable, Union
from unittest.mock import Mock
import re


class MockCutieInteraction:
    """
    Sophisticated mock for cutie interactions with stateful behavior.
    
    This class allows testing complex interaction flows including:
    - Sequential selections
    - Conditional responses based on prompts
    - Navigation (back/forward)
    - Input validation
    """
    
    def __init__(self):
        """Initialize the mock interaction system."""
        self.selection_rules: List[Dict[str, Any]] = []
        self.prompt_rules: List[Dict[str, Any]] = []
        self.call_history: List[Dict[str, Any]] = []
        self.current_rule_index = 0
    
    def add_selection_rule(self, 
                          pattern: Optional[str] = None,
                          options_contains: Optional[List[str]] = None,
                          response: Union[int, Callable] = 0,
                          repeat: int = 1):
        """
        Add a rule for cutie.select responses.
        
        Parameters
        ----------
        pattern : Optional[str]
            Regex pattern to match in the prompt text.
        options_contains : Optional[List[str]]
            List of strings that should be in the options.
        response : Union[int, Callable]
            The selection index to return or a callable that returns it.
        repeat : int
            Number of times this rule can be used.
        """
        self.selection_rules.append({
            'type': 'select',
            'pattern': pattern,
            'options_contains': options_contains,
            'response': response,
            'repeat': repeat,
            'used': 0
        })
    
    def add_prompt_rule(self,
                       pattern: Optional[str] = None,
                       response: Union[bool, Callable] = True,
                       repeat: int = 1):
        """
        Add a rule for cutie.prompt_yes_or_no responses.
        
        Parameters
        ----------
        pattern : Optional[str]
            Regex pattern to match in the prompt text.
        response : Union[bool, Callable]
            The yes/no response or a callable that returns it.
        repeat : int
            Number of times this rule can be used.
        """
        self.prompt_rules.append({
            'type': 'prompt',
            'pattern': pattern,
            'response': response,
            'repeat': repeat,
            'used': 0
        })
    
    def mock_select(self, options: List[str], caption: str = "", **kwargs) -> int:
        """Mock implementation of cutie.select."""
        call_info = {
            'function': 'select',
            'options': options,
            'caption': caption,
            'kwargs': kwargs
        }
        self.call_history.append(call_info)
        
        # Find matching rule
        for rule in self.selection_rules:
            if rule['used'] >= rule['repeat']:
                continue
                
            # Check pattern match
            if rule['pattern'] and not re.search(rule['pattern'], caption):
                continue
            
            # Check options contain required strings
            if rule['options_contains']:
                options_str = ' '.join(options)
                if not all(req in options_str for req in rule['options_contains']):
                    continue
            
            # This rule matches
            rule['used'] += 1
            
            if callable(rule['response']):
                return rule['response'](options, caption)
            else:
                return rule['response']
        
        # No matching rule, return default
        return 0
    
    def mock_prompt_yes_or_no(self, prompt: str, **kwargs) -> bool:
        """Mock implementation of cutie.prompt_yes_or_no."""
        call_info = {
            'function': 'prompt_yes_or_no',
            'prompt': prompt,
            'kwargs': kwargs
        }
        self.call_history.append(call_info)
        
        # Find matching rule
        for rule in self.prompt_rules:
            if rule['used'] >= rule['repeat']:
                continue
                
            # Check pattern match
            if rule['pattern'] and not re.search(rule['pattern'], prompt):
                continue
            
            # This rule matches
            rule['used'] += 1
            
            if callable(rule['response']):
                return rule['response'](prompt)
            else:
                return rule['response']
        
        # No matching rule, return default
        return True
    
    def get_call_history(self) -> List[Dict[str, Any]]:
        """Get the history of all calls made."""
        return self.call_history
    
    def assert_selection_made(self, caption_pattern: str) -> None:
        """Assert that a selection was made with a caption matching the pattern."""
        for call in self.call_history:
            if call['function'] == 'select' and re.search(caption_pattern, call['caption']):
                return
        raise AssertionError(f"No selection made with caption matching '{caption_pattern}'")
    
    def assert_prompt_shown(self, prompt_pattern: str) -> None:
        """Assert that a yes/no prompt was shown matching the pattern."""
        for call in self.call_history:
            if call['function'] == 'prompt_yes_or_no' and re.search(prompt_pattern, call['prompt']):
                return
        raise AssertionError(f"No prompt shown matching '{prompt_pattern}'")


class InteractionScenario:
    """
    Define complex interaction scenarios for testing.
    
    This allows creating reusable test scenarios that can be applied
    to different commands.
    """
    
    def __init__(self, name: str):
        """Initialize a new scenario."""
        self.name = name
        self.steps: List[Dict[str, Any]] = []
    
    def add_step(self, 
                 step_type: str,
                 description: str,
                 **kwargs):
        """
        Add a step to the scenario.
        
        Parameters
        ----------
        step_type : str
            Type of step: 'select', 'prompt', 'input', 'wait'
        description : str
            Human-readable description of the step.
        **kwargs
            Additional parameters for the step.
        """
        self.steps.append({
            'type': step_type,
            'description': description,
            **kwargs
        })
    
    def to_mock_interaction(self) -> MockCutieInteraction:
        """Convert scenario to a MockCutieInteraction."""
        mock = MockCutieInteraction()
        
        for step in self.steps:
            if step['type'] == 'select':
                mock.add_selection_rule(
                    pattern=step.get('pattern'),
                    options_contains=step.get('options_contains'),
                    response=step.get('response', 0),
                    repeat=step.get('repeat', 1)
                )
            elif step['type'] == 'prompt':
                mock.add_prompt_rule(
                    pattern=step.get('pattern'),
                    response=step.get('response', True),
                    repeat=step.get('repeat', 1)
                )
        
        return mock


# Predefined scenarios for common test cases
SCENARIOS = {
    'download_simple': InteractionScenario('download_simple')
        .add_step('select', 'Choose first course', response=0)
        .add_step('select', 'Choose first exercise', response=0),
    
    'download_with_navigation': InteractionScenario('download_with_navigation')
        .add_step('select', 'Choose first course', response=0)
        .add_step('select', 'Go back', response=-1)
        .add_step('select', 'Choose second course', response=1)
        .add_step('select', 'Choose first exercise', response=0),
    
    'cleanup_confirm_all': InteractionScenario('cleanup_confirm_all')
        .add_step('prompt', 'Confirm cleanup containers/images', 
                  pattern='containers.*images', response=True)
        .add_step('prompt', 'Confirm cleanup volumes', 
                  pattern='volumes', response=True),
    
    'cleanup_selective': InteractionScenario('cleanup_selective')
        .add_step('prompt', 'Confirm cleanup containers/images', 
                  pattern='containers.*images', response=True)
        .add_step('prompt', 'Decline cleanup volumes', 
                  pattern='volumes', response=False),
    
    'jupyter_select_image': InteractionScenario('jupyter_select_image')
        .add_step('select', 'Choose exercise image', 
                  options_contains=['course1', 'exercise'], response=1),
    
    'complex_workflow': InteractionScenario('complex_workflow')
        .add_step('select', 'Choose course', response=0)
        .add_step('select', 'Choose exercise', response=0)
        .add_step('prompt', 'Confirm download location', response=True)
        .add_step('select', 'Choose jupyter image', response=0)
        .add_step('prompt', 'Open browser', response=True),
}


def create_mock_for_scenario(scenario_name: str) -> MockCutieInteraction:
    """
    Create a mock interaction for a predefined scenario.
    
    Parameters
    ----------
    scenario_name : str
        Name of the scenario from SCENARIOS dict.
    
    Returns
    -------
    MockCutieInteraction
        Configured mock ready for use in tests.
    """
    if scenario_name not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_name}")
    
    return SCENARIOS[scenario_name].to_mock_interaction()
#!/usr/bin/env python
"""
Demonstration of Click's built-in alternatives to cutie functions.

This shows how Click's native functions can replace cutie for better
testability and integration.
"""

import click
from click.testing import CliRunner


# Example: Replacing cutie.prompt_yes_or_no with click.confirm
@click.command()
def example_confirm():
    """Example using click.confirm instead of cutie.prompt_yes_or_no."""
    if click.confirm('Do you want to continue?', default=True):
        click.echo('Continuing...')
    else:
        click.echo('Cancelled.')


# Example: Replacing cutie.select with click.prompt + click.Choice
@click.command()
def example_select():
    """Example using click.prompt with Choice instead of cutie.select."""
    courses = ['Biology', 'Chemistry', 'Physics']
    
    # Method 1: Using click.prompt with type=click.Choice
    selected = click.prompt(
        'Select a course',
        type=click.Choice(courses),
        default='Biology'
    )
    click.echo(f'You selected: {selected}')
    
    # Method 2: Using click.prompt with numbered options
    click.echo('\nSelect a course:')
    for i, course in enumerate(courses, 1):
        click.echo(f'  {i}. {course}')
    
    choice = click.prompt('Enter choice', type=click.IntRange(1, len(courses)))
    selected = courses[choice - 1]
    click.echo(f'You selected: {selected}')


# Example: Replacing cutie.get_number with click.prompt
@click.command()
def example_number():
    """Example using click.prompt for number input."""
    age = click.prompt('Enter your age', type=int, default=25)
    click.echo(f'Your age is: {age}')
    
    # With validation
    score = click.prompt(
        'Enter score (0-100)',
        type=click.IntRange(0, 100)
    )
    click.echo(f'Score: {score}')


# Example: Multi-selection using multiple prompts
@click.command()
def example_multi_select():
    """Example for multi-selection without cutie.select_multiple."""
    options = ['Docker', 'Python', 'Git', 'VSCode']
    selected = []
    
    click.echo('Select tools to install (y/n for each):')
    for option in options:
        if click.confirm(f'  Install {option}?', default=False):
            selected.append(option)
    
    click.echo(f'Selected: {", ".join(selected)}')


# Example: Command with all replacements that's easily testable
@click.command()
@click.option('--course', type=click.Choice(['bio', 'chem', 'phys']), 
              prompt='Select course', help='Course to download')
@click.option('--confirm', is_flag=True, prompt='Confirm download?',
              help='Confirm the download')
def download_exercise(course, confirm):
    """Example download command using Click's built-in prompts."""
    if confirm:
        click.echo(f'Downloading {course} exercises...')
    else:
        click.echo('Download cancelled.')


def test_click_alternatives():
    """Test that Click alternatives work properly."""
    runner = CliRunner()
    
    # Test confirm command
    result = runner.invoke(example_confirm, input='y\n')
    assert 'Continuing' in result.output
    
    result = runner.invoke(example_confirm, input='n\n')
    assert 'Cancelled' in result.output
    
    # Test select command
    result = runner.invoke(example_select, input='Chemistry\n2\n')
    assert 'Chemistry' in result.output
    
    # Test number input
    result = runner.invoke(example_number, input='30\n85\n')
    assert '30' in result.output
    assert '85' in result.output
    
    # Test multi-select
    result = runner.invoke(example_multi_select, input='y\nn\ny\nn\n')
    assert 'Docker' in result.output
    assert 'Git' in result.output
    
    # Test download command with prompts
    result = runner.invoke(download_exercise, input='bio\ny\n')
    assert 'Downloading bio' in result.output
    
    print("All tests passed!")


if __name__ == '__main__':
    # Run tests
    test_click_alternatives()
    
    # Or run individual examples interactively
    # example_confirm()
    # example_select() 
    # example_number()
    # example_multi_select()
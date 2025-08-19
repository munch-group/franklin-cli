"""
CLI wrapper for backend-aware commands.

This module provides Click commands that work with the backend system,
serving as drop-in replacements for existing Franklin commands.
"""

import click
import os
import sys
from typing import Optional, List, Dict, Any
from pathlib import Path

from .factory import BackendFactory, get_backend
from .config import BackendConfig, init_backend_config
from .adapter import GitLabCompatibilityAdapter, ExerciseAdapter


# Backend management commands
@click.group()
def backend():
    """Manage Franklin backend configuration."""
    pass


@backend.command()
@click.option('--type', 'backend_type', 
              type=click.Choice(['gitlab', 'github']),
              default='gitlab',
              help='Backend type to configure')
@click.option('--url', help='GitLab/GitHub Enterprise URL')
@click.option('--token', help='Personal access token')
@click.option('--interactive/--no-interactive', default=True,
              help='Interactive configuration')
def init(backend_type, url, token, interactive):
    """Initialize backend configuration."""
    
    if interactive and not (url and token):
        config = init_backend_config(backend_type, interactive=True)
    else:
        # Create configuration programmatically
        config = BackendConfig.create_default(backend_type)
        
        if url:
            config.set_backend_setting('url', url)
        if token:
            config.set_backend_setting('token', token)
        
        # Save configuration
        save_path = Path.home() / '.franklin' / 'backend.yaml'
        save_path.parent.mkdir(parents=True, exist_ok=True)
        config.save(str(save_path))
        
        click.echo(f"Backend configuration saved to {save_path}")
    
    # Test the configuration
    try:
        backend = get_backend()
        if backend.authenticate({'token': token or os.environ.get(f'{backend_type.upper()}_TOKEN')}):
            user = backend.get_current_user()
            click.secho(f"✓ Successfully authenticated as {user.username}", fg='green')
        else:
            click.secho("✗ Authentication failed", fg='red')
    except Exception as e:
        click.secho(f"✗ Error: {e}", fg='red')


@backend.command()
def show():
    """Show current backend configuration."""
    from .factory import get_backend_config_path
    
    config_path = get_backend_config_path()
    if config_path and config_path.exists():
        click.echo(f"Configuration file: {config_path}")
        click.echo()
        
        with open(config_path, 'r') as f:
            click.echo(f.read())
    else:
        click.echo("No backend configuration found.")
        click.echo("Run 'franklin backend init' to create one.")


@backend.command()
@click.option('--backend', 'backend_type',
              type=click.Choice(['gitlab', 'github']),
              help='Backend to switch to')
def switch(backend_type):
    """Switch between configured backends."""
    config = BackendConfig()
    
    if backend_type:
        # Direct switch
        config.set_backend_type(backend_type)
        config.save()
        click.echo(f"Switched to {backend_type} backend")
    else:
        # Interactive switch
        import cutie
        
        current = config.backend_type
        backends = ['gitlab', 'github']
        
        click.echo(f"Current backend: {current}")
        click.echo("Select new backend:")
        
        selected = cutie.select(backends, selected_index=backends.index(current))
        new_backend = backends[selected]
        
        if new_backend != current:
            config.set_backend_type(new_backend)
            config.save()
            click.echo(f"Switched to {new_backend} backend")
        else:
            click.echo("No change")


@backend.command()
def test():
    """Test backend connection and authentication."""
    try:
        backend = get_backend()
        
        # Test authentication
        click.echo("Testing backend connection...")
        
        if not backend.is_authenticated:
            click.echo("Attempting authentication...")
            token = os.environ.get('GITLAB_TOKEN') or os.environ.get('GITHUB_TOKEN')
            if not backend.authenticate({'token': token}):
                click.secho("✗ Authentication failed", fg='red')
                return
        
        # Get user info
        user = backend.get_current_user()
        click.secho(f"✓ Authenticated as: {user.username} ({user.name})", fg='green')
        
        # Test capabilities
        caps = backend.capabilities
        click.echo("\nBackend capabilities:")
        click.echo(f"  Create users: {caps.create_users}")
        click.echo(f"  Create groups: {caps.create_groups}")
        click.echo(f"  Nested groups: {caps.nested_groups}")
        click.echo(f"  CI/CD: {caps.ci_cd}")
        
        # List repositories
        click.echo("\nTesting repository access...")
        repos = backend.list_repositories()
        click.echo(f"✓ Found {len(repos)} repositories")
        
        click.secho("\nAll tests passed!", fg='green')
        
    except Exception as e:
        click.secho(f"✗ Test failed: {e}", fg='red')
        sys.exit(1)


# Exercise commands that work with any backend
@click.group()
def exercise():
    """Exercise management commands (backend-aware)."""
    pass


@exercise.command()
@click.argument('name')
@click.option('--namespace', help='Namespace/organization for the exercise')
@click.option('--backend', 'backend_type',
              type=click.Choice(['gitlab', 'github']),
              help='Backend to use (overrides config)')
def create(name, namespace, backend_type):
    """Create a new exercise repository."""
    # Get backend
    if backend_type:
        backend = BackendFactory.create_backend(backend_type)
    else:
        backend = get_backend()
    
    adapter = ExerciseAdapter(backend)
    
    try:
        # Authenticate if needed
        if not backend.is_authenticated:
            token = os.environ.get(f'{backend_type or "GITLAB"}_TOKEN')
            backend.authenticate({'token': token})
        
        # Create exercise
        project = adapter.create_exercise(name, namespace=namespace)
        
        click.secho(f"✓ Created exercise: {project['name']}", fg='green')
        click.echo(f"  URL: {project['web_url']}")
        click.echo(f"  Clone: {project['http_url_to_repo']}")
        
    except Exception as e:
        click.secho(f"✗ Failed to create exercise: {e}", fg='red')
        sys.exit(1)


@exercise.command()
@click.argument('url')
@click.option('--target', type=click.Path(), help='Target directory')
@click.option('--backend', 'backend_type',
              type=click.Choice(['gitlab', 'github']),
              help='Backend to use (overrides config)')
def download(url, target, backend_type):
    """Download an exercise from URL."""
    # Get backend
    if backend_type:
        backend = BackendFactory.create_backend(backend_type)
    else:
        backend = get_backend()
    
    adapter = ExerciseAdapter(backend)
    
    try:
        # Authenticate if needed
        if not backend.is_authenticated:
            token = os.environ.get(f'{backend_type or "GITLAB"}_TOKEN')
            backend.authenticate({'token': token})
        
        # Download exercise
        target_path = Path(target) if target else None
        exercise_dir = adapter.download_exercise(url, target_path)
        
        click.secho(f"✓ Downloaded exercise to: {exercise_dir}", fg='green')
        
    except Exception as e:
        click.secho(f"✗ Failed to download exercise: {e}", fg='red')
        sys.exit(1)


# Repository commands
@click.group()
def repo():
    """Repository management commands (backend-aware)."""
    pass


@repo.command()
@click.argument('name')
@click.option('--visibility', 
              type=click.Choice(['public', 'private', 'internal']),
              default='private',
              help='Repository visibility')
@click.option('--description', help='Repository description')
@click.option('--org', '--organization', 'organization',
              help='Organization/namespace')
@click.option('--backend', 'backend_type',
              type=click.Choice(['gitlab', 'github']),
              help='Backend to use (overrides config)')
def create(name, visibility, description, organization, backend_type):
    """Create a new repository."""
    # Get backend
    if backend_type:
        backend = BackendFactory.create_backend(backend_type)
    else:
        backend = get_backend()
    
    try:
        # Authenticate if needed
        if not backend.is_authenticated:
            token = os.environ.get(f'{backend_type or "GITLAB"}_TOKEN')
            backend.authenticate({'token': token})
        
        # Create repository
        repo = backend.create_repository(
            name,
            visibility=visibility,
            description=description,
            organization=organization,
            init_readme=True
        )
        
        click.secho(f"✓ Created repository: {repo.full_name}", fg='green')
        click.echo(f"  URL: {repo.web_url}")
        click.echo(f"  Clone (HTTPS): {repo.clone_url}")
        click.echo(f"  Clone (SSH): {repo.ssh_url}")
        
    except Exception as e:
        click.secho(f"✗ Failed to create repository: {e}", fg='red')
        sys.exit(1)


@repo.command()
@click.option('--owned', is_flag=True, help='Only show owned repositories')
@click.option('--visibility',
              type=click.Choice(['public', 'private', 'internal']),
              help='Filter by visibility')
@click.option('--search', help='Search term')
@click.option('--backend', 'backend_type',
              type=click.Choice(['gitlab', 'github']),
              help='Backend to use (overrides config)')
def list(owned, visibility, search, backend_type):
    """List repositories."""
    # Get backend
    if backend_type:
        backend = BackendFactory.create_backend(backend_type)
    else:
        backend = get_backend()
    
    try:
        # Authenticate if needed
        if not backend.is_authenticated:
            token = os.environ.get(f'{backend_type or "GITLAB"}_TOKEN')
            backend.authenticate({'token': token})
        
        # List repositories
        filters = {}
        if owned:
            filters['owned'] = True
        if visibility:
            filters['visibility'] = visibility
        if search:
            filters['search'] = search
        
        repos = backend.list_repositories(**filters)
        
        if repos:
            click.echo(f"Found {len(repos)} repositories:\n")
            for repo in repos:
                visibility_badge = f"[{repo.visibility.value}]"
                click.echo(f"  {repo.full_name} {visibility_badge}")
                if repo.description:
                    click.echo(f"    {repo.description}")
                click.echo(f"    {repo.web_url}")
                click.echo()
        else:
            click.echo("No repositories found.")
        
    except Exception as e:
        click.secho(f"✗ Failed to list repositories: {e}", fg='red')
        sys.exit(1)


@repo.command()
@click.argument('repo_id')
@click.option('--backend', 'backend_type',
              type=click.Choice(['gitlab', 'github']),
              help='Backend to use (overrides config)')
def info(repo_id, backend_type):
    """Show repository information."""
    # Get backend
    if backend_type:
        backend = BackendFactory.create_backend(backend_type)
    else:
        backend = get_backend()
    
    try:
        # Authenticate if needed
        if not backend.is_authenticated:
            token = os.environ.get(f'{backend_type or "GITLAB"}_TOKEN')
            backend.authenticate({'token': token})
        
        # Get repository
        repo = backend.get_repository(repo_id)
        
        click.echo(f"Repository: {repo.full_name}")
        click.echo(f"  ID: {repo.id}")
        click.echo(f"  Description: {repo.description or 'None'}")
        click.echo(f"  Visibility: {repo.visibility.value}")
        click.echo(f"  Default branch: {repo.default_branch}")
        click.echo(f"  Owner: {repo.owner}")
        click.echo(f"  Created: {repo.created_at}")
        click.echo(f"  Updated: {repo.updated_at}")
        click.echo(f"  Stars: {repo.stars_count}")
        click.echo(f"  Forks: {repo.forks_count}")
        click.echo(f"  Open issues: {repo.open_issues_count}")
        click.echo(f"  Archived: {repo.archived}")
        click.echo(f"\nURLs:")
        click.echo(f"  Web: {repo.web_url}")
        click.echo(f"  Clone (HTTPS): {repo.clone_url}")
        click.echo(f"  Clone (SSH): {repo.ssh_url}")
        
    except Exception as e:
        click.secho(f"✗ Failed to get repository info: {e}", fg='red')
        sys.exit(1)


# Main CLI group that combines all commands
@click.group()
def cli():
    """Franklin backend-aware CLI commands."""
    pass


# Add command groups to main CLI
cli.add_command(backend)
cli.add_command(exercise)
cli.add_command(repo)


# Compatibility wrapper for existing franklin commands
def wrap_existing_command(original_command):
    """
    Wrap an existing Click command to use the backend system.
    
    This allows existing commands to work with the new backend
    without modifying their code.
    """
    @click.pass_context
    def wrapped(ctx, *args, **kwargs):
        # Inject backend adapter into context
        if not hasattr(ctx, 'obj'):
            ctx.obj = {}
        
        # Replace GitLab module with adapter
        ctx.obj['gitlab'] = GitLabCompatibilityAdapter()
        ctx.obj['backend'] = get_backend()
        
        # Call original command
        return original_command(*args, **kwargs)
    
    # Copy command metadata
    wrapped.__name__ = original_command.__name__
    wrapped.__doc__ = original_command.__doc__
    
    return wrapped


if __name__ == '__main__':
    cli()
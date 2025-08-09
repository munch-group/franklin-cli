"""
Migration utilities for transitioning to the backend system.

This module provides tools to migrate existing Franklin configurations
and repositories to the new backend-aware system.
"""

import os
import sys
import yaml
import json
import shutil
import subprocess
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime

import click

from .base import GitBackend, Repository
from .factory import BackendFactory, get_backend
from .config import BackendConfig
from .adapter import GitLabCompatibilityAdapter


class ConfigMigrator:
    """Migrate existing Franklin configuration to backend system."""
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize the migrator.
        
        Parameters
        ----------
        dry_run : bool
            If True, show what would be done without making changes.
        """
        self.dry_run = dry_run
        self.old_config_paths = [
            Path.home() / '.franklin' / 'config.yaml',
            Path.home() / '.franklin' / 'config.yml',
            Path.home() / '.franklin.yaml',
            Path.home() / '.franklin.yml',
            Path.home() / '.config' / 'franklin' / 'config.yaml',
        ]
        self.new_config_path = Path.home() / '.franklin' / 'backend.yaml'
        self.backup_dir = Path.home() / '.franklin' / 'backup'
    
    def find_old_config(self) -> Optional[Path]:
        """Find existing Franklin configuration file."""
        for path in self.old_config_paths:
            if path.exists():
                return path
        return None
    
    def load_old_config(self, path: Path) -> Dict[str, Any]:
        """Load old configuration file."""
        with open(path, 'r') as f:
            if path.suffix in ['.yaml', '.yml']:
                return yaml.safe_load(f) or {}
            else:
                return json.load(f)
    
    def migrate_config(self) -> bool:
        """
        Migrate old configuration to new backend format.
        
        Returns
        -------
        bool
            True if migration successful, False otherwise.
        """
        # Find old configuration
        old_config_path = self.find_old_config()
        if not old_config_path:
            click.echo("No existing Franklin configuration found.")
            return False
        
        click.echo(f"Found configuration at: {old_config_path}")
        
        # Load old configuration
        old_config = self.load_old_config(old_config_path)
        
        # Create new configuration
        new_config = self._convert_config(old_config)
        
        if self.dry_run:
            click.echo("\nNew configuration would be:")
            click.echo(yaml.dump(new_config, default_flow_style=False))
            return True
        
        # Backup old configuration
        self._backup_file(old_config_path)
        
        # Save new configuration
        self.new_config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.new_config_path, 'w') as f:
            yaml.dump(new_config, f, default_flow_style=False)
        
        click.secho(f"✓ Configuration migrated to: {self.new_config_path}", fg='green')
        
        # Optionally remove old configuration
        if click.confirm("Remove old configuration file?"):
            old_config_path.unlink()
            click.echo(f"Removed: {old_config_path}")
        
        return True
    
    def _convert_config(self, old_config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert old configuration format to new backend format."""
        new_config = {
            'backend': {
                'type': 'gitlab',  # Default to GitLab
                'settings': {},
                'defaults': {}
            }
        }
        
        # Extract GitLab settings
        if 'gitlab_url' in old_config:
            new_config['backend']['settings']['url'] = old_config['gitlab_url']
        elif 'gitlab' in old_config and 'url' in old_config['gitlab']:
            new_config['backend']['settings']['url'] = old_config['gitlab']['url']
        else:
            new_config['backend']['settings']['url'] = 'https://gitlab.com'
        
        # Extract token
        if 'gitlab_token' in old_config:
            new_config['backend']['settings']['token'] = old_config['gitlab_token']
        elif 'gitlab' in old_config and 'token' in old_config['gitlab']:
            new_config['backend']['settings']['token'] = old_config['gitlab']['token']
        elif 'GITLAB_TOKEN' in os.environ:
            new_config['backend']['settings']['token'] = '${GITLAB_TOKEN}'
        
        # Extract defaults
        if 'default_visibility' in old_config:
            new_config['backend']['defaults']['visibility'] = old_config['default_visibility']
        elif 'defaults' in old_config and 'visibility' in old_config['defaults']:
            new_config['backend']['defaults']['visibility'] = old_config['defaults']['visibility']
        
        if 'default_branch' in old_config:
            new_config['backend']['defaults']['default_branch'] = old_config['default_branch']
        elif 'defaults' in old_config and 'branch' in old_config['defaults']:
            new_config['backend']['defaults']['default_branch'] = old_config['defaults']['branch']
        
        # Copy any other settings that might be useful
        if 'namespace' in old_config:
            new_config['backend']['defaults']['namespace'] = old_config['namespace']
        
        return new_config
    
    def _backup_file(self, path: Path) -> Path:
        """Create backup of a file."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{path.name}.{timestamp}.backup"
        backup_path = self.backup_dir / backup_name
        
        shutil.copy2(path, backup_path)
        click.echo(f"Backed up to: {backup_path}")
        
        return backup_path


class RepositoryMigrator:
    """Migrate repositories between different backends."""
    
    def __init__(self, source_backend: GitBackend, target_backend: GitBackend,
                 dry_run: bool = False):
        """
        Initialize repository migrator.
        
        Parameters
        ----------
        source_backend : GitBackend
            Source backend to migrate from.
        target_backend : GitBackend
            Target backend to migrate to.
        dry_run : bool
            If True, show what would be done without making changes.
        """
        self.source = source_backend
        self.target = target_backend
        self.dry_run = dry_run
        self.migration_log = []
    
    def migrate_repository(self, repo_id: str, 
                          target_namespace: Optional[str] = None) -> Optional[Repository]:
        """
        Migrate a single repository.
        
        Parameters
        ----------
        repo_id : str
            Repository identifier in source backend.
        target_namespace : Optional[str]
            Target namespace/organization in target backend.
        
        Returns
        -------
        Optional[Repository]
            Created repository in target backend, or None if dry run.
        """
        click.echo(f"\nMigrating repository: {repo_id}")
        
        # Get source repository
        try:
            source_repo = self.source.get_repository(repo_id)
        except Exception as e:
            click.secho(f"✗ Failed to get source repository: {e}", fg='red')
            return None
        
        click.echo(f"  Source: {source_repo.full_name}")
        
        if self.dry_run:
            click.echo(f"  Would create in target: {target_namespace or 'default namespace'}")
            return None
        
        # Create in target backend
        try:
            target_repo = self.target.create_repository(
                name=source_repo.name,
                visibility=source_repo.visibility,
                description=source_repo.description,
                namespace=target_namespace,
                init_readme=False  # We'll copy content
            )
            click.echo(f"  Target: {target_repo.full_name}")
        except Exception as e:
            click.secho(f"✗ Failed to create target repository: {e}", fg='red')
            return None
        
        # Clone and push content
        if not self._transfer_content(source_repo, target_repo):
            click.secho(f"✗ Failed to transfer content", fg='red')
            return None
        
        # Log migration
        self.migration_log.append({
            'source': source_repo.full_name,
            'target': target_repo.full_name,
            'timestamp': datetime.now().isoformat()
        })
        
        click.secho(f"✓ Successfully migrated {source_repo.name}", fg='green')
        return target_repo
    
    def migrate_multiple(self, repo_ids: List[str],
                        target_namespace: Optional[str] = None) -> int:
        """
        Migrate multiple repositories.
        
        Parameters
        ----------
        repo_ids : List[str]
            List of repository identifiers.
        target_namespace : Optional[str]
            Target namespace/organization.
        
        Returns
        -------
        int
            Number of successfully migrated repositories.
        """
        success_count = 0
        
        with click.progressbar(repo_ids, label='Migrating repositories') as bar:
            for repo_id in bar:
                result = self.migrate_repository(repo_id, target_namespace)
                if result:
                    success_count += 1
        
        return success_count
    
    def migrate_all_user_repos(self, target_namespace: Optional[str] = None) -> int:
        """
        Migrate all repositories owned by the authenticated user.
        
        Parameters
        ----------
        target_namespace : Optional[str]
            Target namespace/organization.
        
        Returns
        -------
        int
            Number of successfully migrated repositories.
        """
        # Get all owned repositories from source
        try:
            repos = self.source.list_repositories(owned=True)
        except Exception as e:
            click.secho(f"✗ Failed to list source repositories: {e}", fg='red')
            return 0
        
        click.echo(f"Found {len(repos)} repositories to migrate")
        
        if self.dry_run:
            click.echo("\nRepositories that would be migrated:")
            for repo in repos:
                click.echo(f"  - {repo.full_name}")
            return len(repos)
        
        # Confirm migration
        if not click.confirm(f"Migrate {len(repos)} repositories?"):
            return 0
        
        # Migrate each repository
        repo_ids = [repo.full_name for repo in repos]
        return self.migrate_multiple(repo_ids, target_namespace)
    
    def _transfer_content(self, source_repo: Repository, 
                         target_repo: Repository) -> bool:
        """Transfer repository content via git clone and push."""
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / source_repo.name
            
            try:
                # Clone from source
                click.echo("  Cloning from source...")
                clone_url = source_repo.clone_url
                
                # Add authentication if available
                if hasattr(self.source, 'token') and self.source.token:
                    if 'gitlab' in clone_url:
                        clone_url = clone_url.replace('https://', 
                                                    f'https://oauth2:{self.source.token}@')
                    elif 'github' in clone_url:
                        clone_url = clone_url.replace('https://',
                                                    f'https://{self.source.token}@')
                
                subprocess.run(
                    ['git', 'clone', '--mirror', clone_url, str(repo_path)],
                    check=True,
                    capture_output=True
                )
                
                # Update remote to target
                click.echo("  Pushing to target...")
                push_url = target_repo.clone_url
                
                # Add authentication if available
                if hasattr(self.target, 'token') and self.target.token:
                    if 'gitlab' in push_url:
                        push_url = push_url.replace('https://',
                                                   f'https://oauth2:{self.target.token}@')
                    elif 'github' in push_url:
                        push_url = push_url.replace('https://',
                                                  f'https://{self.target.token}@')
                
                subprocess.run(
                    ['git', 'remote', 'set-url', 'origin', push_url],
                    cwd=repo_path,
                    check=True
                )
                
                # Push all branches and tags
                subprocess.run(
                    ['git', 'push', '--mirror'],
                    cwd=repo_path,
                    check=True,
                    capture_output=True
                )
                
                return True
                
            except subprocess.CalledProcessError as e:
                click.echo(f"  Git error: {e}")
                return False
            except Exception as e:
                click.echo(f"  Error: {e}")
                return False
    
    def save_migration_log(self, path: Optional[Path] = None) -> None:
        """Save migration log to file."""
        if not self.migration_log:
            return
        
        if path is None:
            path = Path.home() / '.franklin' / 'migration_log.yaml'
        
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            yaml.dump(self.migration_log, f, default_flow_style=False)
        
        click.echo(f"Migration log saved to: {path}")


class CodeMigrator:
    """Migrate Franklin code to use the new backend system."""
    
    def __init__(self):
        """Initialize code migrator."""
        self.import_mapping = {
            'from franklin import gitlab': 'from franklin.backends.adapter import gitlab',
            'from franklin.gitlab import': 'from franklin.backends.adapter import',
            'import franklin.gitlab': 'import franklin.backends.adapter as gitlab',
        }
    
    def migrate_file(self, file_path: Path, dry_run: bool = False) -> bool:
        """
        Migrate a Python file to use the new backend system.
        
        Parameters
        ----------
        file_path : Path
            Path to Python file to migrate.
        dry_run : bool
            If True, show changes without modifying file.
        
        Returns
        -------
        bool
            True if file was modified, False otherwise.
        """
        if not file_path.exists() or not file_path.suffix == '.py':
            return False
        
        with open(file_path, 'r') as f:
            original_content = f.read()
        
        modified_content = original_content
        modified = False
        
        # Apply import mappings
        for old_import, new_import in self.import_mapping.items():
            if old_import in modified_content:
                modified_content = modified_content.replace(old_import, new_import)
                modified = True
        
        if modified:
            if dry_run:
                click.echo(f"\nChanges for {file_path}:")
                # Show diff
                import difflib
                diff = difflib.unified_diff(
                    original_content.splitlines(keepends=True),
                    modified_content.splitlines(keepends=True),
                    fromfile=str(file_path),
                    tofile=str(file_path) + ' (migrated)'
                )
                click.echo(''.join(diff))
            else:
                # Backup original
                backup_path = file_path.with_suffix('.py.backup')
                shutil.copy2(file_path, backup_path)
                
                # Write modified content
                with open(file_path, 'w') as f:
                    f.write(modified_content)
                
                click.echo(f"✓ Migrated {file_path}")
                click.echo(f"  Backup: {backup_path}")
        
        return modified
    
    def migrate_directory(self, directory: Path, dry_run: bool = False) -> int:
        """
        Migrate all Python files in a directory.
        
        Parameters
        ----------
        directory : Path
            Directory to scan for Python files.
        dry_run : bool
            If True, show changes without modifying files.
        
        Returns
        -------
        int
            Number of files modified.
        """
        modified_count = 0
        
        for py_file in directory.rglob('*.py'):
            if self.migrate_file(py_file, dry_run):
                modified_count += 1
        
        return modified_count


# CLI commands for migration
@click.group()
def migrate():
    """Migration utilities for transitioning to backend system."""
    pass


@migrate.command()
@click.option('--dry-run', is_flag=True, help='Show what would be done without making changes')
def config(dry_run):
    """Migrate Franklin configuration to backend format."""
    migrator = ConfigMigrator(dry_run=dry_run)
    
    if migrator.migrate_config():
        if not dry_run:
            click.secho("\n✓ Configuration migration complete!", fg='green')
            click.echo("Test the new configuration with: franklin backend test")
    else:
        click.secho("\n✗ Configuration migration failed", fg='red')


@migrate.command()
@click.option('--source-backend', type=click.Choice(['gitlab', 'github']),
              default='gitlab', help='Source backend')
@click.option('--target-backend', type=click.Choice(['gitlab', 'github']),
              default='github', help='Target backend')
@click.option('--source-token', envvar='SOURCE_TOKEN',
              help='Source backend token')
@click.option('--target-token', envvar='TARGET_TOKEN',
              help='Target backend token')
@click.option('--target-namespace', help='Target namespace/organization')
@click.option('--repo', multiple=True, help='Specific repository to migrate')
@click.option('--all-repos', is_flag=True, help='Migrate all owned repositories')
@click.option('--dry-run', is_flag=True, help='Show what would be done without making changes')
def repos(source_backend, target_backend, source_token, target_token,
         target_namespace, repo, all_repos, dry_run):
    """Migrate repositories between backends."""
    
    if source_backend == target_backend:
        click.secho("Source and target backends must be different", fg='red')
        return
    
    # Create backends
    source = BackendFactory.create_backend(source_backend, token=source_token)
    target = BackendFactory.create_backend(target_backend, token=target_token)
    
    # Authenticate
    click.echo("Authenticating with source backend...")
    if not source.authenticate({'token': source_token}):
        click.secho("✗ Failed to authenticate with source backend", fg='red')
        return
    
    click.echo("Authenticating with target backend...")
    if not target.authenticate({'token': target_token}):
        click.secho("✗ Failed to authenticate with target backend", fg='red')
        return
    
    # Create migrator
    migrator = RepositoryMigrator(source, target, dry_run=dry_run)
    
    # Perform migration
    if all_repos:
        count = migrator.migrate_all_user_repos(target_namespace)
    elif repo:
        count = migrator.migrate_multiple(list(repo), target_namespace)
    else:
        click.echo("Specify --all-repos or --repo <name> to migrate")
        return
    
    if not dry_run:
        migrator.save_migration_log()
        click.secho(f"\n✓ Migrated {count} repositories", fg='green')


@migrate.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--dry-run', is_flag=True, help='Show changes without modifying files')
def code(path, dry_run):
    """Migrate Python code to use new backend system."""
    path = Path(path)
    migrator = CodeMigrator()
    
    if path.is_file():
        if migrator.migrate_file(path, dry_run):
            if not dry_run:
                click.secho("✓ File migrated", fg='green')
        else:
            click.echo("No changes needed")
    elif path.is_dir():
        count = migrator.migrate_directory(path, dry_run)
        if count > 0:
            if not dry_run:
                click.secho(f"✓ Migrated {count} files", fg='green')
        else:
            click.echo("No files needed migration")
    else:
        click.secho("Invalid path", fg='red')


if __name__ == '__main__':
    migrate()
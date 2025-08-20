"""
Automatic update system for Franklin packages.

This module provides robust automatic updating functionality for Franklin
and its plugins with comprehensive error handling, retry logic, and
detailed logging for debugging update failures.
"""

import sys
import os
import click
import time
import json
import importlib
import subprocess
import shutil
from subprocess import Popen, PIPE, CalledProcessError
from typing import Tuple, List, Dict, Callable, Any, Optional
from nbformat import versions
from packaging.version import Version, InvalidVersion
from pathlib import Path
from datetime import datetime, timedelta
from importlib.metadata import version, PackageNotFoundError

from . import config as cfg
from . import utils
from . import docker
from . import terminal as term
from . import system
from . import crash
from .crash import crash_report, UpdateCrash
from .logger import logger


# Update configuration
UPDATE_RETRY_ATTEMPTS = 3
UPDATE_RETRY_DELAY = 2  # seconds
UPDATE_CACHE_DURATION = timedelta(hours=6)
UPDATE_STATUS_FILE = Path.home() / '.franklin' / 'update_status.json'


class UpdateStatus:
    """
    Track update status and history for better error recovery.
    
    This class maintains a persistent record of update attempts,
    successes, and failures to enable smarter retry logic and
    provide better debugging information.
    
    Attributes
    ----------
    last_check : datetime
        Timestamp of last update check.
    last_success : datetime
        Timestamp of last successful update.
    failed_attempts : int
        Number of consecutive failed update attempts.
    error_history : List[Dict[str, Any]]
        History of recent errors for debugging.
    """
    
    def __init__(self):
        """Initialize update status tracking."""
        self.status_file = UPDATE_STATUS_FILE
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_status()
    
    def _load_status(self) -> None:
        """Load status from persistent storage."""
        try:
            if self.status_file.exists():
                with open(self.status_file, 'r') as f:
                    data = json.load(f)
                self.last_check = datetime.fromisoformat(data.get('last_check', '1970-01-01'))
                self.last_success = datetime.fromisoformat(data.get('last_success', '1970-01-01'))
                self.failed_attempts = data.get('failed_attempts', 0)
                self.error_history = data.get('error_history', [])
            else:
                self.reset()
        except Exception as e:
            logger.warning(f"Failed to load update status: {e}")
            self.reset()
    
    def reset(self) -> None:
        """Reset status to defaults."""
        self.last_check = datetime(1970, 1, 1)
        self.last_success = datetime(1970, 1, 1)
        self.failed_attempts = 0
        self.error_history = []
    
    def save(self) -> None:
        """Save status to persistent storage."""
        try:
            data = {
                'last_check': self.last_check.isoformat(),
                'last_success': self.last_success.isoformat(),
                'failed_attempts': self.failed_attempts,
                'error_history': self.error_history[-10:]  # Keep last 10 errors
            }
            with open(self.status_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save update status: {e}")
    
    def record_check(self) -> None:
        """Record that an update check was performed."""
        self.last_check = datetime.now()
        self.save()
    
    def record_success(self) -> None:
        """Record successful update."""
        self.last_success = datetime.now()
        self.failed_attempts = 0
        self.save()
    
    def record_failure(self, error: str, details: Dict[str, Any]) -> None:
        """Record failed update attempt.
        
        Parameters
        ----------
        error : str
            Error message describing the failure.
        details : Dict[str, Any]
            Additional details about the failure context.
        """
        self.failed_attempts += 1
        self.error_history.append({
            'timestamp': datetime.now().isoformat(),
            'error': error,
            'details': details,
            'attempt': self.failed_attempts
        })
        self.save()
    
    def should_check_updates(self) -> bool:
        """Determine if updates should be checked.
        
        Returns
        -------
        bool
            True if update check should proceed, False to skip.
        """
        # Always check if never checked before
        if self.last_check.year == 1970:
            return True
        
        # Skip if too many recent failures
        if self.failed_attempts >= 5:
            time_since_success = datetime.now() - self.last_success
            if time_since_success < timedelta(hours=24):
                logger.debug(f"Skipping update check due to {self.failed_attempts} recent failures")
                return False
        
        # Check if cache period has expired
        time_since_check = datetime.now() - self.last_check
        return time_since_check > UPDATE_CACHE_DURATION


def retry_on_failure(func: Callable) -> Callable:
    """
    Decorator to retry operations on failure with exponential backoff.
    
    Parameters
    ----------
    func : Callable
        Function to wrap with retry logic.
    
    Returns
    -------
    Callable
        Wrapped function with retry capability.
    """
    def wrapper(*args, **kwargs):
        last_exception = None
        for attempt in range(UPDATE_RETRY_ATTEMPTS):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < UPDATE_RETRY_ATTEMPTS - 1:
                    delay = UPDATE_RETRY_DELAY * (2 ** attempt)
                    logger.debug(f"Retry {attempt + 1}/{UPDATE_RETRY_ATTEMPTS} after {delay}s: {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"All {UPDATE_RETRY_ATTEMPTS} attempts failed: {e}")
        raise last_exception
    return wrapper


@retry_on_failure
def conda_latest_version(package: str, include_prereleases: bool = False) -> Optional[Version]:
    """
    Get the latest available version of a package from conda.
    
    Parameters
    ----------
    package : str
        Name of the package to check.
    include_prereleases : bool, optional
        Whether to include development versions, by default False.
    
    Returns
    -------
    Optional[Version]
        Latest available version, or None if not found.
    
    Raises
    ------
    UpdateCrash
        If version check fails after retries.
    """
    logger.debug(f"Checking latest conda version for {package} (include_prereleases={include_prereleases})")
    cmd = f'conda search {cfg.conda_channel}::{package} --json'
    output = utils.run_cmd(cmd)
    
    data = json.loads(output)
    if package not in data:
        logger.warning(f"Package {package} not found in channel {cfg.conda_channel}")
        return None
    
    versions = []
    for x in data[package]:
        try:
            # version = Version(x['version'])
            version = x['version']
            # Skip development versions unless explicitly requested
            if not include_prereleases and Version(version).is_prerelease:
                logger.debug(f"Skipping prerelease version {version}")
                continue
            versions.append(version)
        except InvalidVersion:
            logger.debug(f"Skipping invalid version: {x['version']}")
            continue
            
    if not versions:
        logger.warning(f"No {'stable ' if not include_prereleases else ''}update found for {package}")
        return None

    latest = max(versions, key=Version)
    logger.debug(f"Latest {'(including prereleases) ' if include_prereleases else ''}update of {package}: {latest}")
    return latest
        



def conda_update(package: str, status: UpdateStatus, include_prereleases: bool = False) -> bool:
    """
    Update a package using conda with comprehensive error handling.
    
    Parameters
    ----------
    package : str
        Name of the package to update.
    status : UpdateStatus
        Update status tracker for error recording.
    include_prereleases : bool, optional
        Whether to include development versions, by default False.
    
    Returns
    -------
    bool
        True if package was updated, False if already up to date.
    
    Raises
    ------
    UpdateCrash
        If update fails after retries.
    """
    logger.info(f"Checking for updates to {package} (include_prereleases={include_prereleases})")
    
    # logger.info(f"Checking for pixi updates to {package} (global={is_global})")
    term.secho(f"Checking for conda updates to {package}")


    try:
        current_version = system.package_version(package)
        if current_version is None:
            logger.warning(f"Package {package} not currently installed")
            return False
            
        latest_version = conda_latest_version(package, include_prereleases=include_prereleases)
        if latest_version is None:
            return False
            
        if latest_version <= Version(current_version):
            logger.debug(f"{package} is up to date (current: {current_version})")
            return False
        
        logger.info(f"Updating {package} from {current_version} to {latest_version}")
        
        # Perform the update
        cmd = f'conda install -y -c conda-forge {cfg.conda_channel}::{package}={latest_version}'
        logger.debug(f"Running: {cmd}")
        
        try:
            utils.run_cmd(cmd)
            logger.info(f"Successfully updated {package} to {latest_version}")
            
            # Verify the update
            new_version = system.package_version(package)
            if new_version != str(latest_version):
                logger.warning(f"Version mismatch after update: expected {latest_version}, got {new_version}")
            
            docker.config_fit()
            return True
            
        except CalledProcessError as e:
            error_details = {
                'package': package,
                'current_version': current_version,
                'target_version': str(latest_version),
                'command': cmd,
                'error': str(e)
            }
            status.record_failure(f"conda install failed for {package}", error_details)
            
            raise UpdateCrash(
                f"Failed to update {package} from {current_version} to {latest_version}",
                "The conda install command failed. This may be due to:",
                "  - Network connectivity issues",
                "  - Conda environment conflicts",
                "  - Package dependency problems",
                "",
                "To update manually, run:",
                f"  conda update -y -c conda-forge -c {cfg.conda_channel} {package}",
                "",
                "For more details, check the log file: franklin.log"
            )
            
    except Exception as e:
        if not isinstance(e, UpdateCrash):
            logger.exception(f"Unexpected error updating {package}")
            status.record_failure(f"Unexpected error: {type(e).__name__}", {'package': package, 'error': str(e)})
        raise


def conda_reinstall(package: str, status: UpdateStatus, include_prereleases: bool = False) -> bool:
    """
    Force reinstall a package using conda.
    
    Parameters
    ----------
    package : str
        Name of the package to reinstall.
    status : UpdateStatus
        Update status tracker for error recording.
    include_prereleases : bool, optional
        Whether to include development versions, by default False.
    
    Returns
    -------
    bool
        True if package was reinstalled with a new version.
    """
    logger.info(f"Force reinstalling {package} (include_prereleases={include_prereleases})")
    
    try:
        current_version = system.package_version(package)
        latest_version = conda_latest_version(package, include_prereleases=include_prereleases)
        
        if latest_version and (current_version is None or latest_version > Version(current_version)):
            cmd = f'conda install -y -c conda-forge -c {cfg.conda_channel} --force-reinstall {package}'
            logger.debug(f"Running: {cmd}")
            
            utils.run_cmd(cmd)
            logger.info(f"Successfully reinstalled {package}")
            
            docker.config_fit()
            return True
            
    except Exception as e:
        logger.error(f"Failed to reinstall {package}: {e}")
        status.record_failure(f"Reinstall failed for {package}", {'package': package, 'error': str(e)})
        # Don't raise here - reinstall failures are less critical
        
    return False


def installed_version(package: str) -> Optional[Version]:
    """
    Get the installed version of a package in pixi environment.
    
    Parameters
    ----------
    package : str
        Name of the package to check.
    
    Returns
    -------
    Optional[Version]
        Installed version, or None if not found.
    """

    try:
        return str(version(package))
    except PackageNotFoundError:
        return None


@retry_on_failure
def pixi_update(package: str, status: UpdateStatus, is_global: bool = False, include_prereleases: bool = False) -> bool:
    """
    Update a package using pixi with error handling.
    
    Parameters
    ----------
    package : str
        Name of the package to update.
    status : UpdateStatus
        Update status tracker for error recording.
    is_global : bool, optional
        Whether package is globally installed, by default False.
    include_prereleases : bool, optional
        Whether to include development versions, by default False.
    
    Returns
    -------
    bool
        True if package was updated.
    """
    # logger.info(f"Checking for pixi updates to {package} (global={is_global})")
    term.secho(f"Checking for {'global' if is_global else 'local'} pixi updates to {package}")
    
    before_version = installed_version(package)
    after_version = conda_latest_version(package, include_prereleases=include_prereleases)

    if before_version == after_version:
        logger.debug(f"{package} is already up to date (global)")
        return False
    if is_global:
        output = utils.run_cmd(f'pixi global install -c munch-group -c conda-forge "{package}=={after_version}"')
        return installed_version(package) == after_version
    else:
        # Local package update
        # First check if we're in a pixi project
        if not os.path.exists('pixi.toml'):
            # This shouldn't happen as we detect installation method before calling this
            # But if it does, try global update as fallback
            raise UpdateCrash(f"Not global and no poxi.toml in folder...")

            # logger.warning(f"Not in a pixi project directory but package marked as local. Trying global update...")
            # logger.debug(f"Fallback to global install")
            # output = utils.run_cmd(f'pixi global install -c munch-group -c conda-forge {package}={after_version}')

        cmd = f'pixi add "{package}=={after_version}"'
        result = subprocess.run(cmd, check=True, shell=True, capture_output=True, text=True)
        
        after_version == installed_version(package)
        
        if before_version != after_version:
            logger.info(f"Updated {package} from {before_version} to {after_version}")
            return True


def update_client_conda(status: UpdateStatus, include_prereleases: bool = False) -> int:
    """
    Update Franklin and plugins using conda.
    
    Parameters
    ----------
    status : UpdateStatus
        Update status tracker.
    include_prereleases : bool, optional
        Whether to include development versions, by default False.
    
    Returns
    -------
    int
        Number of packages updated.
    """
    updated_count = 0
    
    # Update core franklin package
    try:
        if conda_update('franklin-cli', status, include_prereleases=include_prereleases):
            updated_count += 1
    except UpdateCrash:
        # Re-raise to let caller handle
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating franklin: {e}")
        raise
    
    # Update plugins if installed
    for plugin in ['franklin-educator', 'franklin-admin']:
        try:
            # Check if plugin is installed
            importlib.import_module(plugin.replace('-', '_'))
            
            # Try to reinstall plugin for compatibility
            if conda_reinstall(plugin, status, include_prereleases=include_prereleases):
                updated_count += 1
                
        except ModuleNotFoundError:
            logger.debug(f"Plugin {plugin} not installed, skipping")
            continue
        except Exception as e:
            logger.warning(f"Failed to update plugin {plugin}: {e}")
            # Don't fail entire update if plugin update fails
            
    return updated_count


def update_client_pixi(status: UpdateStatus, include_prereleases: bool = False, is_global: bool = False) -> int:
    """
    Update Franklin and plugins using pixi.
    
    Parameters
    ----------
    status : UpdateStatus
        Update status tracker.ca
    
    Returns
    -------
    int
        Number of packages updated.
    """
    updated_count = 0
    
    # # Check if Franklin is globally installed
    # franklin_install = detect_installation_method('franklin')
    # is_global = franklin_install == 'pixi-global'
    
    # Update core franklin package
    try:
        if pixi_update('franklin-cli', status, is_global=is_global, include_prereleases=include_prereleases):
            updated_count += 1
    except UpdateCrash:
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating franklin-cli: {e}")
        raise

    # Update plugins if installed
    for plugin in ['franklin-educator', 'franklin-admin']:
        try:
            # Check if plugin is installed
            importlib.import_module(plugin.replace('-', '_'))
            
            # Check if plugin is globally installed
            plugin_install = detect_installation_method(plugin)
            plugin_is_global = plugin_install == 'pixi-global'
            
            # Update plugin
            if pixi_update(plugin, status, is_global=plugin_is_global, include_prereleases=include_prereleases):
                updated_count += 1
                
        except ModuleNotFoundError:
            logger.debug(f"Plugin {plugin} not installed, skipping")
            continue
        except Exception as e:
            logger.warning(f"Failed to update plugin {plugin}: {e}")
            
    return updated_count


def detect_installation_method(package: str = 'franklin-cli') -> str:
    """
    Detect how a package was installed (conda or pixi).
    
    Parameters
    ----------
    package : str, optional
        Package name to check, by default 'franklin-cli'.
    
    Returns
    -------
    str
        Installation method: 'conda', 'pixi', 'pixi-global', or 'unknown'.
    """

    bin_dir = Path(shutil.which('franklin')).parent
    is_global = bin_dir.parents[2] == Path().home() / '.pixi'

    is_pixi = '.pixi' in str(bin_dir)
    is_conda  = (bin_dir / 'conda').exists()

    if is_pixi and is_conda:
        raise UpdateCrash(f"{package} detected as both pixi and conda")
    if is_pixi:
        if is_global:
            logger.debug(f"Detected global pixi installation for {package}")
            return 'pixi-global'
        else:
            logger.debug(f"Detected local pixi installation for {package}")
            return 'pixi'
    elif is_conda:
        logger.debug(f"Detected global conda installation for {package}")
        return 'conda'
    else:
        raise UpdateCrash(
            f"Could not determine installation method for {package}. "
            "Please ensure it is installed via pixi or conda."
        )


def  _update(include_prereleases: bool = False) -> int:
    """
    Internal update function with proper installation method detection.
    
    Parameters
    ----------
    include_prereleases : bool, optional
        Whether to include development versions, by default False.
    
    Returns
    -------
    int
        Number of packages updated.
    """
    status = UpdateStatus()
    
    # Check if we should skip update check
    if not status.should_check_updates():
        logger.debug("Skipping update check (too recent or too many failures)")
        return 0
    
    status.record_check()
    
    # Detect how franklin was installed
    installation_method = detect_installation_method('franklin-cli')
    logger.info(f"Detected installation method for franklin-cli: {installation_method}")
    logger.debug(f"Python executable: {sys.executable}")
    
    if installation_method == 'unknown':
        # Fall back to environment detection
        if '.pixi' in sys.executable or '/.pixi/' in sys.executable:
            logger.warning('Franklin installation method unknown, using pixi based on environment')
            installation_method = 'pixi'
        else:
            logger.warning('Franklin installation method unknown, using conda based on environment')
            installation_method = 'conda'
    
    # Use the appropriate update method matching the installation
    logger.info(f'Franklin was installed with {installation_method}')
    if installation_method == 'pixi-global':
        updated_count = update_client_pixi(status, include_prereleases=include_prereleases, is_global=True)
    elif installation_method == 'pixi':
        updated_count = update_client_pixi(status, include_prereleases=include_prereleases, is_global=False)
    elif installation_method == 'conda':
        updated_count = update_client_conda(status, include_prereleases=include_prereleases)
    else:
        raise UpdateCrash("This should not happen - unknown installation method detected")
    
    if updated_count > 0:
        status.record_success()
        logger.info(f"Successfully updated {updated_count} packages")
    
    return updated_count


@crash_report
@system.internet_ok
def update_packages(include_prereleases: bool = False) -> None:
    """
    Update Franklin packages with user feedback.
    
    This is the main entry point for automatic updates, called
    during Franklin startup. It checks for updates and provides
    appropriate user feedback.
    
    Parameters
    ----------
    include_prereleases : bool, optional
        Whether to include development versions, by default False.
    
    Raises
    ------
    SystemExit
        If updates were installed (exit code 1 to restart).
    """
    logger.debug(f'Starting automatic update check (include_prereleases={include_prereleases})')
    
    try:
        updated_count = _update(include_prereleases=include_prereleases)
        
        if updated_count > 0:
            term.echo()
            term.secho(
                f'Franklin updated {updated_count} package{"s" if updated_count > 1 else ""} - Please run your command again',
                fg='green'
            )
            term.echo()
            sys.exit(1)
        else:
            logger.debug('No updates available')
            
    except UpdateCrash as e:
        # UpdateCrash provides user-friendly messages
        term.echo()
        term.secho('Update failed:', fg='red', bold=True)
        term.secho(str(e), fg='red')
        term.echo()
        # Don't exit - let user continue with current version
        
    except Exception as e:
        # Unexpected errors
        logger.exception('Unexpected error during update')
        term.echo()
        term.secho('Update check failed due to unexpected error', fg='yellow')
        term.secho('Franklin will continue with the current version', fg='yellow')
        term.echo()
        # Don't exit - let user continue


@click.command()
@click.option('--prereleases', is_flag=True, hidden=True, help='Include development versions')
def update(prereleases: bool) -> None:
    """Update Franklin packages manually.
    
    This command forces an update check even if one was recently performed.
    It's useful for testing or when users want to ensure they have the
    latest version.
    """
    # Reset status to force update check
    status = UpdateStatus()
    status.reset()
    status.save()
    
    # Run update with user feedback
    if prereleases:
        term.secho("Checking for updates (including prerelease versions)...", fg='blue')
    else:
        term.secho("Checking for stable updates...", fg='blue')
    update_packages(include_prereleases=prereleases)
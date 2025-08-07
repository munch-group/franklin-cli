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
from subprocess import Popen, PIPE, CalledProcessError
from typing import Tuple, List, Dict, Callable, Any, Optional
from packaging.version import Version, InvalidVersion
from pathlib import Path
from datetime import datetime, timedelta

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
def conda_latest_version(package: str, include_dev: bool = False) -> Optional[Version]:
    """
    Get the latest available version of a package from conda.
    
    Parameters
    ----------
    package : str
        Name of the package to check.
    include_dev : bool, optional
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
    try:
        logger.debug(f"Checking latest conda version for {package} (include_dev={include_dev})")
        cmd = f'conda search {cfg.conda_channel}::{package} --json'
        output = utils.run_cmd(cmd)
        
        data = json.loads(output)
        if package not in data:
            logger.warning(f"Package {package} not found in channel {cfg.conda_channel}")
            return None
        
        versions = []
        for x in data[package]:
            try:
                version = Version(x['version'])
                # Skip development versions unless explicitly requested
                if not include_dev and version.is_devrelease:
                    logger.debug(f"Skipping development version {version}")
                    continue
                versions.append(version)
            except InvalidVersion:
                logger.debug(f"Skipping invalid version: {x['version']}")
                continue
                
        if not versions:
            logger.warning(f"No {'stable ' if not include_dev else ''}versions found for {package}")
            return None
            
        latest = max(versions)
        logger.debug(f"Latest {'(including dev) ' if include_dev else ''}version of {package}: {latest}")
        return latest
        
    except (CalledProcessError, json.JSONDecodeError) as e:
        logger.error(f"Failed to get latest version for {package}: {e}")
        raise UpdateCrash(
            f"Failed to check latest version of {package}",
            "This may be a temporary network issue. Franklin will retry automatically.",
            "",
            "To check manually, run:",
            f"  conda search {cfg.conda_channel}::{package}"
        )


def conda_update(package: str, status: UpdateStatus, include_dev: bool = False) -> bool:
    """
    Update a package using conda with comprehensive error handling.
    
    Parameters
    ----------
    package : str
        Name of the package to update.
    status : UpdateStatus
        Update status tracker for error recording.
    include_dev : bool, optional
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
    logger.info(f"Checking for updates to {package} (include_dev={include_dev})")
    
    try:
        current_version = system.package_version(package)
        if current_version is None:
            logger.warning(f"Package {package} not currently installed")
            return False
            
        latest_version = conda_latest_version(package, include_dev=include_dev)
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


def conda_reinstall(package: str, status: UpdateStatus, include_dev: bool = False) -> bool:
    """
    Force reinstall a package using conda.
    
    Parameters
    ----------
    package : str
        Name of the package to reinstall.
    status : UpdateStatus
        Update status tracker for error recording.
    include_dev : bool, optional
        Whether to include development versions, by default False.
    
    Returns
    -------
    bool
        True if package was reinstalled with a new version.
    """
    logger.info(f"Force reinstalling {package} (include_dev={include_dev})")
    
    try:
        current_version = system.package_version(package)
        latest_version = conda_latest_version(package, include_dev=include_dev)
        
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


def pixi_installed_version(package: str) -> Optional[Version]:
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
        # First check if we're in a pixi environment with the package
        # Use --global flag to check global pixi packages
        try:
            # Try global pixi first (where Franklin is likely installed)
            output = subprocess.check_output(
                'pixi global list --json', 
                shell=True, text=True, stderr=subprocess.DEVNULL
            )
            packages = json.loads(output)
            
            # Check if package is in global list
            if isinstance(packages, dict) and 'environments' in packages:
                # New pixi format with environments
                for env_name, env_data in packages['environments'].items():
                    if 'packages' in env_data:
                        for pkg in env_data['packages']:
                            if pkg == package or (isinstance(pkg, dict) and pkg.get('name') == package):
                                logger.debug(f"Package {package} found in pixi global environment {env_name}")
                                # Get version from pixi info
                                try:
                                    info_output = subprocess.check_output(
                                        f'pixi global info {package}',
                                        shell=True, text=True, stderr=subprocess.DEVNULL
                                    )
                                    # Parse version from info output
                                    for line in info_output.split('\n'):
                                        if 'version' in line.lower():
                                            version_str = line.split(':')[-1].strip()
                                            return Version(version_str)
                                except:
                                    pass
            elif isinstance(packages, list):
                # Old pixi format
                for pkg in packages:
                    if isinstance(pkg, dict) and pkg.get('name') == package:
                        return Version(pkg['version'])
        except (CalledProcessError, json.JSONDecodeError):
            logger.debug("No global pixi packages found")
        
        # If not in global, check local project environment
        # But only if we're actually in a pixi environment
        if '.pixi' in sys.executable:
            try:
                output = subprocess.check_output(
                    'pixi list --json', 
                    shell=True, text=True, stderr=subprocess.DEVNULL
                )
                packages = json.loads(output)
                
                for pkg in packages:
                    if isinstance(pkg, dict) and pkg.get('name') == package:
                        return Version(pkg['version'])
            except (CalledProcessError, json.JSONDecodeError) as e:
                logger.debug(f"Failed to check local pixi environment: {e}")
                
        logger.debug(f"Package {package} not found in pixi environment")
        return None
        
    except (InvalidVersion, Exception) as e:
        logger.error(f"Failed to get pixi version for {package}: {e}")
        return None


@retry_on_failure
def pixi_update(package: str, status: UpdateStatus, is_global: bool = False) -> bool:
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
    
    Returns
    -------
    bool
        True if package was updated.
    """
    logger.info(f"Checking for pixi updates to {package} (global={is_global})")
    
    try:
        before_version = pixi_installed_version(package)
        
        if is_global:
            # For global packages, use pixi global update
            cmd = f'pixi global update "{package}"'
            logger.debug(f"Running: {cmd}")
            result = subprocess.run(cmd, check=True, shell=True, capture_output=True, text=True)
            
            # Check if update actually happened by parsing output
            if 'already up-to-date' in result.stdout.lower() or 'already up to date' in result.stdout.lower():
                logger.debug(f"{package} is already up to date")
                return False
            elif 'updated' in result.stdout.lower() or 'updating' in result.stdout.lower():
                logger.info(f"Successfully updated global {package}")
                return True
            else:
                # Try to detect version change
                after_version = pixi_installed_version(package)
                if before_version != after_version:
                    logger.info(f"Updated {package} from {before_version} to {after_version}")
                    return True
                else:
                    logger.debug(f"{package} appears to be up to date")
                    return False
        else:
            # Local package update
            # First check if we're in a pixi project
            if not os.path.exists('pixi.toml'):
                logger.warning(f"Not in a pixi project directory, cannot update local {package}")
                return False
                
            # Run pixi upgrade
            cmd = f'pixi upgrade "{package}"'
            logger.debug(f"Running: {cmd}")
            subprocess.run(cmd, check=True, shell=True, capture_output=True, text=True)
            
            # Run pixi install to ensure consistency
            subprocess.run('pixi install', check=True, shell=True, capture_output=True, text=True)
            
            after_version = pixi_installed_version(package)
            
            if before_version != after_version:
                logger.info(f"Updated {package} from {before_version} to {after_version}")
                return True
            else:
                logger.debug(f"{package} is up to date")
                return False
            
    except CalledProcessError as e:
        error_details = {
            'package': package,
            'command': cmd if 'cmd' in locals() else 'unknown',
            'error': str(e),
            'stdout': e.stdout if hasattr(e, 'stdout') else '',
            'stderr': e.stderr if hasattr(e, 'stderr') else '',
            'is_global': is_global
        }
        status.record_failure(f"pixi {'global ' if is_global else ''}update failed for {package}", error_details)
        
        if is_global:
            raise UpdateCrash(
                f"Failed to update {package} using pixi global",
                "The pixi global update command failed.",
                "",
                "To update manually, run:",
                f"  pixi global update {package}"
            )
        else:
            raise UpdateCrash(
                f"Failed to update {package} using pixi",
                "The pixi upgrade command failed.",
                "",
                "To update manually, run:",
                f"  pixi upgrade {package}",
                "  pixi install"
            )


def update_client_conda(status: UpdateStatus, include_dev: bool = False) -> int:
    """
    Update Franklin and plugins using conda.
    
    Parameters
    ----------
    status : UpdateStatus
        Update status tracker.
    include_dev : bool, optional
        Whether to include development versions, by default False.
    
    Returns
    -------
    int
        Number of packages updated.
    """
    updated_count = 0
    
    # Update core franklin package
    try:
        if conda_update('franklin', status, include_dev=include_dev):
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
            if conda_reinstall(plugin, status, include_dev=include_dev):
                updated_count += 1
                
        except ModuleNotFoundError:
            logger.debug(f"Plugin {plugin} not installed, skipping")
            continue
        except Exception as e:
            logger.warning(f"Failed to update plugin {plugin}: {e}")
            # Don't fail entire update if plugin update fails
            
    return updated_count


def update_client_pixi(status: UpdateStatus) -> int:
    """
    Update Franklin and plugins using pixi.
    
    Parameters
    ----------
    status : UpdateStatus
        Update status tracker.
    
    Returns
    -------
    int
        Number of packages updated.
    """
    updated_count = 0
    
    # Check if Franklin is globally installed
    franklin_install = detect_installation_method('franklin')
    is_global = franklin_install == 'pixi-global'
    
    # Update core franklin package
    try:
        if pixi_update('franklin', status, is_global=is_global):
            updated_count += 1
    except UpdateCrash:
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
            if pixi_update(plugin, status, is_global=plugin_is_global):
                updated_count += 1
                
        except ModuleNotFoundError:
            logger.debug(f"Plugin {plugin} not installed, skipping")
            continue
        except Exception as e:
            logger.warning(f"Failed to update plugin {plugin}: {e}")
            
    return updated_count


def detect_installation_method(package: str = 'franklin') -> str:
    """
    Detect how a package was installed (conda or pixi).
    
    Parameters
    ----------
    package : str, optional
        Package name to check, by default 'franklin'.
    
    Returns
    -------
    str
        Installation method: 'conda', 'pixi', 'pixi-global', or 'unknown'.
    """
    # Check if in a local pixi project directory (but not for Franklin)
    if os.path.exists('pixi.toml') and package == 'franklin':
        logger.debug("In pixi project directory, but checking for Franklin installation method")
    
    try:
        # Check pixi global installation first
        try:
            output = subprocess.check_output(
                'pixi global list --json', 
                shell=True, text=True, stderr=subprocess.DEVNULL
            )
            packages = json.loads(output)
            
            # Check if package is globally installed
            if isinstance(packages, dict) and 'environments' in packages:
                for env_name, env_data in packages['environments'].items():
                    if 'packages' in env_data:
                        for pkg in env_data['packages']:
                            if pkg == package or (isinstance(pkg, dict) and pkg.get('name') == package):
                                logger.debug(f"{package} found in pixi global environment")
                                return 'pixi-global'
        except:
            pass
        
        # Then check local pixi environment
        pixi_version = pixi_installed_version(package)
        if pixi_version is not None:
            logger.debug(f"{package} found in pixi environment (version {pixi_version})")
            
            # Double-check it's not also in conda (shouldn't happen but good to verify)
            try:
                conda_info = subprocess.check_output(
                    f'conda list "^{package}$" --json', 
                    shell=True, text=True, stderr=subprocess.DEVNULL
                )
                conda_packages = json.loads(conda_info)
                if conda_packages:
                    logger.warning(f"{package} found in both pixi and conda - using pixi")
            except:
                pass
                
            return 'pixi'
    except Exception as e:
        logger.debug(f"Error checking pixi installation: {e}")
    
    try:
        # Check if package exists in conda environment
        conda_info = subprocess.check_output(
            f'conda list "^{package}$" --json', 
            shell=True, text=True, stderr=subprocess.DEVNULL
        )
        conda_packages = json.loads(conda_info)
        
        if conda_packages:
            # Package found in conda
            logger.debug(f"{package} found in conda environment")
            # Check if it's from the expected channel
            for pkg in conda_packages:
                if pkg['name'] == package:
                    channel = pkg.get('channel', 'unknown')
                    logger.debug(f"{package} installed from channel: {channel}")
                    return 'conda'
    except Exception as e:
        logger.debug(f"Error checking conda installation: {e}")
    
    # Check pip as fallback (development install)
    try:
        pip_info = subprocess.check_output(
            [sys.executable, '-m', 'pip', 'show', package],
            stderr=subprocess.DEVNULL, text=True
        )
        if pip_info:
            logger.debug(f"{package} found via pip (likely development install)")
            # For pip installs, fall back to environment detection
            if '.pixi' in sys.executable:
                return 'pixi'
            else:
                return 'conda'
    except:
        pass
    
    logger.warning(f"Could not determine installation method for {package}")
    return 'unknown'


def _update(include_dev: bool = False) -> int:
    """
    Internal update function with proper installation method detection.
    
    Parameters
    ----------
    include_dev : bool, optional
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
    
    try:
        # Detect how franklin was installed
        installation_method = detect_installation_method('franklin')
        
        if installation_method == 'unknown':
            # Fall back to environment detection
            if '.pixi' in sys.executable:
                logger.warning('Franklin installation method unknown, using pixi based on environment')
                installation_method = 'pixi'
            else:
                logger.warning('Franklin installation method unknown, using conda based on environment')
                installation_method = 'conda'
        
        # Use the appropriate update method
        if installation_method in ['pixi', 'pixi-global']:
            logger.info(f'Franklin was installed with {installation_method}, using pixi for updates')
            # Note: Pixi doesn't have dev versions in the same way, so we ignore include_dev for pixi
            updated_count = update_client_pixi(status)
        else:
            logger.info('Franklin was installed with conda, using conda for updates')
            updated_count = update_client_conda(status, include_dev=include_dev)
        
        if updated_count > 0:
            status.record_success()
            logger.info(f"Successfully updated {updated_count} packages")
        
        return updated_count
        
    except Exception as e:
        # Record failure for any unhandled exceptions
        if not isinstance(e, UpdateCrash):
            status.record_failure(
                f"Unhandled exception: {type(e).__name__}",
                {'error': str(e), 'executable': sys.executable, 
                 'installation_method': locals().get('installation_method', 'unknown')}
            )
        raise


@crash_report
@system.internet_ok
def update_packages(include_dev: bool = False) -> None:
    """
    Update Franklin packages with user feedback.
    
    This is the main entry point for automatic updates, called
    during Franklin startup. It checks for updates and provides
    appropriate user feedback.
    
    Parameters
    ----------
    include_dev : bool, optional
        Whether to include development versions, by default False.
    
    Raises
    ------
    SystemExit
        If updates were installed (exit code 1 to restart).
    """
    logger.debug(f'Starting automatic update check (include_dev={include_dev})')
    
    try:
        updated_count = _update(include_dev=include_dev)
        
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
@click.option('--dev', is_flag=True, hidden=True, help='Include development versions')
def update(dev: bool) -> None:
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
    if dev:
        term.secho("Checking for Franklin updates (including development versions)...", fg='blue')
    else:
        term.secho("Checking for Franklin updates...", fg='blue')
    update_packages(include_dev=dev)
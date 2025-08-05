import os
import sys
import platform
import socket
import click
from packaging.version import Version
from importlib.metadata import version as _version
import re
import shutil
import shlex
import subprocess
import time
import requests
from functools import wraps
from typing import List, Dict, Any, Callable, Optional, Union

from .logger import logger
from . import config as cfg
from . import terminal as term


###########################################################
# Checks
###########################################################

# def port_in_use(port, host='127.0.0.1'):
def port_in_use(port: int, host: str = '0.0.0.0') -> bool:
    """
    Check if a network port is currently in use.

    This function attempts to bind to a socket on the specified host and port
    to determine if the port is available for use.

    Parameters
    ----------
    port : int
        The port number to check (1-65535).
    host : str, default='0.0.0.0'
        The host address to check the port on.
        '0.0.0.0' checks all available interfaces.

    Returns
    -------
    bool
        True if the port is in use (bind fails), False if available.

    Examples
    --------
    >>> port_in_use(8080)
    False
    >>> # Start a server on port 8080, then:
    >>> port_in_use(8080)
    True

    Notes
    -----
    - Uses TCP socket binding test
    - Temporarily creates and closes a socket
    - May give false negatives on some systems with port reuse
    - Host '0.0.0.0' binds to all available network interfaces
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False  # Port is not in use
        except OSError:
            return True   # Port is in use


def package_version(pack: str) -> Optional[str]:
    """
    Get the version of an installed Python package.

    This function queries the package metadata to retrieve the version
    of a locally installed package, with proper error handling.

    Parameters
    ----------
    pack : str
        The package name to get the version for.

    Returns
    -------
    Optional[str]
        The package version string if found, None if package not found
        or version cannot be determined.

    Examples
    --------
    >>> package_version('franklin')
    '1.2.3'
    >>> package_version('nonexistent-package')
    None

    Notes
    -----
    - Uses importlib.metadata for package version lookup
    - Returns parsed Version object converted to string
    - Handles missing packages gracefully by returning None
    - Works with any installed Python package, not just Franklin
    """
    try:
        return str(Version(_version(pack)))
    except Exception:
        return None
    

def is_wsl(v: str = platform.uname().release) -> int:
    """
    Detect if Python is running in Windows Subsystem for Linux.

    This function analyzes the system release string to determine if the
    current environment is running under WSL and which version.

    Parameters
    ----------
    v : str, default=platform.uname().release
        The system release string to analyze. Defaults to current system.

    Returns
    -------
    int
        WSL version number:
        - 0: Not running in WSL
        - 1: Running in WSL 1
        - 2: Running in WSL 2

    Examples
    --------
    >>> is_wsl('4.4.0-19041-Microsoft')
    1
    >>> is_wsl('5.4.72-microsoft-standard-WSL2')
    2
    >>> is_wsl('5.4.0-42-generic')
    0

    Notes
    -----
    - WSL 1 releases end with '-Microsoft'
    - WSL 2 releases end with 'microsoft-standard-WSL2'
    - Regular Linux systems return 0
    - Used to adjust Franklin behavior for WSL environments
    """
    if v.endswith("-Microsoft"):
        return 1
    elif v.endswith("microsoft-standard-WSL2"):
        return 2
    return 0


def wsl_available() -> Union[int, bool]:
    """
    Detect if Windows Subsystem for Linux is available from Windows.

    This function checks if WSL is installed and accessible from a Windows
    environment by attempting to run a command in WSL.

    Returns
    -------
    Union[int, bool]
        WSL version if available (1 or 2), False if not available.
        - False: WSL not available or not on Windows
        - 1: WSL 1 is available
        - 2: WSL 2 is available

    Examples
    --------
    >>> # On Windows with WSL 2 installed
    >>> wsl_available()
    2
    >>> # On Windows without WSL
    >>> wsl_available()
    False
    >>> # On Linux/macOS
    >>> wsl_available()
    False

    Notes
    -----
    - Only meaningful on Windows systems
    - Requires 'wsl' command to be available in PATH
    - Tests WSL by running 'uname -r' command
    - Has 15-second timeout for WSL command execution
    - Returns False on any subprocess error
    """
    if os.name != "nt" or not shutil.which("wsl"):
        return False
    try:
        return is_wsl(
            subprocess.check_output(
                ["wsl", "uname", "-r"], text=True, timeout=15
            ).strip()
        )
    except subprocess.SubprocessError:
        return False


def system() -> str:
    """
    Determine the operating system and environment Franklin is running on.

    This function provides a unified way to detect the runtime environment,
    with special handling for WSL environments that behave differently
    from native Windows or Linux.

    Returns
    -------
    str
        System name indicating the runtime environment:
        - 'Windows': Native Windows
        - 'WSL': Windows Subsystem for Linux v1
        - 'WSL2': Windows Subsystem for Linux v2
        - 'Linux': Native Linux
        - 'Darwin': macOS

    Examples
    --------
    >>> system()
    'Darwin'
    >>> # On WSL 2
    >>> system()
    'WSL2'

    Notes
    -----
    - Uses platform.system() as base detection
    - Enhances Windows detection with WSL version detection
    - Critical for Franklin's cross-platform compatibility
    - Used throughout Franklin to adjust system-specific behavior
    - WSL detection prevents treating WSL as native Linux
    """
    plat = platform.system()
    if plat == 'Windows':
        wsl = is_wsl()
        if wsl == 0:
            return 'Windows'
        if wsl == 1:
            return 'WSL'
        if wsl == 2:
            return 'WSL2'
    return plat


###########################################################
# Resources
###########################################################

def jupyter_ports_in_use() -> List[int]:
    """
    Get a list of ports currently in use by running Jupyter servers.

    This function queries the Jupyter server list to find all currently
    running Jupyter instances and extracts their port numbers.

    Returns
    -------
    List[int]
        List of port numbers (integers) currently used by Jupyter servers.
        Empty list if no Jupyter servers are running.

    Examples
    --------
    >>> jupyter_ports_in_use()
    [8888, 8889]
    >>> # If no Jupyter servers running
    >>> jupyter_ports_in_use()
    []

    Notes
    -----
    - Uses 'jupyter server list' command to get running servers
    - Extracts port numbers from localhost URLs in output
    - Requires Jupyter to be installed and accessible
    - May raise subprocess errors if Jupyter command fails
    - Used by Franklin to find available ports for new instances

    Warnings
    --------
    This function contains duplicate regex parsing code that may cause
    incorrect results. The second regex overwrites the first.
    """
        
    cmd = 'jupyter server list'
    cmd = shlex.split(cmd)
    cmd[0] = shutil.which(cmd[0])
    output = subprocess.check_output(cmd).decode()
    occupied_ports = [
        int(x) for x in re.findall(r'(?<=->)\d+', output, re.MULTILINE)
        ]
    occupied_ports = [
        int(x) for x in re.findall(r'(?<=localhost:)\d+', output, re.MULTILINE)
        ]
    return occupied_ports


def check_internet_connection() -> bool:
    """
    Check if there is an active internet connection.

    This function tests internet connectivity by attempting to reach
    Docker Hub. If the connection fails, it displays an error message
    and exits the application.

    Returns
    -------
    bool
        True if internet connection is available.
        Never returns False - exits application on connection failure.

    Examples
    --------
    >>> check_internet_connection()
    True
    >>> # On connection failure, exits with sys.exit(1)

    Notes
    -----
    - Tests connection to https://hub.docker.com/
    - Uses 10-second timeout for connection attempt
    - Logs successful connections to debug log
    - Displays red error message on failure
    - Calls sys.exit(1) on connection failure
    - Essential for Franklin operations requiring internet access

    Warnings
    --------
    This function never returns False - it exits the application
    on connection failure. The return type annotation may be misleading.
    """
    try:
        request = requests.get("https://hub.docker.com/", timeout=10)    
        logger.debug("Internet connection OK.")
        return True
    except (requests.ConnectionError, requests.Timeout) as exception:
        term.secho(
            "No internet connection. Please check your network.", fg='red')
        sys.exit(1)
        return False


def internet_ok(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to ensure internet connectivity before function execution.

    This decorator wraps functions that require internet access and
    automatically checks connectivity before allowing execution.
    If no internet is available, it displays a helpful message and exits.

    Parameters
    ----------
    func : Callable[..., Any]
        The function to be decorated that requires internet access.

    Returns
    -------
    Callable[..., Any]
        The decorated function that checks internet before execution.

    Examples
    --------
    >>> @internet_ok
    ... def download_something():
    ...     # This function will only run if internet is available
    ...     pass

    Notes
    -----
    - Tests connection to https://hub.docker.com/ with 10-second timeout
    - Shows boxed informational message on connection failure
    - Exits application with sys.exit(1) if no internet
    - Logs successful connections to debug log
    - Useful for update and download operations
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            request = requests.get("https://hub.docker.com/", timeout=10)    
            logger.debug("Internet connection OK.")
        except (requests.ConnectionError, requests.Timeout) as exception:
            term.boxed_text(
                f"No internet", 
                ['Franklin needs an internet connection to update'],
                fg='blue')
            sys.exit(1)
        return func(*args, **kwargs)
    return wrapper



def gb_free_disk() -> float:
    """
    Get the amount of free disk space in gigabytes.

    This function queries the filesystem to determine available disk space
    on the root partition and converts it to gigabytes.

    Returns
    -------
    float
        Available disk space in gigabytes (GB).

    Examples
    --------
    >>> gb_free_disk()
    123.45

    Notes
    -----
    - Checks free space on root filesystem ('/')
    - Converts bytes to GB using 1024^3 conversion
    - On Windows/WSL, this may check the root of the current drive
    - Used by Franklin to ensure sufficient space for Docker operations
    - Values are floating point for precision
    """
    return shutil.disk_usage('/').free / 1024**3


def fake_progress_bar(label: str) -> None:
    """
    Display a fake progress bar for user experience enhancement.

    This function creates a visual progress bar that runs for approximately
    1 second to provide user feedback during quick operations that would
    otherwise appear instantaneous.

    Parameters
    ----------
    label : str
        The label text to display alongside the progress bar.

    Returns
    -------
    None
        This function performs UI operations and has no return value.

    Examples
    --------
    >>> fake_progress_bar('Checking disk space:')
    # Displays: Checking disk space: [████████████████████] 100%

    Notes
    -----
    - Uses click.progressbar for consistent UI styling
    - Runs for exactly 1 second (100 steps × 0.01s)
    - Label is left-justified using configuration setting
    - Applies Franklin's progress bar styling options
    - Purely cosmetic - provides no actual progress tracking
    """
        label = label.ljust(cfg.pg_ljust)
        with click.progressbar(label=label, length=100, **cfg.pg_options) as b:
            for i in range(100):
                time.sleep(0.01)
                b.update(1)


def check_free_disk_space() -> None:
    """
    Check if there is sufficient free disk space to run Franklin.

    This function validates available disk space against Franklin's
    requirements and provides appropriate user feedback. It can exit
    the application if space is critically low or warn users about
    low space conditions.

    Returns
    -------
    None
        This function performs checks and may exit the application.

    Examples
    --------
    >>> check_free_disk_space()
    # If sufficient space: displays progress bar and confirmation
    # If low space: shows warning with cleanup suggestions
    # If insufficient: exits with error message

    Notes
    -----
    Behavior based on available space:
    - < required GB: Shows error message and exits with sys.exit(1)
    - < 2× required GB: Shows warning with option to continue or exit
    - ≥ 2× required GB: Shows confirmation with fake progress bar
    
    The function provides:
    - Cleanup suggestions via 'franklin docker remove'
    - Interactive choice to continue or stop when space is low
    - Visual feedback with progress bar when space is adequate
    - Clear indication of space requirements vs. available space

    Warnings
    --------
    This function may call sys.exit(1) and terminate the application
    if disk space is insufficient or user chooses to stop.
    """

    gb_free = gb_free_disk()
    if gb_free < cfg.required_gb_free_disk:
        term.secho(f"Not enough free disk space. Required: "
                   f"{cfg.required_gb_free_disk} GB,"
                   f"Available: {gb_free:.2f} GB", fg='red')
        sys.exit(1)
    elif gb_free < 2 * cfg.required_gb_free_disk:

        term.boxed_text('You are running low on disk space', [
            f'You are running low on disk space. Franklin needs '
            f'{cfg.required_gb_free_disk} GB of free disk space to run and '
            f'you only have {gb_free:.2f} GB left.',
            '',
            'You can use "franklin docker remove" to remove cached Docker '
            'content you no longer need. it automatically get downloaded '
            'if you should need it again',
            ], fg='blue')        
        if click.confirm(
            "Do you want to stop to free up space?", default=False):
            sys.exit(1)

    else:
        term.echo()
        fake_progress_bar('Checking disk space:')
        
        term.echo(f"Free disk space:", nl=False)
        term.secho(f" {gb_free:.1f} Gb", fg='green', bold=True, nl=False)

        term.echo(f" (Franklin needs", nl=False)
        term.secho(f" {cfg.required_gb_free_disk:.1f} Gb", nl=False, bold=True)
        term.echo(f" to run)")



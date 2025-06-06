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
from typing import List, Dict, Any, Callable

from .logger import logger
from . import config as cfg
from . import terminal as term


###########################################################
# Checks
###########################################################

# def port_in_use(port, host='127.0.0.1'):
def port_in_use(port, host='0.0.0.0'):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False  # Port is not in use
        except OSError:
            return True   # Port is in use


def package_version(pack) -> str:
    """
    Get the version of the locally installed franklin package.
    """
    try:
        return Version(_version(pack))
    except:
        return None
    

def is_wsl(v: str = platform.uname().release) -> int:
    """
    Detects if Python is running in WSL
    """
    if v.endswith("-Microsoft"):
        return 1
    elif v.endswith("microsoft-standard-WSL2"):
        return 2
    return 0


def wsl_available() -> int:
    """
    Detect if Windows Subsystem for Linux is available from Windows
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


def system():
    """
    Determine the system the code is running on.

    Returns
    -------
    :
        System name. Either: 'Windows', 'WSL', 'WSL2', 'Linux', or 'Darwin'
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

def jupyter_ports_in_use():
    """
    Get a list of ports in use by Jupyter servers.

    Returns
    -------
    :
        List of ports in use.
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


def check_internet_connection():
    """
    Check if there is an internet connection.

    Returns
    -------
    :
        True if there is an internet connection, False otherwise
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


def internet_ok(func: Callable) -> Callable:
    """
    Decorator for functions that require internet.

    Parameters
    ----------
    func : 
        Function.

    Returns
    -------
    :
        Decorated function.
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



def gb_free_disk():
    """
    Get the amount of free disk space in GB.

    Returns
    -------
    :
        Free disk space in GB.
    """
    return shutil.disk_usage('/').free / 1024**3


def fake_progress_bar(label):
        label = label.ljust(cfg.pg_ljust)
        with click.progressbar(label=label, length=100, **cfg.pg_options) as b:
            for i in range(100):
                time.sleep(0.01)
                b.update(1)


def check_free_disk_space():
    """
    Checks if there is enough free disk space to run Franklin, and exits if 
    there is not.
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



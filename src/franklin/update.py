
import sys
import os
import click
from subprocess import Popen, PIPE
from .crash import crash_report
from . import crash
from . import system

from . import config as cfg
from . import utils
from . import docker
from . import terminal as term
import subprocess
from typing import Tuple, List, Dict, Callable, Any
from packaging.version import Version, InvalidVersion
import json

from . import config as cfg
from . import utils


def conda_latest_version(package) -> Version:
    output = utils.run_cmd(f'conda search munch-group::{package} --json')
    latest = max(Version(x['version']) for x in json.loads(output)[package])    
    return latest


def conda_update(package) -> None:
    """
    Update the package.
    """
    channel = cfg.conda_channel
    try:
        latest = conda_latest_version(package)
        if latest > system.package_version(package):
            term.secho(f'{package} is updating to version {latest}')
            cmd = f'conda install -y -c conda-forge {channel}::{package}={latest}'
            utils.run_cmd(cmd)
        docker.config_fit()
    except:
        raise crash.UpdateCrash(
            f'{package} update failed!',
            'Please run the following command to update manually:',
            '',
            f'  conda update -y -c conda-forge -c munch-group {package}')  
    

def conda_update_client() -> None:
    """
    Update the Franklin client.
    """
    conda_update('franklin')
    try:
        import franklin_educator 
    except ModuleNotFoundError:
        return
    conda_update('franklin-educator')
    

def pixi_update(package: str) -> None:
    """
    Update the package using Pixi.
    """
    try:
        cmd = f'pixi update {package}'
        utils.run_cmd(cmd)
        cmd = 'pixi install'
        utils.run_cmd(cmd)
    except:
        raise crash.UpdateCrash(
            f'{package} update failed!',
            'Please run the following command to update manually:',
            '',
            f'  pixi update {package}')  


def pixi_update_client() -> None:
    """
    Update the Franklin client.
    """
    pixi_update('franklin')
    try:
        import franklin_educator 
    except ModuleNotFoundError:
        return
    pixi_update('franklin-educator')


def _update():
    """Update Franklin
    """    
    if '.pixi' in sys.executable:
        pixi_update_client()
    else:
        conda_update_client()


@click.command()
@crash_report
def update():
    """Update Franklin
    """    
    _update()

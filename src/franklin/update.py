
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
    updated = False
    try:
        latest = conda_latest_version(package)
        if latest > system.package_version(package):
            # term.secho(f'{package} is updating to version {latest}')
            cmd = f'conda install -y -c conda-forge {channel}::{package}={latest}'
            utils.run_cmd(cmd)
            updated = True
        docker.config_fit()
    except:
        raise crash.UpdateCrash(
            f'{package} update failed!',
            'Please run the following command to update manually:',
            '',
            f'  conda update -y -c conda-forge -c munch-group {package}')  
    return updated

def conda_update_client() -> None:
    """
    Update the Franklin client.
    """
    updated = conda_update('franklin')
    try:
        import franklin_educator 
    except ModuleNotFoundError:
        return updated
    updated += conda_update('franklin-educator')
    return updated
    

def pixi_installed_version(package) -> Version:
    output = utils.check_output(f'pixi list --json').decode('utf-8')
    for x in json.loads(output):
        if x['name'] == package:
            return Version(x['version'])
    else:
        raise crash.UpdateCrash(
            f'{package} is not installed.',
            'Please run the following command to install it:',
            '',
            f'  pixi install {package}')
        

def pixi_update(package: str) -> None:
    """
    Update the package using Pixi.
    """
    updated = False
    try:
        before = system.package_version(package)
        cmd = f'pixi update {package}'
        utils.run_cmd(cmd)
        cmd = 'pixi install'
        utils.run_cmd(cmd)

        before = system.package_version(package)

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
    before = pixi_installed_version('franklin')
    pixi_update('franklin')
    updated = before == pixi_installed_version('franklin')

    try:
        import franklin_educator 
    except ModuleNotFoundError:
        return
    before = pixi_installed_version('franklin-educator')
    pixi_update('franklin-educator')
    updated += before == pixi_installed_version('franklin-educator')
    return updated


def _update():
    """Update Franklin
    """    
    if '.pixi' in sys.executable:
        updated = pixi_update_client()
    else:
        updated = conda_update_client()
    if updated:
        term.secho('Franklin was updated - Please run your command again', fg='green')
        sys.exit()


@click.command()
@crash_report
def update():
    """Update Franklin
    """ 
    _update()

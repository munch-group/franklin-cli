
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
from .logger import logger


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
    logger.debug(f'Checking for updates to {package}')
    try:
        latest = conda_latest_version(package)
        if latest > system.package_version(package):
            cmd = f'conda install -y -c conda-forge {channel}::{package}={latest}'
            utils.run_cmd(cmd)
            updated = True
            logger.debug(f'Updated {package}')
        docker.config_fit()
    except:
        raise crash.UpdateCrash(
            f'{package} update failed!',
            'Please run the following command to update manually:',
            '',
            f'  conda update -y -c conda-forge -c munch-group {package}')  
    return updated


def conda_reinstall(package) -> None:
    """
    Reinstall the package.
    """
    channel = cfg.conda_channel
    updated = False
    logger.debug(f'Checking for updates to {package}')
    try:

        latest = conda_latest_version(package)
        if latest > system.package_version(package):        
            cmd = f'conda install -y -c conda-forge -c munch-group --force-reinstall {package}'
            utils.run_cmd(cmd)
            updated = True
            logger.debug(f'Reinstalled {package}')
        docker.config_fit()
    except:
        raise crash.UpdateCrash(
            f'{package} reinstall failed!',
            'Please run the following command to update manually:',
            '',
            f'  conda install -y -c conda-forge -c munch-group --force-reinstall {package}'
            )  
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
    updated += conda_reinstall('franklin-educator')
    return updated
    

def pixi_installed_version(package) -> Version:
    output = subprocess.check_output(f'pixi list --json', shell=True)
    output = output.decode('utf-8')
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
    logger.debug(f'Checking for updates to {package}')
    try:
        before = system.package_version(package)
        cmd = f'pixi upgrade {package}'
        utils.run_cmd(cmd, shell=True)
        cmd = 'pixi install'
        utils.run_cmd(cmd, shell=True)

        if before != pixi_installed_version(package):
            updated = True
            logger.debug(f'Updated {package}')

    except:
        raise crash.UpdateCrash(
            f'{package} update failed!',
            'Please run the following command to update manually:',
            '',
            f'  pixi upgrade {package}')  

    return updated

def pixi_reinstall(package: str) -> None:
    """
    Reinstall the package using Pixi.
    """
    updated = False
    try:
        before = system.package_version(package)
        cmd = f'pixi remove {package}'
        utils.run_cmd(cmd, shell=True)
        cmd = f'pixi add {package}'
        utils.run_cmd(cmd, shell=True)
        cmd = 'pixi install'
        utils.run_cmd(cmd, shell=True)

        if before != pixi_installed_version(package):
            updated = True
            logger.debug(f'Reinstalled {package}')
    except:
        raise crash.UpdateCrash(
            f'{package} reinstall failed!',
            'Please run the following three commands to update manually:',
            '',
            f'  pixi remove {package}'
            '',
            f'  pixi add {package}'
            '',
            f'  pixi install {package}'
            )  


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
    pixi_reinstall('franklin-educator')
    updated += before == pixi_installed_version('franklin-educator')
    return updated

def _update():
    """Update Franklin
    """    
    if '.pixi' in sys.executable:
        logger.debug('Using pixi for update check')
        updated = pixi_update_client()
    else:
        logger.debug('Using conda for update check')
        updated = conda_update_client()
    if updated:
        logger.debug('Franklin was updated')
    return updated

@crash_report
@system.internet_ok
def update_packages():
    """Update Franklin
    """ 
    term.secho('Checking for updates')
    if _update():
        logger.debug('Franklin was updated')
        term.echo()
        term.secho('Franklin was updated - Please run your command again', fg='green')
        term.echo()        
        sys.exit(1)
    else:
        logger.debug('No updates available')
        term.echo()
        term.secho('No updates available')

@click.command()
def update() -> None:
    """Update Franklin
    """
    update_packages()

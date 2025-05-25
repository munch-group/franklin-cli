
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


def latest_version(package) -> Version:
    output = utils.run_cmd(f'conda search munch-group::{package} --json')
    latest = max(Version(x['version']) for x in json.loads(output)[package])    
    return latest


def update_client() -> None:
    """
    Update the Franklin client.
    """
    try:
        package = 'franklin'
        latest = latest_version(package)
        if latest > system.package_version(package):
            term.secho(f'{package} is updating to {latest}', fg='green')
            cmd = f'conda install -y -c conda-forge {cfg.conda_channel}::{package}={latest}'
            utils.run_cmd(cmd)
        docker.config_fit()
    except:
        raise crash.UpdateCrash(
            'Franklin update failed!',
            'Please run the following command to update manually:',
            '',
            '  conda update -y -c conda-forge -c munch-group franklin')        

    try:
        import franklin_educator 
    except ModuleNotFoundError:
        return

    try:
        package = 'franklin-educator'
        latest = latest_version(package)
        if latest > system.package_version(package):
            term.secho(f'{package} is updating to {latest}', fg='green')
            utils.run_cmd(f'conda install -y -c conda-forge {cfg.conda_channel}::{package}={latest}')
        docker.config_fit()
    except:
        raise crash.UpdateCrash(
            'Franklin update failed!',
            'Please run the following command to update manually:',
            '',
            '  conda update -y -c conda-forge -c munch-group franklin-educator')
    

@click.command('update')
@crash_report
def update():
    """Update Franklin
    """    
    update_client()

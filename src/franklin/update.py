
import sys
import os
import click
from subprocess import Popen, PIPE
from .utils import logger, crash_report, config_gitui
from . import config as cfg
from . import utils
from . import docker
from . import terminal as term
import subprocess
from typing import Tuple, List, Dict, Callable, Any
from packaging.version import Version, InvalidVersion

from . import config as cfg
from . import utils

def install_latest_conda_version(package) -> Version:
    """
    Get the newest version of the franklin package from the conda channel.
    """
    logger.debug(f"Getting latest version of {package} from conda channel")
    cmd = f'conda search -c {cfg.conda_channel} {package}'
    output = utils.run_cmd(cmd)
    version = output.strip().splitlines()[-1].split()[1]

    utils.run_cmd(f'conda install -y -c conda-forge -c {cfg.conda_channel} franklin={version}')
        
    return Version(version)


def update_client() -> None:
    """
    Update the Franklin client.
    """
    franklin_version = None
    try:
        franklin_version = utils.package_version('franklin')
        # Update franklin client
        click.secho('Checking for updates to franklin', fg='green')
        try:
            utils.run_cmd(f"conda update -y -c conda-forge -c munch-group franklin", timeout=120)
        except subprocess.TimeoutExpired:
            logger.debug("Update timed out, trying to install latest version")
        except utils.Crash:
            logger.debug("Update failed, trying to install latest version")
            install_latest_conda_version('franklin')
    except KeyboardInterrupt:
        raise click.Abort()
    except:
        raise utils.UpdateCrash(
            'Franklin update failed!',
            'Please run the following command to update manually:',
            '',
            '  conda update -y -c conda-forge -c munch-group franklin')
    
    # Update franklin-educator plugin
    franklin_educator_version = None
    try:
        import franklin_educator 

        franklin_educator_version = utils.package_version('franklin-educator')
        click.secho('Checking for updates to franklin-educator', fg='green')
        try:
            utils.run_cmd(f"conda update -y -c conda-forge -c munch-group franklin-educator", timeout=120)
        except subprocess.TimeoutExpired:
            logger.debug("Update timed out, trying to install latest version")
        except utils.Crash:
            logger.debug("Update failed, trying to install latest version")
            install_latest_conda_version('franklin-educator')

    except ModuleNotFoundError:
        # skip gracefully if not installed
        pass
    except:
        raise utils.UpdateCrash(
            'Franklin update failed!',
            'Please run the following command to update manually:',
            '',
            '  conda update -y -c conda-forge -c munch-group franklin-educator')
    
    # update settings 
    if (franklin_version is not None and franklin_version != utils.package_version('franklin')) or \
        (franklin_educator_version is not None and franklin_educator_version != utils.package_version('franklin-educator')):

        if utils.is_educator():
            if click.confirm(f"Reset to recommended Docker settings fitted to your machine resources?", default=True):
                docker.config_fit()

#        if click.confirm(f"Reset to recommended Git settings?", default=True):
            config_gitui()




@click.command('update')
@crash_report
def update():
    """Update the Franklin client.
    """    
    update_client()

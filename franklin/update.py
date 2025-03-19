
import sys
import click
from subprocess import Popen, PIPE
from .utils import logger, crash_report
from .config import ANACONDA_CHANNEL
from . import utils
from . import docker
from . import terminal as term
from typing import Tuple, List, Dict, Callable, Any

def update_client() -> None:
    """
    Update the Franklin client.
    """
    version = utils.franklin_version()
    click.secho('Checking for Franklin update:', fg='green')
    cmd = f"conda update -y -c conda-forge -c {ANACONDA_CHANNEL} franklin"
    
    logger.debug(cmd)
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    if stdout:
        [logger.debug(x) for x in stdout.decode().splitlines()]
    if stderr:
        [logger.debug(x) for x in stderr.decode().splitlines()]
    if p.returncode:
        term.secho('\nCould not update client', fg='red')
        logger.debug(f"Update failed with return code {p.returncode}")
        if stderr and 'PackageNotInstalledError' in stderr.decode():
            msg = f"""\n\n
            The package is not installed as a conda package in this environment.
            """
            term.echo("\n\nPlease install the package with the following command:")                
            term.echo(f"\n\n  conda install {ANACONDA_CHANNEL}::franklin\n\n")
        sys.exit()

    term.secho(f"Resetting to default settings and fitting them to your machine.")
    docker.config_fit()

    new_version = utils.franklin_version()
    if new_version == version:
        term.secho(f"Franklin is running the newest version: {new_version}")
    else:
        term.echo(f"Franklin was updated from version {version} to {new_version} and exits to get a fresh start.")
        click.echo(f"Please run your command again.")
        sys.exit()


@click.command('update')
@crash_report
def update():
    """Update the Franklin client.
    """    
    update_client(update=True)

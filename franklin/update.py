
import sys
import click
from subprocess import Popen, PIPE
from .utils import logger, crash_report
from .config import ANACONDA_CHANNEL, MAINTAINER_EMAIL
from . import utils
from importlib.metadata import version as _version

def franklin_version():
    try:
        return _version('franklin')
    except:
        return None

def _update_client(update):
    if not update:
        logger.debug('Update check skipped')
    else:
        version = franklin_version()
        click.secho('Checking for Franklin update:', nl=False, fg='green')
        # cmd = f"{os.environ['CONDA_EXE']} update -y -c {ANACONDA_CHANNEL} --no-update-deps franklin"
        cmd = f"conda update -y -c {ANACONDA_CHANNEL} --no-update-deps franklin"
        logger.debug(cmd)
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        if stdout:
            [logger.debug(x) for x in stdout.decode().splitlines()]
        if stderr:
            [logger.debug(x) for x in stderr.decode().splitlines()]
        if p.returncode:
            logger.debug(f"Update failed with return code {p.returncode}")

            if stderr and 'PackageNotInstalledError' in stderr.decode():
                msg = f"""
                The package is not installed as a conda package in this environment.
                Please install the package with the following command:
                
                conda install -c {ANACONDA_CHANNEL} franklin
                """
                click.echo(msg)
            msg = f"""
            Could not update client.
            """
            utils.secho(msg, fg='red')
            sys.exit()
        click.echo('done')
        new_version = franklin_version()
        if new_version == version:
            utils.secho(f"Franklin is running the newest version.")
        else:
            utils.echo(f"Franklin was updated from version {version} to {new_version} and exits to get a fresh start.")
            click.echo(f"Please run your command again.")



@click.command('update')
@crash_report
def update():
    """Update the Franklin client."""    
    _update_client(update=True)

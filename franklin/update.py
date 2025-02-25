
import sys
import click
from subprocess import Popen, PIPE
from .utils import logger
from .config import ANACONDA_CHANNEL, MAINTAINER_EMAIL
from . import utils

def _update_client(update):
    if not update:
        logger.debug('Update check skipped')
    else:
        click.echo('Updating franklin...', nl=False)
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


@click.command('update')
def update():
    """Update the Franklin client."""    
    _update_client(update=True)

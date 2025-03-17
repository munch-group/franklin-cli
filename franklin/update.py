
import sys
import click
from subprocess import Popen, PIPE
from .utils import logger, crash_report
from .config import ANACONDA_CHANNEL, MAINTAINER_EMAIL
from . import utils
from . import docker as _docker

def _update_client(update):
    if not update:
        logger.debug('Update check skipped')
    else:
        version = utils.franklin_version()
        click.secho('Checking for Franklin update:', nl=False, fg='green')
        # cmd = f"{os.environ['CONDA_EXE']} update -y -c {ANACONDA_CHANNEL} --no-update-deps franklin"
        cmd = f"conda update -y -c conda-forge -c {ANACONDA_CHANNEL} --no-update-deps franklin"
        
        logger.debug(cmd)
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        if stdout:
            [logger.debug(x) for x in stdout.decode().splitlines()]
        if stderr:
            [logger.debug(x) for x in stderr.decode().splitlines()]
        if p.returncode:
            utils.secho('\nCould not update client', fg='red')
            logger.debug(f"Update failed with return code {p.returncode}")
            if stderr and 'PackageNotInstalledError' in stderr.decode():
                msg = f"""\n\n
                The package is not installed as a conda package in this environment.
                """
                utils.echo("\n\nPlease install the package with the following command:")                
                utils.echo(f"\n\n  conda install {ANACONDA_CHANNEL}::franklin\n\n")
            sys.exit()
        click.echo('done')

        utils.secho(f"Resetting to default settings and fitting them to your machine.")
        _docker._config_fit()

    # with docker_config() as cfg:
    #     if not cfg.settings:
    #         # user settings emtpy
    #         _config_fit()

        new_version = utils.franklin_version()
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

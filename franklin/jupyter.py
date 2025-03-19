import sys
import os
import re
import logging
import shlex
import time
import webbrowser
import logging
import subprocess
import click
import shutil
import time
from subprocess import Popen, PIPE, STDOUT
from . import utils
from .utils import AliasedGroup, crash_report
from .gitlab import select_image
from . import docker as _docker
from .logger import logger
from .update import update_client
from . import terminal as term

banner = """
        ▗▄▄▄▖▗▄▄▖  ▗▄▖ ▗▖  ▗▖▗▖ ▗▖▗▖   ▗▄▄▄▖▗▖  ▗▖
        ▐▌   ▐▌ ▐▌▐▌ ▐▌▐▛▚▖▐▌▐▌▗▞▘▐▌     █  ▐▛▚▖▐▌
        ▐▛▀▀▘▐▛▀▚▖▐▛▀▜▌▐▌ ▝▜▌▐▛▚▖ ▐▌     █  ▐▌ ▝▜▌
        ▐▌   ▐▌ ▐▌▐▌ ▐▌▐▌  ▐▌▐▌ ▐▌▐▙▄▄▖▗▄█▄▖▐▌  ▐▌
"""


@click.group(cls=AliasedGroup)
def jupyter():
    """Jupyter commands"""
    pass


@click.option("--allow-subdirs-at-your-own-risk/--no-allow-subdirs-at-your-own-risk",
                default=False,
                help="Allow subdirs in current directory mounted by Docker.")
@click.option('--update/--no-update', default=True,
                help="Override check for package updates")
@jupyter.command('run')
@crash_report
def _run(allow_subdirs_at_your_own_risk: bool, update: str) -> None:
    """Run Jupyter notebook in a Docker container.
    """

    term.check_window_size()

    click.clear()
    logger.debug('####################################################################')
    logger.debug('########################## FRANKLIN START ##########################')
    logger.debug('####################################################################')
    for line in banner.splitlines():
        term.secho(line, nowrap=True, center=True, fg='green', log=False)

    term.echo()
    term.echo('"Science and everyday life cannot and should not be separated"', center=True)
    term.echo("Rosalind D. Franklin", center=True)
    term.echo()

    if not allow_subdirs_at_your_own_risk:
        for x in os.listdir(os.getcwd()):
            if os.path.isdir(x) and x not in ['.git', '.ipynb_checkpoints']:
                term.secho("\n  Please run the command in a directory without any sub-directories.\n", fg='red')
                sys.exit(1)

    utils.check_internet_connection()
    utils.logger.debug('Starting Docker Desktop')
    _docker.failsafe_start_docker_desktop()
    utils.check_free_disk_space()
    time.sleep(2)

    if update:
        update_client(update)
    else:
        logger.debug('Update check skipped')

    image_url = select_image()

    term.secho("Downloading/updating image:".ljust(23), fg='green')
    _docker.pull(image_url)
    term.echo()    

    term.secho('Starting container:', fg='green')
    run_container_id, docker_run_p, port = _docker.failsafe_run_container(image_url)

    cmd = f"docker logs --follow {run_container_id}"
    if utils.system() == "Windows":
        popen_kwargs = dict(creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        popen_kwargs = dict(start_new_session = True)
    docker_log_p = Popen(shlex.split(cmd), stdout=PIPE, stderr=STDOUT, bufsize=1, universal_newlines=True, **popen_kwargs)

    while True:
        time.sleep(0.1)
        line = docker_log_p.stdout.readline()
        if line:
            logger.debug('JUPYTER: '+line.strip())
        # line = docker_p_nice_stdout.readline().decode()
        match= re.search(r'https?://127.0.0.1\S+', line)
        if match:
            token_url = match.group(0)
            # replace port in token_url
            token_url = re.sub(r'(?<=127.0.0.1:)\d+', port, token_url)
            docker_log_p.stdout.close()
            docker_log_p.terminate()
            docker_log_p.wait()
            break

    webbrowser.open(token_url, new=1)

    term.secho(f'\nJupyter is running and should open in your default browser.', fg='green')
    term.echo(f'If not, you can access it at this URL:')
    term.echo(f'{token_url}', nowrap=True)

    while True:
        term.secho('\nPress Q to shut down jupyter and close application', fg='green')
        c = click.getchar()
        click.echo()
        if c.upper() == 'Q':

            term.secho('Shutting down container', fg='red') 
            sys.stdout.flush()
            _docker.kill_container(run_container_id)
            docker_run_p.terminate()
            docker_run_p.wait()
            term.secho('Shutting down Docker Desktop', fg='yellow') 
            sys.stdout.flush()
            _docker.docker_desktop_stop()
            term.secho('Service has stopped.', fg='green')
            term.echo()
            term.secho('Jupyter is no longer running and you can close the tab in your browser.')
            logging.shutdown()
            break

    sys.exit()


@jupyter.command('servers')
@crash_report
def _servers() -> None:
    """List Jupyter servers running locally on the host machine.
    """
    for line in utils.run_cmd('jupyter server list').splitlines():
        term.echo(line)

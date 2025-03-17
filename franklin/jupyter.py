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
from .update import _update_client


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
def launch_exercise(allow_subdirs_at_your_own_risk, update):

    utils._check_window_size()

    click.clear()

    for line in banner.splitlines():
        utils.secho(line, nowrap=True, center=True, fg='green')

    logger.debug("################ STARTING FRANKLIN ################")

    utils.echo()
    utils.echo('"Science and everyday life cannot and should not be separated"', center=True)
    utils.echo("Rosalind D. Franklin", center=True)
    utils.echo()

    if not allow_subdirs_at_your_own_risk:
        for x in os.listdir(os.getcwd()):
            if os.path.isdir(x) and x not in ['.git', '.ipynb_checkpoints']:
                utils.secho("\n  Please run the command in a directory without any sub-directories.\n", fg='red')
                sys.exit(1)

    utils._check_internet_connection()
    utils.logger.debug('Starting Docker Desktop')
    _docker._failsafe_start_docker_desktop()
    utils._check_free_disk_space()
    time.sleep(2)

    _update_client(update)

    utils.secho('Starting container:', fg='green')

    image_url = select_image()

    if not _docker._image_exists(image_url):
        utils.secho("Downloading image:", fg='green')
    else:
        utils.secho("Updating image:", fg='green')
    _docker._pull(image_url)
    utils.echo()    

    run_container_id, docker_run_p, port = _docker._failsafe_run_container(image_url)

    cmd = f"docker logs --follow {run_container_id}"
    if utils.system() == "Windows":
        popen_kwargs = dict(creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        popen_kwargs = dict(start_new_session = True)
    docker_log_p = Popen(shlex.split(cmd), stdout=PIPE, stderr=STDOUT, bufsize=1, universal_newlines=True, **popen_kwargs)

    while True:
        time.sleep(0.1)
        line = docker_log_p.stdout.readline()
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

    utils.secho(f'\nJupyter is running and should open in your default browser.', fg='green')
    utils.echo(f'If not, you can access it at this URL:')
    utils.echo(f'{token_url}', nowrap=True)

    while True:
        utils.secho('\nPress Q to shut down jupyter and close application', fg='green')
        c = click.getchar()
        click.echo()
        if c.upper() == 'Q':

            utils.secho('Shutting down container', fg='red') 
            sys.stdout.flush()
            _docker._kill_container(run_container_id)
            docker_run_p.terminate()
            docker_run_p.wait()
            utils.secho('Shutting down Docker Desktop', fg='yellow') 
            sys.stdout.flush()
            _docker._stop()
            utils.secho('Service has stopped.', fg='green')
            utils.echo()
            utils.secho('Jupyter is not longer running and you can close the tab in your browser.')
            logging.shutdown()
            break

    sys.exit()

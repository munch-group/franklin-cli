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
from .docker_desktop import config_fit
from . import terminal as term
from . import options

from pkg_resources import iter_entry_points
from click_plugins import with_plugins

banner = """
        ▗▄▄▄▖▗▄▄▖  ▗▄▖ ▗▖  ▗▖▗▖ ▗▖▗▖   ▗▄▄▄▖▗▖  ▗▖
        ▐▌   ▐▌ ▐▌▐▌ ▐▌▐▛▚▖▐▌▐▌▗▞▘▐▌     █  ▐▛▚▖▐▌
        ▐▛▀▀▘▐▛▀▚▖▐▛▀▜▌▐▌ ▝▜▌▐▛▚▖ ▐▌     █  ▐▌ ▝▜▌
        ▐▌   ▐▌ ▐▌▐▌ ▐▌▐▌  ▐▌▐▌ ▐▌▐▙▄▄▖▗▄█▄▖▐▌  ▐▌
"""


@with_plugins(iter_entry_points('franklin.jupyter.plugins'))
@click.group(cls=AliasedGroup)
def jupyter():
    """Jupyter commands"""
    pass

# @click.option("--allow-subdirs-at-your-own-risk/--no-allow-subdirs-at-your-own-risk",
#                 default=False,
#                 help="Allow subdirs in current directory mounted by Docker.")
# @click.option('--update/--no-update', default=True,
#                 help="Override check for package updates")
@options.allow_subdirs
@options.no_update
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
    # term.echo('"Science and everyday life cannot and should not be separated"', center=True)
    term.echo("Rosalind D.", center=True)
    term.echo()

    if not allow_subdirs_at_your_own_risk:
        for x in os.listdir(os.getcwd()):
            if os.path.isdir(x) and not os.path.basename(x).startswith('.'):
                term.boxed_text("You have subfolders in your current directory",
                                [
                                    "Franklin must run from a folder with no other folders inside it.",
                                    "",
                                    "You can make an empty folder called 'exercise' with this command:",
                                    "",
                                    "    mkdir exercise",
                                    "",
                                    "and change to that folder with this command:",
                                    "",                                    
                                    "    cd exercise",
                                    "",
                                    "Then run your franklin command.",
                                ], fg='magenta')
                sys.exit(1)

    utils.check_internet_connection()

    if update:
        update_client()
    else:
        logger.debug('Update check skipped')

    utils.check_free_disk_space()

    if shutil.which('docker'):
        config_fit()

    utils.logger.debug('Starting Docker Desktop')
    _docker.failsafe_start_docker_desktop()
    time.sleep(2)

    image_url = select_image()
    launch_jupyter(image_url)

def launch_jupyter(image_url: str, cwd: str=None) -> None:
    """
    Launch Jupyter notebook in a Docker container.

    Parameters
    ----------
    image_url : 
        Image registry URL.
    cwd : 
        Launch jupyter in this directory (relative to dir where jupyter is launched), by default None
    """

    term.secho("Downloading/updating image:", fg='green')
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

    if cwd is not None:
        token_url = token_url.replace('/lab', f'/lab/tree/{cwd}')

    # try:
    #     if utils.system() == 'Windows':
    #         chrome_path = 'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
    #     elif utils.system() == 'Mac':
    #         chrome_path = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    #     elif utils.system() == 'Linux':
    #         chrome_path = '/usr/bin/google-chrome'
    #     webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))
    #     webbrowser.get('chrome').open(token_url, new=1, autoraise=True)
    # except:
    #     webbrowser.open(token_url, new=1)
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

    # sys.exit()


@jupyter.command('servers')
@crash_report
def _servers() -> None:
    """List Jupyter servers running locally on the host machine.
    """
    for line in utils.run_cmd('jupyter server list').splitlines():
        term.echo(line)

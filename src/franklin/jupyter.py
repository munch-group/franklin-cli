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
from .crash import crash_report
from .gitlab import select_image
from . import docker as _docker
from .logger import logger
from .desktop import config_fit
from . import terminal as term
from . import options
from . import system

@options.subdirs_allowed
@click.command()
@crash_report
def jupyter(allow_subdirs_at_your_own_risk: bool) -> None:
    """Run jupyter for an exercise
    """
    if not allow_subdirs_at_your_own_risk:
        for x in os.listdir(os.getcwd()):
            if os.path.isdir(x) and not os.path.basename(x).startswith('.'):
                term.boxed_text(
                    'You have subfolders in your current directory',
                                [
        'Franklin must run from a folder with no other folders inside it.',
        '',
        'You can make an empty folder called "exercise" with this command:',
        '',
        '    mkdir exercise',
        '',
        'and change to that folder with this command:',
        '',                                    
        '    cd exercise',
        '',
        'Then run your franklin command.',
                                ], fg='magenta')
                sys.exit(1)

    system.check_internet_connection()

    system.check_free_disk_space()

    if shutil.which('docker'):
        config_fit()

    _docker.failsafe_start_desktop()
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
        Launch jupyter in this directory (relative to dir where jupyter is 
        launched), by default None
    """

    term.secho("Downloading/updating image:")
    _docker.pull(image_url)
    term.echo()    

    term.secho('Starting container')
    run_container_id, docker_run_p, port = \
        _docker.failsafe_run_container(image_url)

    cmd = f"docker logs --follow {run_container_id}"
    if system.system() == "Windows":
        popen_kwargs = dict(
            creationflags = subprocess.DETACHED_PROCESS \
                | subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        popen_kwargs = dict(start_new_session = True)
    docker_log_p = Popen(shlex.split(cmd), stdout=PIPE, stderr=STDOUT, 
                         bufsize=1, universal_newlines=True, **popen_kwargs)

    while True:
        time.sleep(0.1)
        line = docker_log_p.stdout.readline()
        if line:
            logger.debug('JUPYTER: '+line.strip())
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

    webbrowser.open(token_url, new=1)

    term.secho(
        f'\nJupyter is running and should open in your default browser.', 
        fg='green')
    term.echo(f'If not, you can access it at this URL:')
    term.secho(f'{token_url}', nowrap=True, fg='blue')

    while True:
        term.secho('\nPress Q to shut down jupyter and close application', 
                   fg='green')
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
            _docker.desktop_stop()
            term.secho('Service has stopped.', fg='green')
            term.echo()
            term.secho('Jupyter is no longer running and you can close '
                       'the tab in your browser.')
            logging.shutdown()
            break

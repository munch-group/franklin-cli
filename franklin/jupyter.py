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
from pathlib import Path, PureWindowsPath, PurePosixPath
from subprocess import Popen, PIPE, DEVNULL, STDOUT
from .config import GITLAB_API_URL, GITLAB_GROUP, MIN_WINDOW_HEIGHT, PG_OPTIONS
from . import utils
from .utils import AliasedGroup, crash_report
from .gitlab import get_registry_listing, get_course_names, get_exercise_names, pick_course, select_exercise, select_image
from . import docker as _docker
from .logger import logger
from . import cutie
from .update import _update_client



def launch_exercise():

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


@click.group(cls=AliasedGroup)
def jupyter():
    """Jupyter commands"""
    pass


@click.option("--allow-subdirs-at-your-own-risk/--no-allow-subdirs-at-your-own-risk",
                default=False,
                help="Allow subdirs in current directory mounted by Docker.")
@click.option('--update/--no-update', default=True,
                help="Override check for package updates")
@jupyter.command()
@crash_report
def run(allow_subdirs_at_your_own_risk, update):

    utils._check_window_size()

    click.clear()
    s = """
           ▗▄▄▄▖▗▄▄▖  ▗▄▖ ▗▖  ▗▖▗▖ ▗▖▗▖   ▗▄▄▄▖▗▖  ▗▖
           ▐▌   ▐▌ ▐▌▐▌ ▐▌▐▛▚▖▐▌▐▌▗▞▘▐▌     █  ▐▛▚▖▐▌
           ▐▛▀▀▘▐▛▀▚▖▐▛▀▜▌▐▌ ▝▜▌▐▛▚▖ ▐▌     █  ▐▌ ▝▜▌
           ▐▌   ▐▌ ▐▌▐▌ ▐▌▐▌  ▐▌▐▌ ▐▌▐▙▄▄▖▗▄█▄▖▐▌  ▐▌
    """
    for line in s.splitlines():
        utils.secho(line, nowrap=True, center=True, fg='green', log=False)
    logger.debug("################ STARTING FRANKLIN ################")

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
    # click.clear()
    # click.echo('\n'*int(MIN_WINDOW_HEIGHT/2))
    utils._check_free_disk_space()
    time.sleep(2)
    # TODO: _docker.check_no_other_exercise_container_running()
    # TODO: _docker.check_no_other_local_jupyter_running()

    # dirs_in_cwd = any(os.path.isdir(x) ))
    # if dirs_in_cwd and not allow_subdirs_at_your_own_risk:
    #     utils.secho("\n  Please run the command in a directory without any sub-directories.", fg='red')
    #     sys.exit(1)


    _update_client(update)

    utils.secho('Starting container:', fg='green')
    launch_exercise()    



# import threading

# class KeyboardThread(threading.Thread):

#     def __init__(self, input_cbk = None, name='keyboard-input-thread'):
#         self.input_cbk = input_cbk
#         super(KeyboardThread, self).__init__(name=name, daemon=True)
#         self.start()

#     def run(self):
#         while True:
#             self.input_cbk(input()) #waits to get input + Return

# showcounter = 0 #something to demonstrate the change

# def my_callback(inp):
#     #evaluate the keyboard input
#     print('You Entered:', inp, ' Counter is at:', showcounter)

# #start the Keyboard thread
# kthread = KeyboardThread(my_callback)

# while True:
#     #the normal program executes without blocking. here just counting up
#     showcounter += 1
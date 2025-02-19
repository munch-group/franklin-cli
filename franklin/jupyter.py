
import sys
import os
import re
import logging
import platform
import shlex
import time
import webbrowser
import argparse
import logging
import subprocess
import click
import shutil
from subprocess import Popen, PIPE, DEVNULL, CalledProcessError, STDOUT
from .config import ANACONDA_CHANNEL, MAINTAINER_EMAIL, GITLAB_API_URL, GITLAB_GROUP
from os.path import expanduser
from .utils import format_cmd, wrap_text
from .select import select_image
from .gitlab import get_registry_listing
from . import docker as _docker
from .utils import SuppressedKeyboardInterrupt


def above_subdir_limit(allowed_depth):
    for dir, _, _ in os.walk('.'):
        if len(dir.split('/')) > allowed_depth:
            return True
    return False



def launch_exercise():

    cleanup = False

    subdir_limit = 1
    if above_subdir_limit(subdir_limit):
        msg = click.wrap_text(
            f"Please run the command in a directory without any sub-directories.",
            width=shutil.get_terminal_size().columns - 2, 
            initial_indent='', subsequent_indent='', preserve_paragraphs=True)
        click.secho(msg, fg='red')
        sys.exit(1)

    if not _docker.installed():
        print('Docker is not installed')
        sys.exit(1) 

    # get registry listing
    registry = f'{GITLAB_API_URL}/groups/{GITLAB_GROUP}/registry/repositories'
    exercises_images = get_registry_listing(registry)
    # image_info = get_registry_listing(registry)
    # exercises_images = dict((key, val['location']) for key, val in image_info.items())

    # select image using menu prompt
    image_url = select_image(exercises_images)

    # image_size = [val['size'] for val in image_info.values() if val['location'] == image_url][0]

    try:
        cmd = 'docker --version'
        p = subprocess.run(format_cmd(cmd), check=True, stdout=DEVNULL, stderr=DEVNULL)
    except CalledProcessError:
        try:
            cmd = r'"C:\Program Files\Docker\Docker\Docker Desktop.exe"'
            p = subprocess.run(cmd, check=True)
            time.sleep(5)
        except CalledProcessError:
            print('\n\nIT SEEMS "DOCKER DESKTOP" IS NOT INSTALLED. PLEASE INSTALL VIA WEBPAGE.\n\n')
            time.sleep(2)
            if platform.system == "Windows":
                webbrowser.open("https://docs.docker.com/desktop/install/windows-install/", new=1)
            if platform.system == "Mac":
                webbrowser.open("https://docs.docker.com/desktop/install/mac-install/", new=1)
            if platform.system == "Linux":
                webbrowser.open("https://docs.docker.com/desktop/install/linux-install/", new=1)
            sys.exit()

    # pull image if not already present
    if not _docker.image_exists(image_url):
        _docker.pull(image_url)
        raise Exception('Image not found. Restart Docker Desktop and try again.')

    from pathlib import Path
    home = str(Path.home())
    pwd = str(Path.cwd())
    # home = expanduser("~")
    # pwd = os.getcwd()

    # if platform.system() == 'Windows':
    #     pwd = pwd.replace('\\', '/').replace('C:', '/c')
    #     home = home.replace('\\', '/').replace('C:', '/c')  

    ssh_mount = (os.path.join(home,'.ssh'), '/tmp/.ssh')
    anaconda_mount = (os.path.join(home, '.anaconda'), '/root/.anaconda')
    pwd_mount = (pwd, pwd)

    # repo_mount = ''
    # if clone:
    #     repo_mount = f'--mount type=bind,source={pwd}/git-repository,target=/root/git-repository'

    # command for running jupyter docker container
    # cmd = f"docker run --rm --mount type=bind,source={home}/.ssh,target=/tmp/.ssh --mount type=bind,source={home}/.anaconda,target=/root/.anaconda --mount type=bind,source={pwd},target={pwd} -w {pwd} -i -t -p 8888:8888 {image_url}:main"
    # cmd = f"docker run --rm {repo_mount} --mount type=bind,source={home}/.ssh,target=/tmp/.ssh --mount type=bind,source={home}/.anaconda,target=/root/.anaconda --mount type=bind,source={pwd},target={pwd} -w {pwd} -i -p 8888:8888 {image_url}:main"



    cmd = (
        f"docker run --rm"
        f" --mount type=bind,source={ssh_mount[0]},target={ssh_mount[1]}"
        f" --mount type=bind,source={anaconda_mount[0]},target={anaconda_mount[1]}"
        f" --mount type=bind,source={pwd_mount[0]},target={pwd_mount[1]}"
        f" -w {pwd_mount[0]} -i -p 8888:8888 {image_url}:main"
    )
    
        # cmd = f"docker run --rm --mount type=bind,source={home}/.ssh,target=/tmp/.ssh --mount type=bind,source={home}/.anaconda,target=/root/.anaconda --mount type=bind,source={pwd},target={pwd} -w {pwd} -i -p 8888:8888 {image_url}:main"




    # cmd = f"docker run --rm --mount type=bind,source=$env:userprofile\.ssh,target=/tmp/.ssh --mount type=bind,source=$env:userprofile\.anaconda,target=/root/.anaconda --mount type=bind,source=$($pwd  -replace '\\', '/' -replace 'C:', '/c'),target=$($pwd -replace '\\', '/' -replace 'C:', '/c') -w $($pwd  -replace '\\', '/' -replace 'C:', '/c') -i -t -p 8888:8888 registry.gitlab.au.dk/au81667/mbg-docker-exercises:main

    # if platform.system() == "Windows":
    #     popen_kwargs = dict(creationflags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP)
    # else:
    #     popen_kwargs = dict(start_new_session = True)
    popen_kwargs = dict()

    # run docker container
    # global docker_run_p
    docker_run_p = Popen(shlex.split(cmd), stdout=DEVNULL, stderr=DEVNULL, **popen_kwargs)

    time.sleep(5)

    # get id of running container
    for cont in _docker.containers(return_json=True):
        if cont['Image'].startswith(image_url):
            run_container_id  = cont['ID']
            break
    else:
        print('No running container with image')
        sys.exit()   

    cmd = f"docker logs --follow {run_container_id}"
    docker_log_p = Popen(shlex.split(cmd), stdout=PIPE, stderr=STDOUT, bufsize=1, universal_newlines=True, **popen_kwargs)

    # docker_log_p = Popen(shlex.split(cmd), stdout=PIPE, stderr=STDOUT, universal_newlines=False, **popen_kwargs)
    # docker_p_nice_stdout = open(os.dup(docker_log_p.stdout.fileno()), newline='') 

    # docker_log_p = Popen(shlex.split(cmd), stdout=PIPE, stderr=STDOUT, **popen_kwargs)
    # docker_p_nice_stdout = open(os.dup(docker_log_p.stdout.fileno()), 'rb') 
    # https://koldfront.dk/making_subprocesspopen_in_python_3_play_nice_with_elaborate_output_1594

# newline determines how to parse newline characters from the stream. It can be None, '', '\n', '\r', and '\r\n'. It works as follows:
# When reading input from the stream, if newline is None, universal newlines mode is enabled. Lines in the input can end in '\n', '\r', or '\r\n', and these are translated into '\n' before being returned to the caller. If it is '', universal newlines mode is enabled, but line endings are returned to the caller untranslated. If it has any of the other legal values, input lines are only terminated by the given string, and the line ending is returned to the caller untranslated.
# When writing output to the stream, if newline is None, any '\n' characters written are translated to the system default line separator, os.linesep. If newline is '' or '\n', no translation takes place. If newline is any of the other legal values, any '\n' characters written are translated to the given string.

#     # signal handler for cleanup when terminal window is closed
#     def handler(signal_nr, frame):
#         with SuppressedKeyboardInterrupt():
#             signal_name = signal.Signals(signal_nr).name
#             logging.debug(f'Signal handler called with signal {signal_name} ({signal_nr})')
            
#             logging.debug('killing docker container')
#             docker_kill(run_container_id)

#             logging.debug('killing docker log process')
#             docker_log_p.kill()

#             logging.debug('waiting for docker log process')
#             docker_log_p.wait()

#             logging.debug('killing docker run process')
#             docker_run_p.kill()
#             #docker_run_p.kill(signal.CTRL_C_EVENT)

#             logging.debug('waiting for docker run process')
#             docker_run_p.wait()

#             if cleanup:
#                 docker_cleanup()
#         sys.exit()
#         #raise Exception

# #os.kill(self.p.pid, signal.CTRL_C_EVENT)

#     # register handler for signals
#     signal.signal(signal.SIGTERM, handler)
#     # signal.signal(signal.SIGINT, handler)
#     signal.signal(signal.SIGABRT, handler)
#     if platform.system() == 'Mac':
#         signal.signal(signal.SIGHUP, handler)
#     if platform.system() == 'Linux':
#         signal.signal(signal.SIGHUP, handler)
#     if platform.system() == 'Windows':
#         signal.signal(signal.SIGBREAK, handler)
#         signal.signal(signal.CTRL_C_EVENT, handler)


    while True:
        time.sleep(0.1)
        line = docker_log_p.stdout.readline()
        # line = docker_p_nice_stdout.readline().decode()
        match= re.search(r'https?://127.0.0.1\S+', line)
        if match:
            token_url = match.group(0)
            break

    webbrowser.open(token_url, new=1)

    click.secho(f'Jupyter is running at {token_url}', fg='green')

    while True:
        click.echo('\nPress Q to shut down jupyter and close application\n', nl=False)
        c = click.getchar()
        click.echo()
        if c.upper() == 'Q':
            click.secho('Shutting down JupyterLab', fg='yellow')
            logging.debug('Jupyter server is stopping')
            _docker.kill(run_container_id)
            docker_log_p.stdout.close()
            docker_log_p.kill()
            docker_run_p.kill()
            docker_log_p.wait()
            docker_run_p.wait()
            logging.debug('Jupyter server stopped')
            click.secho('Jupyter server stopped', fg='red')
            break

    sys.exit()

    args = f"run --rm --mount type=bind,source={user_home}/.ssh,target=/tmp/.ssh --mount type=bind,source={user_home}/.anaconda,target=/root/.anaconda --mount type=bind,source={pwd},target={pwd} -w {pwd} -i -t -p 8888:8888 {image_url}:main".split()
    asyncio.run(run_docker(args))
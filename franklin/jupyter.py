
import sys
import os
import re
import logging
import platform
import shlex
import time
import webbrowser
import logging
import subprocess
import click
import shutil
import time
from subprocess import Popen, PIPE, DEVNULL, CalledProcessError, STDOUT
from .config import ANACONDA_CHANNEL, MAINTAINER_EMAIL, GITLAB_API_URL, GITLAB_GROUP, ALLOW_SUBDIRS
from os.path import expanduser
from .utils import format_cmd, wrap_text
from .select import select_image
from .gitlab import get_registry_listing, get_course_names, get_exercise_names
from . import docker as _docker
from .utils import update_client
from .logger import logger


from . import cutie


def select_image(exercises_images):

    # print(exercise_list)
    # image_tree = defaultdict(lambda: defaultdict(str))
    # for course, exercise in exercise_dict:
    #     # c, w, v = image_name.split('-')
    #     # image_tree[c.replace('_', ' ')][w.replace('_', ' ')][v.replace('_', ' ')] = image_name
    #     image_tree[course][exercise] = image_name

    click.clear()
    click.secho("\n\nFranklin says Hi", fg='green')
    click.echo(click.wrap_text("\n\nUse arrow keys to move and enter to select"
                               "Press Ctrl-C to close the application.", width=max((shutil.get_terminal_size().columns)/2, 70), 
               initial_indent='', subsequent_indent='', 
               preserve_paragraphs=True))   
    

    def pick_course():
        course_names = get_course_names()
        course_group_names, course_danish_names,  = zip(*sorted(course_names.items()))
        click.secho("\nSelect course:", fg='green')
        captions = []
        # options = list(image_tree.keys())
        # course = options[cutie.select(options, caption_indices=captions, selected_index=0)]
        course_idx = cutie.select(course_danish_names, caption_indices=captions, selected_index=0)
        return course_group_names[course_idx], course_danish_names[course_idx]

    while True:
        course, danish_course_name = pick_course()

        exercise_names = get_exercise_names(course)

        # only use those with listed images
        for key in list(exercise_names.keys()):
            if (course, key) not in exercises_images:
                del exercise_names[key]

        if exercise_names:
            break

        click.secho(f"\n  >>No exercises for {danish_course_name}<<", fg='red')

    exercise_repo_names, exercise_danish_names = zip(*sorted(exercise_names.items()))
    click.secho(f"\nSelect exercise in {danish_course_name}:", fg='green')
    captions = []
    # options = list(image_tree[course].keys())
    # week = options[cutie.select(options, caption_indices=captions, selected_index=0)]
    exercise_idx = cutie.select(exercise_danish_names, caption_indices=captions, selected_index=0)
    exercise = exercise_repo_names[exercise_idx]
    # print("\nSelect exercise:")
    # captions = []
    # options = list(image_tree[course][week].keys())
    # exercise = options[cutie.select(options, caption_indices=captions, selected_index=0)]

    click.echo(f"\nPreparing jupyter session for:\n")
    click.echo(f"    {danish_course_name}: {exercise_danish_names[exercise_idx]} \n")
    time.sleep(1)

    selected_image = exercises_images[(course, exercise)]
    return selected_image



# @click.option("--containers/--no-containers", default=True, help="Prune containers")
# @click.option("--volumes/--no-volumes", default=True, help="Prune volumes")
# @docker.command()
# def prune(containers, volumes):
#     """Prune docker containers and volumes."""
#     if containers and volumes:
#         _docker.prune_all()
#     elif containers:
#         _docker.prune_containers()
#     elif volumes:
#         _docker.prune_volumes()

# @click.option("--force/--no-force", default=False, help="Force removal")
# @click.argument('image')
# @docker.command()
# def remove(image, force):
#     """Remove docker image.
    
#     IMAGE is the id of the image to remove.
#     """

#     _docker.rm_image(image, force)

# @docker.command()
# def cleanup():
#     """Cleanup everything."""

#     for image in _docker.images():
#         if image['Repository'].startswith(REGISTRY_BASE_URL):
#             _docker.rm_image(image['ID'])
#     _docker.prune_containers()
#     _docker.prune_volumes()
#     _docker.prune_all()





def launch_exercise():

    cleanup = False


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
    if not _docker._image_exists(image_url):
        _docker._pull(image_url)
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
    for cont in _docker._containers(return_json=True):
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
            _docker._kill(run_container_id)
            docker_log_p.stdout.close()
            docker_log_p.kill()
            docker_run_p.kill()
            docker_log_p.wait()
            docker_run_p.wait()
            logging.debug('Jupyter server stopped')
            click.secho('Jupyter server stopped', fg='red')
            break

    sys.exit()

    # args = f"run --rm --mount type=bind,source={user_home}/.ssh,target=/tmp/.ssh --mount type=bind,source={user_home}/.anaconda,target=/root/.anaconda --mount type=bind,source={pwd},target={pwd} -w {pwd} -i -t -p 8888:8888 {image_url}:main".split()
    # asyncio.run(run_docker(args))

@click.group()
def jupyter():
    """Docker commands."""
    pass



# @click.option("--verbose",
#                 default=False,
#                 help="Print debugging information")
# @click.option("--fixme",
#                 default=False,
#                 help="Run trouble shooting")
# @click.option("--clone",
#                 default=False,
#                 help="Also clone the repository")
@click.option("--allow-subdirs-at-your-own-risk/--no-allow-subdirs-at-your-own-risk",
                default=False,
                help="Allow subdirs in current directory mounted by Docker.")
@click.option('--update/--no-update', default=True,
                help="Override check for package updates")
@jupyter.command()
def select(allow_subdirs_at_your_own_risk, update):

    # gb_free = shutil.disk_usage('/').free / 1024**3
    # if gb_free < 10:




    _docker._prepare_user_setup(ALLOW_SUBDIRS or allow_subdirs_at_your_own_risk)

    # if _docker._check_internet_connection():
    #     logger.error("Internet connection to Docker Hub ok")
    # else:
    #     click.secho('"No internet connection', fg='red')
    #     logger.error("No internet connection to Docker Hub")
    #     sys.exit(1)

    # if _docker._check_docker_desktop_running():
    #     logger.debug("Docker Desktop is running")
    # else:
    #     click.secho('Docker Desktop is not running', fg='red')
    #     logger.error("Docker Desktop is not running")
    #     sys.exit(1)

    # free_gb = _docker._free_disk_space()
    # if free_gb < REQUIRED_GB_FREE_DISK:
    #     click.secho(f'Not enough disk space. Required: {REQUIRED_GB_FREE_DISK} GB, Available: {free_gb} GB', fg='red')
    #     logger.error(f"Not enough disk space. Required: {REQUIRED_GB_FREE_DISK} GB, Available: {free_gb} GB")
    #     sys.exit(1)

    # TODO: check if docker is installed
    # _docker.check_no_other_exercise_container_running()
    # _docker.check_no_other_local_jupyter_running()

    update_client(update)

    launch_exercise()    
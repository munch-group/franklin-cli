
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
from pathlib import Path, PureWindowsPath, PurePosixPath
from subprocess import Popen, PIPE, DEVNULL, CalledProcessError, STDOUT
from .config import ANACONDA_CHANNEL, MAINTAINER_EMAIL, GITLAB_API_URL, GITLAB_GROUP, ALLOW_SUBDIRS
from os.path import expanduser
from . import utils
# from .select import select_image
from .gitlab import get_registry_listing, get_course_names, get_exercise_names
from . import docker as _docker
from .utils import update_client
from .logger import logger

# from subprocess import Popen, PIPE, STDOUT, DEVNULL, CalledProcessError
# if platform.system() == "Windows":
#     from subprocess import DETACHED_PROCESS, CREATE_NEW_PROCESS_GROUP

from . import cutie


def select_image(exercises_images):

    # print(exercise_list)
    # image_tree = defaultdict(lambda: defaultdict(str))
    # for course, exercise in exercise_dict:
    #     # c, w, v = image_name.split('-')
    #     # image_tree[c.replace('_', ' ')][w.replace('_', ' ')][v.replace('_', ' ')] = image_name
    #     image_tree[course][exercise] = image_name

    utils.echo("\n\nUse arrow keys for navigation and enter to select\n")
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
    utils.echo("\n\nUse arrow keys for navigation and enter to select\n")
    captions = []
    exercise_idx = cutie.select(exercise_danish_names, caption_indices=captions, selected_index=0)
    exercise = exercise_repo_names[exercise_idx]

    utils.echo(f"\nPreparing jupyter session for:\n", nowrap=True)  # FIXME: if I don't add nowrap here and below, text is printed twice...
    utils.echo(f"    {danish_course_name}: {exercise_danish_names[exercise_idx]} \n", nowrap=True)
    time.sleep(1)

    selected_image = exercises_images[(course, exercise)]
    return selected_image


def launch_exercise():

    cleanup = False

    # get registry listing
    registry = f'{GITLAB_API_URL}/groups/{GITLAB_GROUP}/registry/repositories'
    exercises_images = get_registry_listing(registry)

    # select image using menu prompt
    image_url = select_image(exercises_images)

    # image_size = [val['size'] for val in image_info.values() if val['location'] == image_url][0]

    # pull image if not already present
    if not _docker._image_exists(image_url):
        _docker._pull(image_url)

    ssh_mount = Path.home() / '.ssh'
    anaconda_mount = Path.home() / '.anaconda'
    cwd_mount_source = Path.cwd()
    cwd_mount_target = Path.cwd()

    if platform.system() == 'Windows':
        ssh_mount = PureWindowsPath(ssh_mount)
        anaconda_mount = PureWindowsPath(anaconda_mount)
        cwd_mount_source = PureWindowsPath(cwd_mount_source)
        cwd_mount_target = PurePosixPath(cwd_mount_source)
        parts = cwd_mount_target.parts
        assert ':' in parts[0]
        cwd_mount_target = PurePosixPath('/', *(cwd_mount_target.parts[1:]))

    cmd = (
        rf"docker run --rm"
        rf" --mount type=bind,source={ssh_mount},target=/tmp/.ssh"
        rf" --mount type=bind,source={anaconda_mount},target=/root/.anaconda"
        rf" --mount type=bind,source={cwd_mount_source},target={cwd_mount_target}"
        rf" -w {cwd_mount_target} -i -p 8888:8888 {image_url}:main"
    )
    logger.debug(f'docker run cmd: {cmd}')

    # if platform.system() == "Windows":
    #     popen_kwargs = dict(creationflags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP)
    # else:
    #     popen_kwargs = dict(start_new_session = True)
    popen_kwargs = dict()
    cmd = cmd.split()
    cmd[0] = shutil.which(cmd[0])
    docker_run_p = Popen(cmd, 
                         stdout=DEVNULL, stderr=DEVNULL, 
                         **popen_kwargs)

    time.sleep(5)

    # get id of running container
    for _ in range(10):
        time.sleep(1)
        run_container_id = None
        for cont in _docker._containers(return_json=True):
            if cont['Image'].startswith(image_url):
                run_container_id  = cont['ID']
        if run_container_id:
            break
    else:
        print('No running container with image')
        sys.exit()   

    cmd = f"docker logs --follow {run_container_id}"
    docker_log_p = Popen(shlex.split(cmd), stdout=PIPE, stderr=STDOUT, bufsize=1, universal_newlines=True, **popen_kwargs)

    while True:
        time.sleep(0.1)
        line = docker_log_p.stdout.readline()
        # line = docker_p_nice_stdout.readline().decode()
        match= re.search(r'https?://127.0.0.1\S+', line)
        if match:
            token_url = match.group(0)
            docker_log_p.stdout.close()
            docker_log_p.terminate()
            docker_log_p.wait()
            break

    webbrowser.open(token_url, new=1)

    click.secho(f'Jupyter is running at {token_url}', fg='green')

    while True:
        click.echo('\nPress Q to shut down jupyter and close application')
        # c = input()
        # c = c.strip()
        c = click.getchar()
        click.echo()
        if c.upper() == 'Q':
            click.secho('Shutting down JupyterLab', fg='yellow')
            logging.debug('Jupyter server is stopping')
            _docker._kill_container(run_container_id)
            # docker_log_p.stdout.close()
            # docker_log_p.kill()
            docker_run_p.kill()
            # docker_log_p.wait()
            docker_run_p.wait()
            logging.debug('Jupyter server stopped')
            click.secho('Jupyter server stopped', fg='red')
            break

    sys.exit()


@click.group()
def jupyter():
    """Docker commands."""
    pass


@click.option("--allow-subdirs-at-your-own-risk/--no-allow-subdirs-at-your-own-risk",
                default=False,
                help="Allow subdirs in current directory mounted by Docker.")
@click.option('--update/--no-update', default=True,
                help="Override check for package updates")
@jupyter.command()
def select(allow_subdirs_at_your_own_risk, update):

    utils._welcome_screen()

    _docker._check_docker_desktop_installed()

    _docker._failsafe_start_docker_desktop()

    utils._check_internet_connection()

    utils._check_free_disk_space()

    # TODO: check if docker is installed
    # _docker.check_no_other_exercise_container_running()
    # _docker.check_no_other_local_jupyter_running()

    dirs_in_cwd = any(os.path.isdir(x) for x in os.listdir(os.getcwd()))
    if dirs_in_cwd and not allow_subdirs_at_your_own_risk:
        utils.secho("\n  Please run the command in a directory without any sub-directories.", fg='red')
        sys.exit(1)


    update_client(update)

    launch_exercise()    
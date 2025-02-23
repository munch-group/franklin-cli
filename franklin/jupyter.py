
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
from subprocess import Popen, PIPE, DEVNULL, STDOUT
from .config import GITLAB_API_URL, GITLAB_GROUP
from . import utils
from .gitlab import get_registry_listing, get_course_names, get_exercise_names
from . import docker as _docker
from .utils import update_client
from .logger import logger
from . import cutie


def select_image(exercises_images):

    def pick_course():
        course_names = get_course_names()
        course_group_names, course_danish_names,  = zip(*sorted(course_names.items()))
        utils.secho("\nUse arrow keys to select course and press Enter:", fg='green')
        captions = []
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
    utils.secho("\nUse arrow keys to select exercise in {danish_course_name} and press Enter:", fg='green')
    captions = []
    exercise_idx = cutie.select(exercise_danish_names, caption_indices=captions, selected_index=0)
    exercise = exercise_repo_names[exercise_idx]

    utils.echo(f"\nPreparing jupyter session for:\n", nowrap=True)  # FIXME: if I don't add nowrap here and below, text is printed twice...
    utils.echo(f"    {danish_course_name}: {exercise_danish_names[exercise_idx]} \n", nowrap=True)
    time.sleep(1)

    selected_image = exercises_images[(course, exercise)]
    return selected_image


def launch_exercise():

    registry = f'{GITLAB_API_URL}/groups/{GITLAB_GROUP}/registry/repositories'
    exercises_images = get_registry_listing(registry)

    image_url = select_image(exercises_images)

    if not _docker._image_exists(image_url):
        utils.echo("Downloading image:")
        _docker._pull(image_url)

    bar_length = 20
    with click.progressbar(length=bar_length, label='Launching:', fill_char='=', empty_char=' ') as bar:
        prg = 1
        bar.update(prg)

        ssh_mount = Path.home() / '.ssh'
        anaconda_mount = Path.home() / '.anaconda'
        cwd_mount_source = Path.cwd()
        cwd_mount_target = Path.cwd()

        ssh_mount.mkdir(exist_ok=True)
        anaconda_mount.mkdir(exist_ok=True)

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
            rf" -w {cwd_mount_target} -i -p 8050:8050 -p 8888:8888 {image_url}:main"
        )
        logger.debug(f'docker run cmd: {cmd}')

        if platform.system() == "Windows":
            popen_kwargs = dict(creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            popen_kwargs = dict(start_new_session = True)

        cmd = cmd.split()
        cmd[0] = shutil.which(cmd[0])
        docker_run_p = Popen(cmd, 
                            stdout=DEVNULL, stderr=DEVNULL, 
                            **popen_kwargs)
        for b in range(5):
            time.sleep(1)
            prg += 1
            bar.update(prg)

        # get id of running container
        for _ in range(10):
            time.sleep(1)
            run_container_id = None
            for cont in _docker._containers(return_json=True):
                if cont['Image'].startswith(image_url):
                    run_container_id  = cont['ID']
            if run_container_id:
                break
            prg += 1
            bar.update(prg)
        else:
            utils.echo('Docker not responding...', fg='red')
            with utils.TroubleShooting():
                # utils.echo('Troubleshooting...', fg='red', nl=False)
                _docker._kill_all_docker_desktop_processes()
                # utils.echo(' done.', fg='red')
            utils.echo('Please rerun your command now (press arrow-up)', fg='red')
            sys.exit()   


        bar.update(bar_length)

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

    utils.secho(f'\nJupyter is running and should open in your default browser. If not, you can access it at this URL:', fg='green')
    utils.secho(f'{token_url}', fg='green')

    while True:
        utils.echo('\nPress Q to shut down jupyter and close application')
        c = click.getchar()
        click.echo()
        if c.upper() == 'Q':
            click.secho('Shutting down JupyterLab', fg='yellow') # FIXME: change to utils.secho and no logging call
            logging.debug('Jupyter server is stopping')
            _docker._kill_container(run_container_id)
            docker_run_p.terminate()
            docker_run_p.wait()
            click.secho('Jupyter server stopped', fg='red')
            logging.debug('Jupyter server stopped') # FIXME: change to utils.secho and no logging call
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

    click.echo()
    utils.secho("FRANKLIN", fg='green', bold=True)
    click.echo("Science and everyday life cannot and should not be separated. - Rosalind D. Franklin")

    _docker._failsafe_start_docker_desktop()

    utils._check_internet_connection()

    utils._check_free_disk_space()

    # TODO: _docker.check_no_other_exercise_container_running()
    # TODO: _docker.check_no_other_local_jupyter_running()

    dirs_in_cwd = any(os.path.isdir(x) for x in os.listdir(os.getcwd()))
    if dirs_in_cwd and not allow_subdirs_at_your_own_risk:
        utils.secho("\n  Please run the command in a directory without any sub-directories.", fg='red')
        sys.exit(1)


    update_client(update)

    launch_exercise()    



    import threading

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
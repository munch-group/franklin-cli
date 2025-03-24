import json
import os
import click
import shutil
import time
import psutil
from functools import wraps
from pathlib import Path, PureWindowsPath, PurePosixPath
from packaging.version import Version
import subprocess
from subprocess import Popen, PIPE, DEVNULL, STDOUT

from .docker_desktop import (
    docker_desktop_status, docker_desktop_start, docker_desktop_stop, 
    docker_desktop_restart, update_docker_desktop, failsafe_start_docker_desktop, 
    docker_desktop_version, docker_config, config_get, config_set, config_reset, config_fit
)
from . import terminal as term
from . import utils
from .utils import AliasedGroup, crash_report, fmt_cmd
from .config import REGISTRY_BASE_URL, GITLAB_GROUP, DOCKER_SETTINGS, CONTAINER_MEMORY_LIMIT
from . import cutie
from .gitlab import get_course_names, get_exercise_names
from .logger import logger

from typing import Tuple, List, Dict, Callable, Any
# type Vector = list[float]


# import yaml
# _root = os.path.abspath(os.path.dirname(__file__))
# config_path = os.path.join(_root, 'config.yaml')
# with open(config_path) as f:
#     cfg = yaml.safe_load(f)


os.environ['DOCKER_CLI_HINTS'] = 'false'

def run_container(image_url: str) -> Tuple[str, Popen, str]:
    """
    Run container from image.

    Parameters
    ----------
    image_url : 
        Image url

    Returns
    -------
    :
        Tuple with container id, process handle and port.

    Raises
    ------
    :
        Exception if container if a container id for the running container is not retrieved.
    """
    docker_run_p, port = run(image_url)
    run_container_id = None
    for _ in range(10):
        time.sleep(5)    
        for cont in containers():
            if cont['Image'].startswith(image_url):
                run_container_id  = cont['ID']
        if run_container_id is not None:
            return run_container_id, docker_run_p, port
    else:
        raise Exception()

def failsafe_run_container(image_url: str) -> Tuple[str, Popen, str]:
    """
    Run container from image. Upon Exception is raised by run_container, it does a docker system prune and a docker desktop restart.

    Parameters
    ----------
    image_url : 
        Image URL.

    Returns
    -------
    :
        Tuple with container id, process handle and port.

    Raises
    ------
    :
        Exception if container if a container id for the running container is not retrieved.
    """

    try:
        return run_container(image_url)
    except:
        prune_all()    
        docker_desktop_restart()    
        return run_container(image_url)


def ensure_docker_running(func: Callable) -> Callable:
    """
    Decorator for functions that require Docker Desktop to be running.

    Parameters
    ----------
    func : 
        Function.

    Returns
    -------
    :
        Decorated function.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        failsafe_start_docker_desktop()
        return func(*args, **kwargs)
    return wrapper

def irrelevant_unless_docker_running(func: Callable) -> Callable:
    """
    Decorator for click command functions that are irrelevant unless Docker Desktop is running.
    If users use command when Docker Desktop is not running, they will be informed.

    Parameters
    ----------
    func : 
        Function.

    Returns
    -------
    :
        Decorated function.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not docker_desktop_status() == 'running':
            term.secho("Docker is not running")
            return None
        return func(*args, **kwargs)
    return wrapper


def image_exists(image_url: str) -> bool:
    """
    Checks if image exists.

    Parameters
    ----------
    image_url : 
        Image URL.

    Returns
    -------
    :
        True if image exists, False otherwise.
    """
    for image in images(return_json=True):
        if image['Repository'].startswith(image_url):
            return True
    return False


# def _command(command, silent=False, return_json=False):
#     if silent:
#         return subprocess.run(utils.format_cmd(command), check=False, stdout=DEVNULL, stderr=DEVNULL)
#     if return_json:
#         result = []
#         for line in subprocess.check_output(utils.format_cmd(command + ' --format json')).decode().strip().splitlines():
#             result.append(json.loads(line))
#         return result
#     else:
#         return subprocess.check_output(utils.format_cmd(command)).decode().strip()


def format_table(header: str, table: List[List[str]], ids: List[str], min_widths: List[int]=None, select: bool=True) -> List[str]:
    """
    Called by *_list functions to format a table for display in the terminal.

    Parameters
    ----------
    header : 
        Table header.
    table : 
        List of lists of strings.
    ids : 
        List of string IDs for each row.
    min_widths : 
        List of same length as the number of table columns. Integer values represent 
        minimal column widths. None values represent no minimal width. All columns 
        with None have same width. By default None, in which case all columns have 
        the same width. 
    select : 
        Whether to prompt user to select rows. By default True.

    Returns
    -------
    :
        If select is True, returns a list of selected IDs. If select is False, 
        returns a list of strings for each row in the table.
    """
    col_widths = [max(len(x) for x in col) for col in zip(*table)]

    max_width = shutil.get_terminal_size().columns - 4 * len(col_widths) - 4 * int(select) - 2

    if min_widths is None:
        min_widths = [15] * len(col_widths)
    elif None in min_widths:
        non_col_widths = sum(c for c, m in zip(col_widths, min_widths) if m is None)
        leeway = (max_width - sum(x for x in min_widths if x is not None))
        col_widths = [int(c / non_col_widths * leeway) if m is None else m for c, m in zip(col_widths, min_widths)]
    elif sum(col_widths) > max_width:
        leeway = max_width - sum(min_widths)
        if leeway > 0:
            col_widths =  [min_widths[i] + int((w/sum(col_widths)*leeway)) for i, w in enumerate(col_widths)]

    table_width = sum(col_widths) + 4 * len(col_widths) + 2

    term.echo("Move: Arrow up/down, Toggle-select: Space, Confirm: Enter, Abort: Ctrl-C\n"*int(select))
    term.echo('    '*int(select)+'| '+'| '.join([x[:w].ljust(w+2) for x, w in zip(header, col_widths)]), nowrap=True)
    click.echo('-'*(table_width-4*int(not select)))
    rows = []
    for row in table:
        rows.append('| '+'| '.join([x[:w].ljust(w+2) for x, w in zip(row, col_widths)]))

    if not select:
        return rows

    captions = []
    selected_indices = cutie.select_multiple(
        rows, caption_indices=captions, 
        # hide_confirm=False
        hide_confirm=True
    )
    return [ids[i]for i in selected_indices]


def container_list(callback: Callable=None) -> None:
    """
    Displays a list of running containers in the terminal. If callback 
    is provided, it will prompt the user to select containers and run the 
    callback function will be called for each container with the container ID
    as argument.

    Parameters
    ----------
    callback : 
        _description_, Callback function taking a container ID as argument, by default None

    Returns
    -------
    :
        None
    """
    current_containers = containers()
    if not current_containers:
        click.echo("\nNo running containers\n")
        return

    course_names = get_course_names()
    exercise_names = {}

    header = ['Course', 'Exercise', 'Started', 'Size']
    table = []
    ids = []
    prefix = f'{REGISTRY_BASE_URL}/{GITLAB_GROUP}'
    for cont in current_containers:
        if cont['Image'].startswith(prefix):
            rep = cont['Image'].replace(prefix, '')
            if rep.endswith(':latest'):
                rep = rep[:-7]
            if rep.startswith('/'):
                rep = rep[1:]
            course_label, exercise_label = rep.split('/')
            if exercise_label not in exercise_names:
                exercise_names.update(get_exercise_names(course_label))
            course_name = course_names[course_label]
            exercise_name = exercise_names[exercise_label]
            ids.append(cont['ID'])
            table.append((course_name, exercise_name , cont['RunningFor'].replace(' ago', ''), cont['Size']))

    if callback is None:
        for row in format_table(header, table, ids, min_widths=[None, None, 20, 25], select=False):
            term.echo(row, nowrap=True)
        term.echo()
        return
    
    term.secho("Select containers:", fg='green')

    for cont_id in format_table(header, table, ids, min_widths=[None, None, 20, 25], select=True):
        callback(cont_id, force=True)


def image_list(callback: Callable=None):
    """
    Displays a list of images in the terminal. If callback is provided,
    it will prompt the user to select images and run the callback function 
    will be called for each image with the image ID as argument.

    Parameters
    ----------
    callback : 
        _description_, Callback function taking a container ID as argument, by default None

    Returns
    -------
    :
        None
    """
    img = images(return_json=True)
    if not img:
        click.echo("\nNo images\n")
        return

    course_names = get_course_names()
    exercise_names = {}

    header = ['Course', 'Exercise', 'Age', 'Size']
    table = []
    ids = []
    prefix = f'{REGISTRY_BASE_URL}/{GITLAB_GROUP}'
    for img in images(return_json=True):
        if img['Repository'].startswith(prefix):

            rep = img['Repository'].replace(prefix, '')
            if rep.startswith('/'):
                rep = rep[1:]
            course_label, exercise_label = rep.split('/')
            if exercise_label not in exercise_names:
                exercise_names.update(get_exercise_names(course_label))
            course_name = course_names[course_label]
            exercise_name = exercise_names[exercise_label]
            course_field = course_name
            exercise_field = exercise_name
            ids.append(img['ID'])
            table.append((course_field, exercise_field , img['CreatedSince'].replace(' ago', ''), img['Size'].replace("GB", " GB")))

    if callback is None:
        for row in format_table(header, table, ids, min_widths=[None, None, 9, 9], select=False):
            term.echo(row, nowrap=True)
        term.echo()
        return

    term.secho("\nSelect images:", fg='green')

    for img_id in format_table(header, table, ids, min_widths=[None, None, 9, 9], select=True):
        callback(img_id, force=True)


###########################################################
# docker subcommands
###########################################################

@click.group(cls=AliasedGroup)
def docker():
    """Docker commands
    """
    pass


def pull(image_url :str) -> None:
    """
    Pull Docker image.

    Parameters
    ----------
    image_url : 
        Image URL.
    """
    # p = Popen(utils.format_cmd(f'docker pull {image_url}:latest'), stdout=PIPE, stderr=STDOUT, bufsize=1, universal_newlines=True)
    # p = Popen(fmt_cmd(f'docker pull {image_url}:latest'), stdout=PIPE, stderr=STDOUT, bufsize=1, universal_newlines=True)
    # f = p.stdout
    # while True:
    #     line = f.readline()
    #     if not line:
    #         break
    #     sys.stdout.write(line)
    #     sys.stdout.flush()
    # p.wait()

    # buffer = []
    # while True:            
    #     c = f.read(1)
    #     if not c:
    #         break
    #     if len(buffer) < 6:
    #         buffer.append(c)
    #     else:
    #         if ''.join(buffer) == 'Digest':
    #             break
    #         buffer.append(c)
    #         buffer.pop(0)
    #         sys.stdout.write(c)
    #         sys.stdout.flush()
    # for c in buffer:
    #     sys.stdout.write(c)
    #     sys.stdout.flush()
    # p.wait()

    subprocess.run(utils.fmt_cmd(f'docker pull {image_url}:latest'), check=False)
    # utils.run_cmd(f'docker pull {image_url}:latest', check=False)


@click.argument("url")
@docker.command('pull')
@ensure_docker_running
@crash_report
def _pull(url):
    """Pull docker image.
    
    URL is the Docker image URL.
    """
    pull(url)


@docker.command('restart')
@crash_report
def _restart():
    """Restart Docker Desktop.
    """
    docker_desktop_restart()


@docker.command('start')
@crash_report
def _start():
    """Start Docker Desktop.
    """
    docker_desktop_start()


@docker.command('stop')
@irrelevant_unless_docker_running
@crash_report
def _stop():
    """Stop Docker Desktop.
    """
    docker_desktop_stop()


@docker.command('status')
@crash_report
def _status():
    """Docker Desktop status.
    """
    s = docker_desktop_status()
    fg = 'green' if s == 'running' else 'red'
    term.secho(s, fg=fg, nowrap=True)


@docker.command('update')
@crash_report
def _update():
    """Update Docker Desktop.
    """
    if utils.system() == 'Windows':
        term.echo('This command is not available on Windows systems. Please open the Docker Desktop application and check for updates there.')
    else:
        update_docker_desktop()


@docker.command('version')
@crash_report
def _version():
    """Show Docker Desktop version
    """
    term.echo(docker_desktop_version())


def run(image_url :str) -> Tuple[Popen, str]:
    """
    Runs a container from an image.

    Parameters
    ----------
    image_url : 
        Image URL.

    Returns
    -------
    :
        Tuple of subprocess handle for 'docker run' and host port used for jupyter display.
    """

    if utils.system() == "Windows":
        popen_kwargs = dict(creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        popen_kwargs = dict(start_new_session = True)

    ssh_mount = Path.home() / '.ssh'
    anaconda_mount = Path.home() / '.anaconda'
    cwd_mount_source = Path.cwd()
    cwd_mount_target = Path.cwd()
    ssh_mount.mkdir(exist_ok=True)
    anaconda_mount.mkdir(exist_ok=True)
    if utils.system() == 'Windows':
        ssh_mount = PureWindowsPath(ssh_mount)
        anaconda_mount = PureWindowsPath(anaconda_mount)
        cwd_mount_source = PureWindowsPath(cwd_mount_source)
        cwd_mount_target = PurePosixPath(cwd_mount_source)
        parts = cwd_mount_target.parts
        assert ':' in parts[0]
        cwd_mount_target = PurePosixPath('/', *(cwd_mount_target.parts[1:]))

    port = '8888'
    occupied_ports = utils.jupyter_ports_in_use()
    if occupied_ports:
        term.echo(f"Default host port {port} is in use.", nl=False)
        port = str(max(occupied_ports) + 1)
        term.echo(f"Using port {port} instead.")

    # cmd = (
    #     # rf"docker run --memory {CONTAINER_MEMORY_LIMIT} --rm --label dk.au.gitlab.group={GITLAB_GROUP}"
    #     rf"docker run --rm --label dk.au.gitlab.group={GITLAB_GROUP}"
    #     rf" --mount type=bind,source={ssh_mount},target=/tmp/.ssh"
    #     rf" --mount type=bind,source={anaconda_mount},target=/root/.anaconda"
    #     rf" --mount type=bind,source={cwd_mount_source},target={cwd_mount_target}"
    #     rf" -w {cwd_mount_target} -i -p 8050:8050 -p {port}:8888 {image_url}:latest"
    # )
    cmd = (
        # rf"docker run --memory {CONTAINER_MEMORY_LIMIT} --rm --label dk.au.gitlab.group={GITLAB_GROUP}"
        rf"docker run --rm --label dk.au.gitlab.group={GITLAB_GROUP}"
        rf" --mount type=bind,source={anaconda_mount},target=/root/.anaconda"
        rf" --mount type=bind,source={cwd_mount_source},target={cwd_mount_target}"
        rf" -w {cwd_mount_target} -i -p 8050:8050 -p {port}:8888 {image_url}:latest"
    )
    logger.debug(cmd)

    cmd = cmd.split()
    cmd[0] = shutil.which(cmd[0])
    docker_run_p = Popen(cmd, 
                        stdout=DEVNULL, stderr=DEVNULL, 
                        **popen_kwargs)
    if docker_run_p.poll() is not None:
        raise Exception('Failed to start container')
    return docker_run_p, port

@click.argument("url")
@docker.command('run')
@ensure_docker_running
@crash_report
def _run(url):
    """Run container from image.
     
    Use for running locally built images.    
    """
    run(url)


###########################################################
# docker prune subcommands
###########################################################

@docker.group(cls=AliasedGroup)
@crash_report
def prune():
    """Docker pruning commands.
    """
    pass


def prune_networks():
    # _command(f'docker container prune --force --filter="dk.au.gitlab.group={GITLAB_GROUP}"')
    utils.run_cmd(f'docker network prune --force --filter="dk.au.gitlab.group={GITLAB_GROUP}"')

@prune.command('networks')
@crash_report
def _prune_networks():
    """Remove networks not used by at least one container.
    """
    prune_networks()


def prune_containers():
    """
    Prunes containers.
    """
    # _command(f'docker container prune --all --force --filter="dk.au.gitlab.group={GITLAB_GROUP}"', silent=True)
    utils.run_cmd(f'docker container prune --all --force --filter="dk.au.gitlab.group={GITLAB_GROUP}"', check=False)

@prune.command('containers')
@crash_report
def _prune_containers():
    """Prune containers.
    """
    prune_containers()


def prune_images():
    """
    Prunes images.
    """
    # _command(f'docker image prune --all --force --filter="dk.au.gitlab.group={GITLAB_GROUP}"', silent=True)
    utils.run_cmd(f'docker image prune --all --force --filter="dk.au.gitlab.group={GITLAB_GROUP}"', check=False)

@prune.command('images')
@crash_report
def _prune_images():
    """Prune images.
    """
    prune_images()

# def _prune_cache():
#     _command(f'docker system prune --all --force --filter="dk.au.gitlab.group={GITLAB_GROUP}"', silent=True)

# @docker.command('cache')
# def prune_cache():
#     """
#     Remove all dangling images.
#     """
#     _prune_cache()


def prune_all():
    """
    Prunes all Docker elements.
    """
    # _command(f'docker system prune --all --force --filter="dk.au.gitlab.group={GITLAB_GROUP}"', silent=True)
    utils.run_cmd(f'docker system prune --all --force --filter="dk.au.gitlab.group={GITLAB_GROUP}"', check=False)

@prune.command('all')
@crash_report
def _prune_all():
    """Prune all Docker elements.

    Remove stopped containers, unused networks, 
    dangling images, and unused build cache.
    """
    prune_all()




# docker build command


# def _build(directory=Path.cwd(), tag=None):

#     if tag is None:
#         check_output('')
#     git config --get remote.origin.url

#     tag = f'-t {tag}' if tag else ''
#     subprocess.run(utils.format_cmd(f'docker build --platform=linux/amd64 {directory} {tag}'), check=False)

#     git config --get remote.origin.url

#  -t franklin/genomic-thinking/arg-dashboard for build
# #docker build --platform=linux/amd64 -t kaspermunch/jupyter-linux-amd64:latest .

# @click.argument("directory")
# @click.option("--tag", help="Tag for the image")
# @docker.command()
# def build(directory, tag=None):
#     """
#     Build image from Dockerfile. Use for testing that the image builds correctly.
#     """
#     _build(directory, tag)





###########################################################
# docker kill subcommands
###########################################################

@docker.group(cls=AliasedGroup)
@crash_report
def kill():
    """Docker kill commands.
    """
    pass

def kill_container(container_id: str) -> None:
    """
    Kills a running container.

    Parameters
    ----------
    container_id : 
        Container ID.
    """
    cmd = fmt_cmd(f'docker kill {container_id}')
    Popen(cmd, stderr=DEVNULL, stdout=DEVNULL)

# def kill_container(container_id):
#     _kill_container(container_id)


# @docker.command('kill')
def kill_docker_processes() -> None:
    """
    Kills all docker-related processes using SIGTERM AND SIGKILL.
    """
    for process in psutil.process_iter():
        name = process.name().lower()
        if 'docker' in name and 'franklin' not in name:

            def on_terminate(proc):
                print("process {} terminated with exit code {}".format(proc, proc.returncode))

            children = psutil.Process(process.pid).children(recursive=True)
            for child in children:
                child.terminate()  # friendly termination
            _, still_alive = psutil.wait_procs(children, timeout=3, callback=on_terminate)
            for child in still_alive:
                child.kill()  # unfriendly termination


def shutdown_wsl():
    """
    Shuts down WSL
    """
    if utils.system() == 'Windows':
        logger.debug('Restarting WSL Docker Desktop distribution.')
        subprocess.check_call('wsl -t docker-desktop')
        term.dummy_progressbar(10, label='Restarting.')
        if docker_desktop_status() == 'running':
            return
        

def shutdown_wsl_docker_distribution():
    """
    Shuts down WSL Docker Desktop distribution
    """
    if utils.system() == 'Windows':
        logger.debug('Shutting down WSL Docker Desktop distribution.')
        term.echo('WSL needs to restart.')
        subprocess.check_call('wsl --shutdown')    
        term.dummy_progressbar(10, label='Restarting.')
        if docker_desktop_status() == 'running':
            return    


@kill.command('containers')
@click.argument("container_id", required=False)
@irrelevant_unless_docker_running
@crash_report
def kill_selected_containers(container_id: str=None) -> None:
    """
    If a container ID is given as argument, this container is killed.
    Otherwise kills containers selected from a list of running containers. 

    Parameters
    ----------
    container_id : 
        Container ID, by default None
    """

    if container_id:
        kill_container(container_id)
        return
    
    container_list(callback=kill_container)


###########################################################
# docker show subcommands
###########################################################

@docker.group(cls=AliasedGroup)
@crash_report
def show():
    """Docker show commands
    """
    pass


# def containers(return_json=False):
def containers() -> List[Dict[str, Any]]:
    """
    Get information about running containers.

    Returns
    -------
    :
        List of dictionaries with information about running containers.
    """

    # return _command('docker ps --all --size', return_json=return_json)
    output = utils.run_cmd('docker ps --all --size --format json')
    return [json.loads(line) for line in output.strip().splitlines()]

@show.command('containers')
@ensure_docker_running
@crash_report
def _containers():
    """Show running docker containers.
    """
    container_list()
    # term.echo(_containers(), nowrap=True)


def storage(verbose=False):
    """
    Information about storage usage.
    """
    if verbose:
        # return _command(f'docker system df -v')
        return utils.run_cmd('docker system df -v')
    # return _command(f'docker system df')
    return utils.run_cmd(f'docker system df')

@click.option("--verbose/--no-verbose", default=False, help="More detailed output")
@show.command('storage')
@ensure_docker_running
@crash_report
def _storage(verbose):
    """Show Docker's disk usage."""
    term.echo(storage(verbose), nowrap=True)


def logs() -> List[Dict[str, Any]]:
    """
    Docker Desktop logs.

    Parameters
    ----------
    return_json : 
        _description_, by default False

    Returns
    -------
    :
        List of dictionaries with log information.
    """
    # _command('docker desktop logs', return_json=return_json)
    output = utils.run_cmd('docker desktop logs --format json')
    return [json.loads(line) for line in output.strip().splitlines()]


@show.command('logs')
@crash_report
def _logs():
    """Show Docker Desktop logs.
    """
    logs()


def volumes() -> List[Dict[str, Any]]:
    """
    Docker volumes.

    Returns
    -------
    :
        List of dictionaries with volume information.
    """
    output = utils.run_cmd('docker volume ls --format json')
    return [json.loads(line) for line in output.strip().splitlines()]

@show.command('volumes')
@ensure_docker_running
@crash_report
def _volumes():
    """List docker volumes.
    """
    term.echo(volumes(), nowrap=True)


def images() -> List[Dict[str, Any]]:
    """
    Docker images.

    Returns
    -------
    :
        List of dictionaries with image information.
    """
    # return _command('docker images', return_json=return_json)
    output = utils.run_cmd('docker images --format json')
    return [json.loads(line) for line in output.strip().splitlines()]

@show.command('images')
@ensure_docker_running
@crash_report
def _images():
    """List docker images.
    """
    # term.echo(_images(), nowrap=True)
    image_list()


###########################################################
# docker remove subcommands
###########################################################

@docker.group(cls=AliasedGroup)
@ensure_docker_running
@crash_report
def remove():
    """Remove Docker images and volumes
    """
    pass


def rm_container(container, force=False) -> None:
    """
    Remove container.

    Parameters
    ----------
    container : 
        Container ID.
    force : 
        Force removal if container is in use, by default False
    """
    if force:
        # _command(f'docker rm -f {container}', silent=True)
        utils.run_cmd(f'docker rm -f {container}', check=False)

    else:
        # _command(f'docker rm {container}', silent=True)
        utils.run_cmd(f'docker rm {container}', check=False)

@remove.command('containers')
@click.argument("container_id", required=False)
@crash_report
def remove_selected_containers(container_id=None):
    """Remove selected containers.
    """
    if container_id:
        rm_container(container_id)
        return
    
    container_list(callback=rm_container)


def rm_image(image, force=False):
    """
    Remove image.

    Parameters
    ----------
    image : 
        Image ID.
    force : 
        Force removal if image is in use, by default False
    """    
    if force:
        # _command(f'docker image rm -f {image}', silent=True)
        utils.run_cmd(f'docker image rm -f {image}', check=False)
    else:
        # _command(f'docker image rm {image}', silent=True)
        utils.run_cmd(f'docker image rm {image}', check=False)

@remove.command('images')
@click.argument("image_id", required=False)
@crash_report
def remove_selected_images(image_id=None):
    """Remove selected containers.
    """
    if image_id:
        rm_image(image_id)
        return
    image_list(callback=rm_image)

def remove_everything():
    # _command(f'docker system prune --all --force --filter="dk.au.gitlab.group={GITLAB_GROUP}"', silent=True)
    utils.run_cmd(f'docker system prune --all --force --filter="dk.au.gitlab.group={GITLAB_GROUP}"', check=False)

@remove.command('everything')
@crash_report
def _remove_everything():
    """Remove all Docker elements.
    """
    remove_everything()             

###########################################################
# docker config subcommands
###########################################################





@docker.group(cls=AliasedGroup)
@crash_report
def config():
    """Docker configuration.
    """
    pass


@config.command('get')
@click.argument("variable", required=False)
@crash_report
def _config_get(variable=None):
     """Get value of Docker configuration variable.
     """
     return config_get(variable=variable)
     

@config.command('set')
@click.argument("variable", required=True)
@click.argument("value", required=True)
@crash_report
def _config_set(variable, value):
    """Set Docker configuration variable.
    """
    return config_set(variable, value)


@config.command('reset')
@click.argument("variable", required=False)
@crash_report
def _config_reset(variable):
    """Reset Docker configuration variable
    """
    return config_reset(variable=variable)


@config.command('fit')
@crash_report
def _config_fit():
    return config_fit()

# uninstall
#/Applications/Docker.app/Contents/MacOS/uninstall
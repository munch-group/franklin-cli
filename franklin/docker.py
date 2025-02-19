import platform
import subprocess
from subprocess import DEVNULL
import json
import sys
import os
import click
import shutil
import time
import requests
from .utils import format_cmd
from .config import REGISTRY_BASE_URL, GITLAB_GROUP, REQUIRED_GB_FREE_DISK
from . import cutie
from .gitlab import get_course_names, get_exercise_names
from .logger import logger




def _docker_desktop_installed():
    if platform.system() == 'Darwin':
        return shutil.which('docker')
    if platform.system() == 'Linux':
        return shutil.which('docker')
    if platform.system() == 'Windows':
        return shutil.which('docker')
    return False

# def _free_disk_space():
    


# def _check_docker_desktop_running():
    
#     # processes = [p.name() for p in psutil.process_iter() if 'docker desktop' in p.name().lower()]
#     # if not processes:
#     #     return False
#     # return True

#     return _status() == 'running'


def _check_internet_connection():
    try:
        request = requests.get("https://hub.docker.com/", timeout=2)
        return True
    except (requests.ConnectionError, requests.Timeout) as exception:
        return False


def _prepare_user_setup(allow_subdirs=False):

    if not _docker_desktop_installed():
        click.secho("The Docker Desktop application is not installed on your computer.", fg='red')
        click.secho('Visit https://www.docker.com/products/docker-desktop and click the big blue "Download Docker Desktop" button.', fg='red')
        sys.exit(1)

    if not _status() == 'running':
        click.secho("Need to start Docker Desktop. Please wait.", fg='green')
        _restart()
    for _ in range(10):
        if _status() == 'running':                
            break
        time.sleep(6)
    if not _status() == 'running':
        click.secho("Could not start Docker Desktop. Please start Docker Desktop manually.", fg='red')
        sys.exit(1)
    click.secho('Docker Desktop is running', fg='green')


    if not _check_internet_connection():
        click.secho("No internet connection. Please check your network.", fg='red')
        sys.exit(1)


    gb_free = shutil.disk_usage('/').free / 1024**3
    if gb_free < REQUIRED_GB_FREE_DISK:
        click.secho(f"Not enough free disk space. Required: {REQUIRED_GB_FREE_DISK} GB, Available: {gb_free:.2f} GB", fg='red')
        sys.exit(1)
    elif gb_free < 2 * REQUIRED_GB_FREE_DISK:
        click.secho(f"Low disk space. Required: {REQUIRED_GB_FREE_DISK} GB, Available: {gb_free:.2f} GB", fg='yellow')
    else:     
        click.secho(f"Free disk space: {gb_free:.2f} GB", fg='green')

    dirs_in_cwd = any(os.path.isdir(x) for x in os.listdir(os.getcwd()))
    if dirs_in_cwd and not allow_subdirs:
        msg = click.secho("Please run the command in a directory without any sub-directories.", fg='red')
        sys.exit(1)


    # for dir, _, _ in os.walk('.'):
    #     if len(dir.split('/')) > allowed_depth:
    #         print(dir)
    #         return True
    # return False


    # if _above_subdir_limit(SUBDIR_LIMIT):
    #     msg = click.wrap_text(
    #         f"Please run the command in a directory without any sub-directories.",
    #         width=shutil.get_terminal_size().columns - 2, 
    #         initial_indent='', subsequent_indent='', preserve_paragraphs=True)
    #     click.secho(msg, fg='red')
    #     sys.exit(1)


def _image_exists(image_url):
    for image in images(return_json=True):
        if image['Repository'].startswith(image_url):
            return True
    return False

def _command(command, silent=False, return_json=False):
    if silent:
        return subprocess.run(format_cmd(command), check=False, stdout=DEVNULL, stderr=DEVNULL)
    if return_json:
        result = []
        for line in subprocess.check_output(format_cmd(command + ' --format json')).decode().strip().splitlines():
            result.append(json.loads(line))
        return result
    else:
        return subprocess.check_output(format_cmd(command)).decode().strip()


@click.group()
def docker():
    """Docker commands."""

    pass


def _pull(image_url):
    subprocess.run(format_cmd(f'docker pull {image_url}:main'), check=False)

@click.argument("url")
@docker.command()
def _pull(url):
    """Pull docker image.
    
    URL is the Docker image URL.
    """
    _pull(url)


def _containers(return_json=False):
    return _command('docker ps', return_json=return_json)

@docker.command()
def containers():
    """List docker containers."""
    click.echo(_containers())


def _kill(container_id):
    _command(f'docker kill {container_id}', silent=True)

@click.argument('container')
@docker.command()
def kill(container):
    """Kills a running container.
    
    CONTAINER is the id of the container to kill."""
    _kill(container)


def _storage(verbose=False):
    if verbose:
        return _command(f'docker system df -v')
    return _command(f'docker system df')

@click.option("--verbose/--no-verbose", default=False, help="More detailed output")
@docker.command()
def storage(verbose):
    """Show Docker's disk usage."""
    click.echo(_storage(verbose))


def _logs(return_json=False):
    _command('docker desktop logs', return_json=return_json)

@docker.command()
def logs():
    _logs()


def _restart():
    _command(('docker desktop restart'), silent=True)

@docker.command()
def restart():
    """Restart Docker Desktop"""
    _restart()


def _start():
    _command('docker desktop start', silent=True)

@docker.command()
def start():
    """Start Docker Desktop"""
    _start()


def _stop():
    _command('docker desktop stop', silent=True)

@docker.command()
def stop():
    """Stop Docker Desktop"""
    _stop()


def _status():
    stdout = subprocess.check_output(format_cmd('docker desktop status --format json')).decode()
    data = json.loads(stdout)
    return data['Status']

@docker.command()
def status():
    "Docker Desktop status"
    s = _status()
    fg = 'green' if s == 'running' else 'red'
    click.secho(s, fg=fg)


def _update(return_json=False):
    return _command('docker desktop update', return_json=return_json)

@docker.command()
def update():
    """Update Docker Desktop"""
    _update()


def _version(return_json=False):
    _command('docker desktop version --format json', return_json=return_json)

@docker.command()
def version():
    """Get Docker Desktop version"""
    _version()


def _volumes(return_json=False):
    return _command('docker volume ls', return_json=return_json)

@docker.command()
def volumes():
    """List docker volumes."""
    click.echo(_volumes())


def _images(return_json=False):
    return _command('docker images', return_json=return_json)

@docker.command()
def images():
    """List docker images."""
    click.echo(_images())





# def prune_containers():
#     _command(f'docker container prune --filter="Name={REGISTRY_BASE_URL}*"', silent=True)


# def prune_volumes():
#     _command(f'docker volume --filter="Name={REGISTRY_BASE_URL}*"')


# def prune_all():
#     _command(f'docker prune -a', silent=True)


# def rm_image(image, force=False):
#     if force:
#         _command(f'docker image rm -f {image}', silent=True)
#     else:
#         _command(f'docker image rm {image}', silent=True)




# def cleanup():
#     for image in images():
#         if image['Repository'].startswith(REGISTRY_BASE_URL):
#             rm_image(image['ID'])
#     prune_containers()
#     prune_volumes()
#     prune_all()



###########################################################
# remove subcommand
###########################################################

@docker.group()
def remove():
    """Remove Docker elements."""
    pass


def _remove_images():
    img = images(return_json=True)
    if not img:
        click.echo("\nNo images to remove\n")
        return

    course_names = get_course_names()
    exercise_names = {}

    header = ['Course', 'Exercise', 'Created', 'Size', 'ID']
    table = []
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
            course_field = course_field[:20]+'...' if len(course_name) > 23 else course_name
            table.append((course_names[course_label], exercise_names[exercise_label], img['CreatedSince'], img['Size'], img['ID']))

    col_widths = [max(len(x) for x in col) for col in zip(*table)]

    table_width = sum(col_widths) + 4 * len(col_widths) + 2
    # print(table_width)
    click.secho("\nChoose images to remove:", fg='green')

    click.echo("\nUse arrows to move highlight and space to select/deselect one or more images. Press enter to remove \n")

    click.echo('    | '+'| '.join([x.ljust(w+2) for x, w in zip(header, col_widths)]))
    click.echo('-'*table_width)
    rows = []
    for row in table:
        rows.append('| '+'| '.join([x.ljust(w+2) for x, w in zip(row, col_widths)]))
    captions = []
    selected_indices = cutie.select_multiple(
        rows, caption_indices=captions, 
        # hide_confirm=False
    )
    for img_id in [table[i][-1] for i in selected_indices]:
        rm_image(img_id, force=True)


@remove.command()
def images():
    _remove_images()


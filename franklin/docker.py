import platform
import subprocess
from subprocess import run, check_output, Popen, PIPE, DEVNULL
import json
import sys
import os
import re
import click
import requests
import shutil
import time
import psutil
import sysconfig
from . import utils
from .config import REGISTRY_BASE_URL, GITLAB_GROUP, REQUIRED_GB_FREE_DISK
from . import cutie
from .gitlab import get_course_names, get_exercise_names
from .logger import logger
from pathlib import Path
from filecmp import dircmp

def _docker_desktop_settings(**kwargs):

    home = Path.home()
    if platform.system() == 'Darwin':
        json_settings = home / 'Library/Group Containers/group.com.docker/settings-store.json'
    elif platform.system() == 'Windows':
        json_settings = home / '/AppData/Roaming/Docker/settings-store.json'
    elif platform.system() == 'Linux':
        json_settings = home / '.docker/desktop/settings-store.json'

    with open(json_settings, 'r') as f:
        settings = json.load(f)

    if not kwargs:
        return settings
    
    for key, value in kwargs.items():
        settings[key] = value

    with open(json_settings, 'w') as f:
        json.dump(settings, f)


def _install_docker_desktop():

    utils.secho(f"\nInstalling Docker desktop.", fg='green')

    architecture = sysconfig.get_platform().split('-')[-1]
    assert architecture in ['amd64', 'arm64']

    if platform.system() == 'Windows':
        if architecture == 'arm64':
            download_url = 'https://desktop.docker.com/win/main/arm64/Docker%20Desktop%20Installer.exe'
        else:
            download_url = 'https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe'
        installer = 'Docker Desktop Installer.exe'
    elif platform.system() == 'Darwin':
        if architecture == 'arm64':
            download_url = 'https://desktop.docker.com/mac/main/arm64/Docker.dmg'
        else:
            download_url = 'https://desktop.docker.com/mac/main/amd64/Docker.dmg'
        installer = 'Docker.dmg'
    else:
        url = 'https://docs.docker.com/desktop/linux/install/'
        utils.echo(f'Download from {url} and install before proceeding.')
        sys.exit(1)

    response = requests.get(download_url, stream=True)
    if not response.ok:





        utils.echo(f"Could not download Docker Desktop. Please download from {download_url} and install before proceeding.")
        sys.exit(1)

    file_size = response.headers['Content-length']
    with open(installer, mode="wb") as file:
        nr_chunks = int(file_size) // (10 * 1024) + 1
        with click.progressbar(length=nr_chunks, label='Downloading', fill_char='#') as bar:
            for chunk in response.iter_content(chunk_size=10 * 1024):
                file.write(chunk)
                bar.update(1)

    def _run(cmd):
        logger.debug(cmd)
        cmd = cmd.split()
        cmd[0] = shutil.which(cmd[0])
        return check_output(cmd).decode().strip()
    
    if platform.system() == 'Windows':

        utils.echo("Installing:")
        utils.echo()
        utils.secho('='*75, fg='red')
        utils.echo('  You will be prompted for install permission. Accept follow the installation procedure. Once completed, return to this window.', fg='red')
        utils.secho('='*75, fg='red')
        utils.echo()
        click.pause()

        utils.echo(" - Removing installer...")
        os.remove(installer)

        run(installer, check=True)
    elif platform.system() == 'Darwin':
        cmd = f'hdiutil attach -nobrowse -readonly {installer}'
        logger.debug(cmd)
        cmd = cmd.split()
        cmd[0] = shutil.which(cmd[0])
        output = check_output(cmd).decode().strip()

        # Extract the mounted volume name from the output
        mounted_volume_name = re.search(r'/Volumes/([^ ]*)', output.strip()).group(1)

        utils.echo("Installing:")
        utils.echo()
        utils.secho('='*75, fg='red')
        utils.echo('  Press Enter and then drag the Docker to the Applications folder.', fg='red')
        utils.secho('='*75, fg='red')
        utils.echo()
        click.pause('Press Enter...')

        _run(f'open /Volumes/{mounted_volume_name}')

        utils.echo(" - Copying to Applications...")
        output = _run(f'du -s /Volumes/Docker/Docker.app')
        source_size = output.split()[0]

        prev_size = ''
        for _ in range(1000):
            cmd = f'du -s /Applications/Docker.app'
            logger.debug(cmd)
            cmd = cmd.split()
            cmd[0] = shutil.which(cmd[0])
            output = run(cmd, stdout=PIPE, stderr=DEVNULL, timeout=1, check=False).stdout.decode().strip()
            if output:
                size = output.split()[0]
                if size == prev_size:
                    break
                prev_size = size
            time.sleep(5)

        time.sleep(5)

        # # allow some time for the app to be copied and validated...
        # with click.progressbar(length=10, label='Validating Docker Desktop', fill_char='#') as bar:
        #     for _ in range(10):
        #         time.sleep(1)
        #         bar.update(1)

        utils.echo(" - Unmounting...")

        if os.path.exists('/Volumes/{mounted_volume_name}'):
            _run(f'hdiutil detach /Volumes/{mounted_volume_name}/')

        utils.echo(" - Removing installer...")
        os.remove(installer)

    utils.echo(" - Setup...")
    # Disable the "Open on startup"
    _docker_desktop_settings(OpenUIOnStartupDisabled=True)


#  start /w "" "Docker Desktop Installer.exe" uninstall
#  /Applications/Docker.app/Contents/MacOS/uninstall

def _start_docker_desktop():
    if not _status() == 'running':
        utils.logger.debug('Starting/restarting Docker Desktop')
        _restart()
    for w in range(10):
        if _status() == 'running':                
            break
        time.sleep(1)
    utils.echo()


def _failsafe_start_docker_desktop():
    
    if not shutil.which('docker'):
         _install_docker_desktop()

    _start_docker_desktop()

    if not _status() == 'running':
        utils.logger.debug('Killing all Docker Desktop processes')
        _kill_all_docker_desktop_processes()
        _start_docker_desktop()

    if not _status() == 'running':
        utils.logger.debug('Could not start Docker Desktop. Please start Docker Desktop manually')
        utils.secho("Could not start Docker Desktop. Please start Docker Desktop manually.", fg='red')
        sys.exit(1)


def _image_exists(image_url):
    for image in _images(return_json=True):
        if image['Repository'].startswith(image_url):
            return True
    return False


def _command(command, silent=False, return_json=False):
    if silent:
        return subprocess.run(utils.format_cmd(command), check=False, stdout=DEVNULL, stderr=DEVNULL)
    if return_json:
        result = []
        for line in subprocess.check_output(utils.format_cmd(command + ' --format json')).decode().strip().splitlines():
            result.append(json.loads(line))
        return result
    else:
        return subprocess.check_output(utils.format_cmd(command)).decode().strip()


def _multi_select_table(header, table, ids):

    col_widths = [max(len(x) for x in col) for col in zip(*table)]

    table_width = sum(col_widths) + 4 * len(col_widths) + 2

    utils.echo("Use up/down arrows to navigate and Space to select/deselect.\n")

    utils.echo('    | '+'| '.join([x.ljust(w+2) for x, w in zip(header, col_widths)]), nowrap=True)
    click.echo('-'*table_width)
    rows = []
    for row in table:
        rows.append('| '+'| '.join([x.ljust(w+2) for x, w in zip(row, col_widths)]))
    captions = []
    selected_indices = cutie.select_multiple(
        rows, caption_indices=captions, 
        hide_confirm=False
    )
    return [ids[i]for i in selected_indices]


###########################################################
# docker subcommands
###########################################################

@click.group()
def docker():
    """Docker commands."""
    pass


def _pull(image_url):
    subprocess.run(utils.format_cmd(f'docker pull {image_url}:main'), check=False)

@click.argument("url")
@docker.command()
def pull(url):
    """Pull docker image.
    
    URL is the Docker image URL.
    """
    _pull(url)


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
    stdout = subprocess.run(utils.format_cmd('docker desktop status --format json'), 
                            check=False, stderr=DEVNULL, stdout=PIPE).stdout.decode()
    if not stdout:
        return 'not running'
    # stdout = subprocess.check_output(utils.format_cmd('docker desktop status --format json')).decode()
    data = json.loads(stdout)
    return data['Status']

@docker.command()
def status():
    "Docker Desktop status"
    s = _status()
    fg = 'green' if s == 'running' else 'red'
    utils.secho(s, fg=fg, nowrap=True)


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


def _prune():
    _command(f'docker system prune --all --force --filter="Name={REGISTRY_BASE_URL}*"', silent=True)

@docker.command()
def prune():
    """
    Remove, all stopped containers, all networks not used by at 
    least one container all dangling images, unused build cache.
    """
    _prune()

###########################################################
# docker kill subcommands
###########################################################

@docker.group()
def kill():
    """Kill Docker elements."""
    pass


def _kill_container(container_id):
    """Kill a running container."""
    run(utils.format_cmd(f'docker kill {container_id}'), check=False, stderr=DEVNULL, stdout=DEVNULL)

@click.argument("container_id")
@kill.command('container')
def kill_container(container_id):
    _kill_container(container_id)


@kill.command('everything')
def _kill_all_docker_desktop_processes():
    """Kills all docker-related processes."""
    for process in psutil.process_iter():
        if 'docker' in process.name().lower():
            pid = psutil.Process(process.pid)
            if not 'SYSTEM' in pid.username():
                process.kill()
                
@kill.command('container')
def _kill_selected_containers():
    cont = _containers(return_json=True)
    if not cont:
        click.echo("\nNo running containers to kill\n")
        return

    course_names = get_course_names()
    exercise_names = {}

    header = ['Course', 'Exercise', 'Started']
    table = []
    ids = []
    prefix = f'{REGISTRY_BASE_URL}/{GITLAB_GROUP}'
    for cont in _containers(return_json=True):
        if cont['Image'].startswith(prefix):
            rep = cont['Image'].replace(prefix, '')
            if rep.endswith(':main'):
                rep = rep[:-5]
            if rep.startswith('/'):
                rep = rep[1:]
            course_label, exercise_label = rep.split('/')
            if exercise_label not in exercise_names:
                exercise_names.update(get_exercise_names(course_label))
            course_name = course_names[course_label]
            exercise_name = exercise_names[exercise_label]
            course_field = course_name[:30]+'...' if len(course_name) > 33 else course_name
            exercise_field = exercise_name[:30]+'...' if len(exercise_name) > 33 else exercise_name
            # table.append((course_field, exercise_field , img['CreatedSince'], img['Size'], img['ID']))
            ids.append(cont['ID'])
            table.append((course_field, exercise_field , cont['RunningFor']))

    utils.secho("\nChoose containes to kill:", fg='green')

    for cont_id in _multi_select_table(header, table, ids):
        _kill_container(cont_id, force=True)

###########################################################
# docker prune subcommands
###########################################################

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

###########################################################
# docker show subcommands
###########################################################


@docker.group()
def show():
    pass


def _containers(return_json=False):
    return _command('docker ps', return_json=return_json)

@show.command()
def containers():
    """List docker containers."""
    utils.echo(_containers(), nowrap=True)


def _storage(verbose=False):
    if verbose:
        return _command(f'docker system df -v')
    return _command(f'docker system df')

@click.option("--verbose/--no-verbose", default=False, help="More detailed output")
@show.command()
def storage(verbose):
    """Show Docker's disk usage."""
    utils.echo(_storage(verbose), nowrap=True)


def _logs(return_json=False):
    _command('docker desktop logs', return_json=return_json)

@show.command()
def logs():
    _logs()


def _volumes(return_json=False):
    return _command('docker volume ls', return_json=return_json)

@show.command()
def volumes():
    """List docker volumes."""
    utils.echo(_volumes(), nowrap=True)


def _images(return_json=False):
    return _command('docker images', return_json=return_json)

@show.command()
def images():
    """List docker images."""
    utils.echo(_images(), nowrap=True)


###########################################################
# docker remove subcommands
###########################################################

def _rm_image(image, force=False):
    if force:
        _command(f'docker image rm -f {image}', silent=True)
    else:
        _command(f'docker image rm {image}', silent=True)


@docker.group()
def remove():
    """Remove Docker elements."""
    pass


@remove.command('image')
def _remove_selected_images():
    img = _images(return_json=True)
    if not img:
        click.echo("\nNo images to remove\n")
        return

    course_names = get_course_names()
    exercise_names = {}

    # header = ['Course', 'Exercise', 'Created', 'Size', 'ID']
    header = ['Course', 'Exercise', 'Created', 'Size']
    table = []
    ids = []
    prefix = f'{REGISTRY_BASE_URL}/{GITLAB_GROUP}'
    for img in _images(return_json=True):
        if img['Repository'].startswith(prefix):

            rep = img['Repository'].replace(prefix, '')
            if rep.startswith('/'):
                rep = rep[1:]
            course_label, exercise_label = rep.split('/')
            if exercise_label not in exercise_names:
                exercise_names.update(get_exercise_names(course_label))
            course_name = course_names[course_label]
            exercise_name = exercise_names[exercise_label]
            course_field = course_name[:30]+'...' if len(course_name) > 33 else course_name
            exercise_field = exercise_name[:30]+'...' if len(exercise_name) > 33 else exercise_name
            # table.append((course_field, exercise_field , img['CreatedSince'], img['Size'], img['ID']))
            ids.append(img['ID'])
            table.append((course_field, exercise_field , img['CreatedSince'], img['Size']))

    utils.secho("\nChoose images to remove:", fg='green')

    for img_id in _multi_select_table(header, table, ids):
        _rm_image(img_id, force=True)



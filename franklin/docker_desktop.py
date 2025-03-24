import sysconfig
import os
import re
from . import terminal as term
from . import utils
import sys
import requests
import click
import json
from .config import WRAP_WIDTH, PG_OPTIONS, DOCKER_SETTINGS
from subprocess import check_output, DEVNULL, TimeoutExpired
from .logger import logger
import subprocess
import time
import shutil
from packaging.version import Version, InvalidVersion
import psutil
from pathlib import Path
from typing import Any


class docker_config():
    """
    Contest manager for Docker Desktop settings.
    """
    def __init__(self):
        home = Path.home()
        if utils.system() == 'Darwin':
            self.json_settings = home / 'Library/Group Containers/group.com.docker/settings-store.json'
        elif utils.system() == 'Windows':
            self.json_settings = home / 'AppData/Roaming/Docker/settings-store.json'
        elif utils.system() == 'Linux':
            self.json_settings = home / '.docker/desktop/settings-store.json'

    def user_config_file(self):
        if os.path.exists(self.json_settings):
            return self.json_settings
        return None

    def __enter__(self):
        if os.path.exists(self.json_settings):
            with open(self.json_settings, 'r') as f:
                self.settings = json.load(f)
        else:
             self.settings = dict()
        return self

    def __exit__(self, type, value, traceback):
        if self.settings:
            with open(self.json_settings, 'w') as f:
                json.dump(self.settings, f)


def config_get(variable: str=None) -> None:
    """
    Get Docker configuration for variable or all variables.

    Parameters
    ----------
    variable : 
        Variable name, by default None in which case all variables are shown.
    """
    with docker_config() as cfg:
        if variable is not None:
            if variable not in DOCKER_SETTINGS:
                term.echo(f'Variable "{variable}" cannot be accessed by Franklin.')
                return
            term.echo(f'{variable}: {cfg.settings[variable]}')
        else:
            for variable in DOCKER_SETTINGS:
                if variable in cfg.settings:
                    term.echo(f'{str(variable).rjust(31)}: {cfg.settings[variable]}')


def config_set(variable: str, value: Any) -> None:
    """
    Set value of Docker configuration variable.

    Parameters
    ----------
    variable : 
        Variable name.
    value : 
        Variable value.
    """

    if type(value) is str:
        value = utils.as_type(value)

    if value == 'DiskSizeMiB':
        # for some reason Docker Desktop only accepts values in multiples of 1024
        value = int(value / 1024) * 1024

    if variable not in DOCKER_SETTINGS:
        term.echo(f'Variable "{variable}" cannot be set/changed by Franklin.')
        return

    with docker_config() as cfg:
        logger.debug(f"Setting {variable} to {value}")
        cfg.settings[variable] = value


def _config_reset(variable: str=None) -> None:
    """
    Resets Docker configuration to defaults set by Franklin.

    Parameters
    ----------
    variable : 
        Variable name, by default None in which case all variables are reset.
    """
    with docker_config() as cfg:
        if variable is not None:
            if variable not in DOCKER_SETTINGS:
                term.echo(f'Variable "{variable}" cannot be accessed by Franklin.')
                return
            logger.debug(f"Resetting {variable} to {DOCKER_SETTINGS[variable]}")
            cfg.settings[variable] = DOCKER_SETTINGS[variable]
        else:
            for variable in DOCKER_SETTINGS:
                logger.debug(f"Resetting {variable} to {DOCKER_SETTINGS[variable]}")
                cfg.settings[variable] = DOCKER_SETTINGS[variable]


def config_fit():
    """Set resource limits to reasonable values given available resources.
    """

    _config_reset()

    nr_cpu = psutil.cpu_count(logical=True)
    logger.debug(f"Fitting Cpus to {int(nr_cpu // 2)}")
    config_set('Cpus', int(nr_cpu // 2))

    svmem = psutil.virtual_memory()
    mem_mb = svmem.total // (1024 ** 2)
    logger.debug(f"Fitting MemoryMiB to {int(mem_mb // 2)}")
    config_set('MemoryMiB', int(mem_mb // 2))


def install_docker_desktop() -> None:
    """
    Downloads and installs Docker Desktop on Windows or Mac.
    """
    architecture = sysconfig.get_platform().split('-')[-1]
    assert architecture

    operating_system = utils.system()



    if operating_system == 'Windows':
        if architecture == 'arm64':
            download_url = 'https://desktop.docker.com/win/main/arm64/Docker%20Desktop%20Installer.exe'
        else:
            download_url = 'https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe'
        installer = 'Docker Desktop Installer.exe'
    elif operating_system == 'Darwin':
        if architecture == 'arm64':
            download_url = 'https://desktop.docker.com/mac/main/arm64/Docker.dmg'
        else:
            download_url = 'https://desktop.docker.com/mac/main/amd64/Docker.dmg'
        installer = 'Docker.dmg'
    else:
        url = 'https://docs.docker.com/desktop/linux/install/'
        term.echo(f'Download from {url} and install before proceeding.')
        sys.exit(1)

    if (Path.home() / 'Downloads').exists():
        installer_dir = str(Path.home() / 'Downloads')
    elif (Path.home() / 'Overførsler').exists():
        installer_dir = str(Path.home() / 'Overførsler')
    else: 
        installer_dir = os.getcwd()

    installer_path = os.path.join(installer_dir, installer)

    term.boxed_text(f"Franklin needs Docker Desktop", 
                     ['Franklin depends on a program called Docker Desktop and will download a Docker Desktop installer to your Downloads folder.'],
                     prompt='Press Enter to start the download...', 
                     fg='green')

    response = requests.get(download_url, stream=True)
    if not response.ok:
        term.echo(f"Could not download Docker Desktop. Please download from {download_url} and install before proceeding.")
        sys.exit(1)
    else:
        term.echo(f"Will download installer to {installer_path}.")

    file_size = response.headers['Content-length']
    with open(installer_path, mode="wb") as file:
        nr_chunks = int(file_size) // (10 * 1024) + 1
        with click.progressbar(length=nr_chunks, label='Downloading:'.ljust(25), **PG_OPTIONS) as bar:
            for chunk in response.iter_content(chunk_size=10 * 1024):
                file.write(chunk)
                bar.update(1)

    # if the user already has a user config file, we temporarily set OpenUIOnStartupDisabled 
    # to False so that the user can see the Dashboard under the install procedure
    with docker_config() as cfg:
        if cfg.user_config_file():            
            cfg.settings['OpenUIOnStartupDisabled'] = False


    if utils.system() == 'Windows':
        kwargs = dict(subsequent_indent=' '*5)
        term.echo()
        term.echo()
        term.secho(f"How to install Docker Desktop on Windows:", fg='green')
        term.secho('='*WRAP_WIDTH, fg='green')
        term.echo()
        term.echo("  Please follow this exact sequence of steps:")
        term.echo()
        term.echo('  1. If you are a teacher, you must turn on admin privileges in Heimdal', **kwargs)
        term.echo('  2. Double-click the "Docker Desktop Installer.exe" file.', **kwargs)
        term.echo('  3. Follow the default installation procedure and accept/connect when prompted.', **kwargs)
        term.echo('  4. When the installation is completed, open Docker Desktop.', **kwargs)
        term.echo('  5. Accept the Docker Desktop license agreement')
        term.echo('  6. When you are asked to log in or create an account, just click skip.', **kwargs)
        term.echo('  7. When you are asked to take a survey, just click skip.', **kwargs)
        # term.echo('  8. Wait while it says "Starting the Docker Engine..."')
        term.echo('  8. If it says "New version available" in the bottom right corner, click that to update (scroll to find the blue button)"', **kwargs)
        term.echo('  9. Quit the Docker application. Then return to this window and start Franklin the same way as you did before', **kwargs)
        term.echo()
        term.echo('  Press Enter to close Franklin.')
        term.echo()
        term.echo('='*WRAP_WIDTH, fg='green')
        click.pause('')
        sys.exit(0)

    elif utils.system() == 'Darwin':
        cmd = utils.fmt_cmd(f'hdiutil attach -nobrowse -readonly {installer}')
        output = check_output(cmd).decode().strip()

        # Extract the mounted volume name from the output
        mounted_volume_name = re.search(r'/Volumes/([^ ]*)', output.strip()).group(1)

        term.echo('\nPress Enter and then drag the Docker application to the Applications folder.', fg='red')
        
        check_output(utils.fmt_cmd(f'open /Volumes/{mounted_volume_name}')).decode().strip()

        term.echo('\nDid you drag the Docker application to the Applications folder? If you did, press Enter to continue.', fg='red')

        with click.progressbar(length=100, label='Copying to Applications:'.ljust(25), **PG_OPTIONS) as bar:
            prev_size = 0
            for _ in range(1000):
                cmd = f'du -s /Applications/Docker.app'
                logger.debug(cmd)
                cmd = cmd.split()
                cmd[0] = shutil.which(cmd[0])
                output = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=1, check=False).stdout.decode().strip()
                if output:
                    size = int(output.split()[0])
                    if size == prev_size:
                        break
                    bar.update(int(100*(1 - (size - prev_size) / int(size))))
                    prev_size = size
                time.sleep(5)

        term.dummy_progressbar(seconds=10, label='Validating Docker Desktop:')

        logger.debug("Unmounting volume")
        if os.path.exists('/Volumes/{mounted_volume_name}'):
            utils.run_cmd(f'hdiutil detach /Volumes/{mounted_volume_name}/')

        logger.debug("Removing installer dmg")
        os.remove(installer)

        kwargs = dict(subsequent_indent=' '*5)
        term.echo()
        term.echo()
        term.secho(f"How to set up Docker Desktop on Mac:", fg='green')
        term.secho('='*WRAP_WIDTH, fg='green')
        term.echo()
        term.echo("  Please follow this exact sequence of steps:")
        term.echo()
        term.echo('  1. Open the Docker application from your Applications folder', **kwargs)
        term.echo('  3. Follow the default installation procedure.', **kwargs)
        term.echo('  4. When the installation is completed, open Docker Desktop.', **kwargs)
        term.echo('  5. Accept the Docker Desktop license agreement')
        term.echo('  6. When you are asked to log in or create an account, just click skip.', **kwargs)
        term.echo('  7. When you are asked to take a survey, just click skip.', **kwargs)
        # term.echo('  8. Wait while it says "Starting the Docker Engine..."')
        term.echo('  8. If it says "New version available" in the bottom right corner, click that to update (scroll to find the blue button)"', **kwargs)
        term.echo('  9. Quit the Docker application.', **kwargs)
        term.echo('  10. Quit the Docker application. Then return to this window and start Franklin the same way as you did before', **kwargs)
        term.echo()
        term.echo('  Press Enter now to close Franklin.')
        term.echo()
        term.echo('='*WRAP_WIDTH, fg='green')
        click.pause('')
        sys.exit(0)

#  start /w "" "Docker Desktop Installer.exe" uninstall
#  /Applications/Docker.app/Contents/MacOS/uninstall


def failsafe_start_docker_desktop() -> None:
    """
    Starts Docker Desktop if it is not running, attempting to handle any errors.
    """
    if not shutil.which('docker'):
         install_docker_desktop()    

    if not docker_desktop_status() == 'running':
        docker_desktop_start()
        term.dummy_progressbar(seconds=10, label='Starting Docker Desktop:')

    if not docker_desktop_status() == 'running':
        term.secho("Could not start Docker Desktop. Please start Docker Desktop manually.", fg='red')
        sys.exit(1)

    if utils.system() == 'Darwin':
        update_docker_desktop()


def docker_desktop_restart() -> None:
    """
    Restart Docker Desktop.
    """
    cmd = 'docker desktop restart'
    timeout=40    
    try:
        logger.debug(cmd)
        output = check_output(utils.fmt_cmd(cmd), timeout=timeout).decode()
    except TimeoutExpired as e:
        logger.debug(f"Timeout of {timeout} seconds exceeded.")
        return False
    except subprocess.CalledProcessError as e:        
        logger.debug(e.output.decode())
        raise click.Abort()    
    return True


def docker_desktop_start() -> None:
    """
    Start Docker Desktop.
    """    
    cmd = 'docker desktop start'
    timeout=40    
    try:
        logger.debug(cmd)
        output = check_output(utils.fmt_cmd(cmd), timeout=timeout).decode()
    except TimeoutExpired as e:
        logger.debug(f"Timeout of {timeout} seconds exceeded.")
        return False
    except subprocess.CalledProcessError as e:        
        logger.debug(e.output.decode())
        raise click.Abort()    
    return True


def docker_desktop_stop() -> None:
    """
    Stop Docker Desktop.
    """       
    # _command('docker desktop stop', silent=True)
    utils.run_cmd('docker desktop stop', check=False)


def docker_desktop_status() -> str:
    """
    Status of Docker Desktop.

    Returns
    -------
    :
        'running' if Docker Desktop is running.
    """

    # stdout = subprocess.run(utils._cmd('docker desktop status --format json'), 
    #                         check=False, stderr=DEVNULL, stdout=PIPE).stdout.decode()
    stdout = utils.run_cmd('docker desktop status --format json', check=False)
    if not stdout:
        return 'not running'
    data = json.loads(stdout)
    return data['Status']


def docker_desktop_version() -> Version:
    """
    Docker Desktop version.

    Returns
    -------
    :
        Docker Desktop version.
    """
    stdout = subprocess.check_output(utils.fmt_cmd('docker version --format json'))
    data = json.loads(stdout.decode())
    cmp = data['Server']['Components']
    vers = [c['Version'] for c in cmp if c['Name'] == 'Engine'][0]
    return Version(vers)

def get_latest_docker_version() -> Version:
    """
    Get most recent Docker Desktop version.

    Returns
    -------
    :
        Docker Desktop version.
    """
    # A bit of a hack: gets version as tag of base docker image (which is for use with "docker in docker")

    s = requests.Session()
    url = 'https://registry.hub.docker.com/v2/namespaces/library/repositories/docker/tags'
    tags = []
    r  = s.get(url, headers={ "Content-Type" : "application/json"})
    if not r.ok:
        r.raise_for_status()
    data = r.json()
    for entry in data['results']:
        if 'name' in entry:
            try:
                tags.append(Version(entry['name']))
            except InvalidVersion:
                # latest and other non-version tags
                pass
    return max(tags)


def update_docker_desktop() -> None:
    """
    Update Docker Desktop if a newer version is available.
    """
    if utils.system() == 'Windows':
        current_engine_version = docker_desktop_version()
        most_recent_version = get_latest_docker_version()
        if current_engine_version < most_recent_version:
            term.boxed_text(f"Update Docker Desktop",
                             [f'Please open the "Docker Desktop" application and and click where it says "New version available" in the bottom right corner.', 
                              'Then scroll down and click the blue button to update'],
                            prompt='Press Enter to close Franklin.', fg='red')
            sys.exit(0)
    else:
        # stdout = subprocess.check_output(utils.format_cmd('docker desktop update --check-only')).decode()
        stdout = utils.run_cmd('docker desktop update --check-only')
        if 'is already the latest version' not in stdout:
            # subprocess.run(utils.format_cmd('docker desktop update --quiet'))
            utils.run_cmd('docker desktop update --quiet')
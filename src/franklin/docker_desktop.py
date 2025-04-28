import sysconfig
import os
import re
from . import terminal as term
from . import utils
import sys
import requests
import click
import json
from . import config as cfg
from subprocess import check_output, DEVNULL, TimeoutExpired
from .logger import logger
import subprocess
import time
import shutil
from packaging.version import Version, InvalidVersion
import psutil
from pathlib import Path
from typing import Any


def get_user_config_file() -> str:
    """
    Returns the path to the user configuration file for Docker Desktop.
    """
    home = Path.home()
    if utils.system() == 'Darwin':
        json_settings = home / 'Library/Group Containers/group.com.docker/settings-store.json'
    elif utils.system() == 'Windows':
        json_settings = home / 'AppData/Roaming/Docker/settings-store.json'
    elif utils.system() == 'Linux':
        json_settings = home / '.docker/desktop/settings-store.json'
    return json_settings


def read_user_config() -> dict:
    """
    Reads the Docker Desktop configuration file and returns a dictionary with the settings.
    """
    json_settings = get_user_config_file()
    if not os.path.exists(json_settings):
        return dict()
    with open(json_settings, 'r') as f:
        settings = json.load(f)
    return settings


def write_user_config(settings: dict) -> None:
    """
    Writes the Docker Desktop configuration file with the settings.
    """
    json_settings = get_user_config_file()
    with open(json_settings, 'w') as f:
        json.dump(settings, f)


# class docker_config():
#     """
#     Contest manager for Docker Desktop settings.
#     """
#     def __init__(self):
#         home = Path.home()
#         if utils.system() == 'Darwin':
#             self.json_settings = home / 'Library/Group Containers/group.com.docker/settings-store.json'
#         elif utils.system() == 'Windows':
#             self.json_settings = home / 'AppData/Roaming/Docker/settings-store.json'
#         elif utils.system() == 'Linux':
#             self.json_settings = home / '.docker/desktop/settings-store.json'

#     def user_config_file(self):
#         if os.path.exists(self.json_settings):
#             return self.json_settings
#         return None

#     def __enter__(self):
#         if not os.path.exists(self.json_settings):
#             return dict()
#         with open(self.json_settings, 'r') as f:
#             self.settings = json.load(f)
#         return self

#     def __exit__(self, type, value, traceback):
#         with open(self.json_settings, 'w') as f:
#             json.dump(self.settings, f)


def config_get(variable: str=None) -> None:
    """
    Get Docker configuration for variable or all variables.

    Parameters
    ----------
    variable : 
        Variable name, by default None in which case all variables are shown.
    """
    if not get_user_config_file().parent.exists():
        term.echo('Docker installation not completed. No user configs.')
        return

    config = read_user_config()

    if variable:
        if variable not in cfg.docker_settings:
            term.echo(f'Variable "{variable}" not controlled by Franklin.')
            return
        if variable not in config:
            term.echo(f'Variable "{variable}" not set.')
            return
        term.echo(f'{variable}: {config[variable]}')
        return
    
    for variable in cfg.docker_settings:
        if variable in config:
            term.echo(f'{str(variable).rjust(31)}: {config[variable]}')

    write_user_config(config)




    # with docker_config() as config:
    #     if variable is not None:
    #         if variable not in cfg.docker_settings:
    #             term.echo(f'Variable "{variable}" cannot be accessed by Franklin.')
    #             return
    #         term.echo(f'{variable}: {config.settings[variable]}')
    #     else:
    #         for variable in cfg.docker_settings:
    #             if variable in config.settings:
    #                 term.echo(f'{str(variable).rjust(31)}: {config.settings[variable]}')


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
    if not get_user_config_file().parent.exists():
        term.echo('Docker installation not completed. No user configs.')
        return

    if variable not in cfg.docker_settings:
        term.echo(f'Variable "{variable}" cannot be set/changed by Franklin.')
        return
    
    config = read_user_config()

    if type(value) is str:
        value = utils.as_type(value)

    if variable == 'DiskSizeMiB':
        # for some reason Docker Desktop only accepts values in multiples of 1024
        value = int(value / 1024) * 1024

    logger.debug(f"Setting {variable} to {value}")
    config[variable] = value
    write_user_config(config)


def config_reset(variable: str=None) -> None:
    """
    Resets Docker configuration to defaults set by Franklin.

    Parameters
    ----------
    variable : 
        Variable name, by default None in which case all variables are reset.
    """
    if variable:
        config_set(variable, cfg.docker_settings[variable])
    else:
        config = read_user_config()
        for variable in cfg.docker_settings:
            if variable in config:
                logger.debug(f"Resetting {variable} to {cfg.docker_settings[variable]}")
                config[variable] = cfg.docker_settings[variable]
        write_user_config(config)


def config_fit():
    """Set resource limits to reasonable values given available resources.
    """

    config_reset()

    nr_cpu = psutil.cpu_count(logical=True)
    logger.debug(f"Fitting Cpus to {int(nr_cpu // 2)}")
    config_set('Cpus', int(nr_cpu // 2))

    svmem = psutil.virtual_memory()
    mem_mb = svmem.total // (1024 ** 2)
    logger.debug(f"Fitting MemoryMiB to {int(mem_mb * 0.7)}")
    config_set('MemoryMiB', int(mem_mb // 2))


def install_docker_desktop() -> None:
    """
    Downloads and installs Docker Desktop on Windows or Mac.
    """
    architecture = sysconfig.get_platform().split('-')[-1]
    assert architecture

    operating_system = utils.system()

    if operating_system == 'Darwin':
        if os.path.exists('/Applications/Docker.app'):
            term.echo('Docker Desktop is already installed. Try to open it and complete the setup procedure. Otherwise remove it and try again.')
            sys.exit(1)

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
        term.echo("Please install Docker Desktop manually by visiting https://docs.docker.com/get-started/get-docker")
        sys.exit(1)

    if (Path.home() / 'Downloads').exists():
        installer_dir = str(Path.home() / 'Downloads')
    elif (Path.home() / 'Overførsler').exists():
        installer_dir = str(Path.home() / 'Overførsler')
    else: 
        installer_dir = os.getcwd()

    installer_path = os.path.join(installer_dir, installer)

    if os.path.exists(installer_path):
        term.echo(f"An installer already exists at {installer_path}. Please remove it and run the command again.")
        sys.exit(1)


    with requests.get(download_url, stream=True) as response:
#        response = requests.get(download_url, stream=True)
        if not response.ok:
            term.echo(f"Could not download Docker Desktop. Please download from {download_url} and install before proceeding.")
            sys.exit(1)
        else:
            term.echo(f"Will download installer to {installer_path}")

        file_size = response.headers['Content-length']
        with open(installer_path, mode="wb") as file:
            nr_chunks = int(file_size) // (10 * 1024) + 1
            with click.progressbar(length=nr_chunks, label='Downloading:'.ljust(cfg.pg_ljust), **cfg.pg_options) as bar:
                for chunk in response.iter_content(chunk_size=10 * 1024):
                    file.write(chunk)
                    bar.update(1)

    # if the user already has a user config file, we temporarily set OpenUIOnStartupDisabled 
    # to False so that the user can see the Dashboard under the install procedure

    if utils.system() == 'Windows':
        click.launch(installer_path, wait=True)

        click.launch('/Applications/Docker.app')

    elif utils.system() == 'Darwin':
        term.echo('Installing:')
        try:
            output = utils.run_cmd(f'hdiutil detach /Volumes/Docker', check=False)
            output = utils.run_cmd(f'hdiutil attach -nobrowse -readonly {installer_path}')
            output = utils.run_cmd(f'cp -a /Volumes/Docker/Docker.app /Applications/')
            output = utils.run_cmd(f'hdiutil detach /Volumes/Docker/')
        except Exception as e:
            raise e
        finally:
            os.remove(installer_path)

        if get_user_config_file().parent.exists():
            config_reset()
            # config_set('OpenUIOnStartupDisabled', False)

        term.boxed_text(f"In Docker Desktop", 
                        ['Franklin will open Docker Desktop. You must then:',
                         '1. Accept the license agreement.',
                         "2. Complete the setup procedure (you can click anywhere it says 'skip').",
                         "3. Click bottom right corner to to update and click the blue button on the page that appears.",
                         '4. Quit the Docker Desktop application.',
                         '5. Come back here :)'
                        ],
                        prompt='Press Enter to continue.',
                        fg='blue', subsequent_indent='   ')
        
        # term.echo('Franklin will open Docker Desktop. You must:'
        #           '' so you can accept the license agreement. '
        #           'Once you have completed the setup, Quick Docker Desktop and setup. '
        #           'You can skip creating an account and the questionnaire. ')
        # click.pause('Press Enter to continue.')
        

        click.launch('/Applications/Docker.app', wait=True)


    if not shutil.which('docker'):
        term.secho("Docker Desktop installation failed or is incomplete. Please install Docker Desktop manually.", fg='red')
        sys.exit(1)

    if not docker_desktop_status() == 'running':
        docker_desktop_start()
        term.dummy_progressbar(seconds=10, label='Starting Docker Desktop:')

    if not docker_desktop_status() == 'running':
        term.secho("Docker Desktop is not running. Please install Docker Desktop manually.", fg='red')
        sys.exit(1)

    config_reset()

    if utils.system() == 'Darwin':
        update_docker_desktop()




#  start /w "" "Docker Desktop Installer.exe" uninstall
#  /Applications/Docker.app/Contents/MacOS/uninstall

def failsafe_start_docker_desktop() -> None:
    """
    Starts Docker Desktop if it is not running, attempting to handle any errors.
    """
    if not shutil.which('docker'):
         
        term.boxed_text(f"Franklin needs Docker Desktop", 
                        ['Franklin depends on a program called Docker Desktop that needs '
                        'to be installed on your computer. '
                        'You can download it from ',
                        'https://docs.docker.com/get-started/get-docker ',
                        'and follow the default installation procedure.',
                        # 'If you have a Mac you can use the command below to install it:',
                        # '',
                        # '  franklin docker install',
                        # '',
                        ],
                        fg='blue')
        sys.exit(1)

    config_set('OpenUIOnStartupDisabled', True)

    if not docker_desktop_status() == 'running':
        docker_desktop_start()
        term.dummy_progressbar(seconds=10, label='Starting Docker Desktop:')

    if not docker_desktop_status() == 'running':
        term.secho("Could not reach Docker Desktop. Please quit Docker Desktop manually.", fg='red')
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
        stdout = utils.run_cmd('docker desktop update --check-only')
        if 'is already the latest version' not in stdout:
            term.secho('Docker Desktop is updating, which may take a while. Do not interrupt the process. You may be prompted to allow Docker to update.', fg='red')
            utils.run_cmd('docker desktop update --quiet')
            term.dummy_progressbar(seconds=60, label='Docker Desktop is updating:')



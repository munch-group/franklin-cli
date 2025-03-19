import sysconfig
import os
import re
from . import terminal as term
from . import utils
import sys
import requests
import click
import json
from .config import WRAP_WIDTH, PG_OPTIONS
from subprocess import check_output, DEVNULL, TimeoutExpired
from .logger import logger
import subprocess
import time
import shutil
from packaging.version import Version, InvalidVersion


def install_docker_desktop():

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

    term.boxed_text(f"Franklin needs Docker Desktop", 
                     ['Franklin depends on a program called Docker Desktop and will download a Docker Desktop installer to your Downloads folder.'],
                     prompt='Press Enter to start the download...', 
                     fg='green')

    response = requests.get(download_url, stream=True)
    if not response.ok:
        term.echo(f"Could not download Docker Desktop. Please download from {download_url} and install before proceeding.")
        sys.exit(1)

    file_size = response.headers['Content-length']
    with open(installer, mode="wb") as file:
        nr_chunks = int(file_size) // (10 * 1024) + 1
        with click.progressbar(length=nr_chunks, label='Downloading:', **PG_OPTIONS) as bar:
            for chunk in response.iter_content(chunk_size=10 * 1024):
                file.write(chunk)
                bar.update(1)
    
    if utils.system() == 'Windows':

        kwargs = dict(subsequent_indent=5)
        term.echo()
        term.echo()
        term.secho(f"How to install Docker Desktop on Windows:", fg='green')
        term.secho('='*WRAP_WIDTH, fg='green')
        term.echo()
        term.echo("  Please follow this exact sequence of steps:")
        term.echo()
        term.echo('  1. Open the Downloads folder.', **kwargs)
        term.echo('  2. Double-click the "Docker Desktop Installer.exe" file.', **kwargs)
        term.echo('  3. Follow the default installation procedure.', **kwargs)
        term.echo('  4. When the installation is completed, open Docker Desktop.', **kwargs)
        term.echo('  5. Accept the Docker Desktop license agreement')
        term.echo('  6. When you are asked to log in or create an account, just click skip.', **kwargs)
        term.echo('  7. When you are asked to take a survey, just click skip.', **kwargs)
        term.echo('  8. Wait while it says "Starting the Docker Engine..."')
        term.echo('  9. If it says "New version available" in the bottom right corner, click that to update (scroll to find the blue button)"', **kwargs)
        term.echo('  10. Quit the Docker application.', **kwargs)
        term.echo('  11. Return to this window and start Franklin the same way as you did before.', **kwargs)
        term.echo()
        term.echo('  Press Enter now to close Franklin.')
        term.echo()
        term.echo('='*WRAP_WIDTH, fg='green')
        click.pause('')
        sys.exit(0)

        # subprocess.run(installer, check=True)

        # term.echo(" - Removing installer...")
        # os.remove(installer)

    elif utils.system() == 'Darwin':
        cmd = utils.fmt_cmd(f'hdiutil attach -nobrowse -readonly {installer}')
        output = check_output(cmd).decode().strip()

        # Extract the mounted volume name from the output
        mounted_volume_name = re.search(r'/Volumes/([^ ]*)', output.strip()).group(1)

        term.echo("Installing:")
        term.echo()
        term.secho('='*WRAP_WIDTH, fg='red')
        term.echo('  Press Enter and then drag the Docker application to the Applications folder.', fg='red')
        term.secho('='*WRAP_WIDTH, fg='red')
        term.echo()
        click.pause('Press Enter...')
        term.echo()
        term.secho('='*WRAP_WIDTH, fg='red')
        term.echo('  Did you drag the Docker application to the Applications folder? If so, press Press Enter to continue.', fg='red')
        term.secho('='*WRAP_WIDTH, fg='red')
        term.echo()
        click.pause('Press Enter...')

        check_output(utils.fmt_cmd(f'open /Volumes/{mounted_volume_name}')).decode().strip()

   

        term.echo(" - Copying to Applications...")
        with click.progressbar(length=100, label='Copying to Applications:', **PG_OPTIONS) as bar:
            prev_size = ''
            for _ in range(1000):
                cmd = f'du -s /Applications/Docker.app'
                logger.debug(cmd)
                cmd = cmd.split()
                cmd[0] = shutil.which(cmd[0])
                output = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=1, check=False).stdout.decode().strip()
                if output:
                    size = output.split()[0]
                    if size == prev_size:
                        break
                    bar.update(100*int(1 - (size - prev_size) / size))
                    prev_size = size
                time.sleep(5)

        term.dummy_progressbar(seconds=10, label='Validating Docker Desktop:')

        term.echo(" - Unmounting...")

        if os.path.exists('/Volumes/{mounted_volume_name}'):
            run(f'hdiutil detach /Volumes/{mounted_volume_name}/')

        term.echo(" - Removing installer...")
        os.remove(installer)

        kwargs = dict(subsequent_indent=5)
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
        term.echo('  8. Wait while it says "Starting the Docker Engine..."')
        term.echo('  9. If it says "New version available" in the bottom right corner, click that to update (scroll to find the blue button)"', **kwargs)
        term.echo('  10. Quit the Docker application.', **kwargs)
        term.echo('  11. Return to this window and start Franklin the same way as you did before.', **kwargs)
        term.echo()
        term.echo('  Press Enter now to close Franklin.')
        term.echo()
        term.echo('='*WRAP_WIDTH, fg='green')
        click.pause('')
        sys.exit(0)

#  start /w "" "Docker Desktop Installer.exe" uninstall
#  /Applications/Docker.app/Contents/MacOS/uninstall


def failsafe_start_docker_desktop():

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


def docker_desktop_restart():
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


def docker_desktop_start():
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


def docker_desktop_stop():
    # _command('docker desktop stop', silent=True)
    utils.run_cmd('docker desktop stop', check=False)


def docker_desktop_status():
    # stdout = subprocess.run(utils._cmd('docker desktop status --format json'), 
    #                         check=False, stderr=DEVNULL, stdout=PIPE).stdout.decode()
    stdout = utils.run_cmd('docker desktop status --format json', check=False)
    if not stdout:
        return 'not running'
    data = json.loads(stdout)
    return data['Status']


def docker_desktop_version(return_json=False):
    stdout = subprocess.check_output(utils.fmt_cmd('docker version --format json'))
    data = json.loads(stdout.decode())
    cmp = data['Server']['Components']
    vers = [c['Version'] for c in cmp if c['Name'] == 'Engine'][0]
    return Version(vers)

def get_latest_docker_version():

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


def update_docker_desktop(return_json=False):

    if utils.system() == 'Windows':
        current_engine_version = version()
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
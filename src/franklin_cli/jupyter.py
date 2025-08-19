import sys
import os
import re
import logging
import shlex
import time
import webbrowser
import subprocess
import click
import shutil
import time
from subprocess import Popen, PIPE, STDOUT
from typing import Optional
from .crash import crash_report
from .gitlab import select_image
from . import docker as _docker
from .logger import logger, LoggerWriter
from .desktop import config_fit
from . import terminal as term
from . import options
from . import system
from .utils import DelayedKeyboardInterrupt
from . import chrome

# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service as ChromeService
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import WebDriverException
# from webdriver_manager.chrome import ChromeDriverManager
# from selenium.common.exceptions import NoSuchWindowException
# from selenium.webdriver.chrome.options import Options


# def wait_for_chrome(token_url: str) -> None:
#     options = Options()
#     options.add_argument("--disable-infobars")  # suppresses the "Chrome is being controlled..." message
#     options.add_experimental_option("excludeSwitches", ["enable-automation"])
#     options.add_experimental_option("useAutomationExtension", False)

#     # Set up the WebDriver with the correct version of ChromeDriver
#     driver = webdriver.Chrome(
#         service=ChromeService(
#             ChromeDriverManager().install()
#             ),
#             options=options
#         )
#     # Open the Jupyter Notebook in the Chrome controlled by Selenium
#     driver.get(token_url)
#     driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
#         "source": """
#             Object.defineProperty(navigator, 'webdriver', {
#                 get: () => undefined
#             });
#         """
#     })
#     shutdown = False
#     try:
#         # Wait until the Jupyter main page loads
#         WebDriverWait(driver, 60).until(
#             # EC.presence_of_element_located((By.CLASS_NAME, "jp-Notebook"))
#             lambda d: shutdown or d.current_url and "lab/tree" in d.current_url       
#             )
#         # Polling loop to detect when the tab is closed
#         while True:
#             if len(driver.window_handles) == 0:
#                 break
#             time.sleep(1)

#     except NoSuchWindowException as e:
#         pass
#     finally:
#         # Close the browser if it's still open
#         try:
#             driver.quit()
#         except NoSuchWindowException:
#             pass


def launch_jupyter(image_url: str, cwd: Optional[str] = None) -> None:
    """
    Launch Jupyter notebook server in a Docker container with browser automation.

    This function provides a complete workflow for running Jupyter notebooks:
    1. Downloads/updates the Docker image
    2. Starts a container with the image
    3. Monitors container logs for the Jupyter server URL
    4. Opens Chrome browser and waits for user to close it
    5. Cleans up containers and Docker Desktop on exit

    Parameters
    ----------
    image_url : str
        The Docker image URL/name containing the Jupyter environment.
    cwd : Optional[str], default=None
        The working directory to navigate to in JupyterLab.
        If provided, appends '/lab/tree/{cwd}' to the Jupyter URL.

    Returns
    -------
    None
        This function manages the complete Jupyter session lifecycle.

    Examples
    --------
    >>> # Launch with default directory
    >>> launch_jupyter('jupyter/datascience-notebook')
    
    >>> # Launch in specific subdirectory
    >>> launch_jupyter('jupyter/datascience-notebook', cwd='exercises/week1')

    Notes
    -----
    - Uses failsafe container startup with automatic recovery
    - Monitors Docker logs to extract Jupyter server URL with token
    - Replaces container port with host-mapped port in URL
    - Uses Chrome browser automation for better user experience
    - Handles cleanup even on KeyboardInterrupt
    - Stops Docker Desktop after session ends
    - Redirects Chrome output to debug logging

    Warnings
    --------
    This function requires Chrome browser to be installed and will fail
    if Chrome is not available on the system.
    """
    term.secho()
    term.secho("Downloading/updating image:")
    _docker.pull(image_url)
    term.echo()    

    term.secho('Starting container')
    run_container_id, docker_run_p, port = \
        _docker.failsafe_run_container(image_url)

    cmd = f"docker logs --follow {run_container_id}"
    if system.system() == "Windows":
        popen_kwargs = dict(
            creationflags = subprocess.DETACHED_PROCESS \
                | subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        popen_kwargs = dict(start_new_session = True)
    docker_log_p = Popen(shlex.split(cmd), stdout=PIPE, stderr=STDOUT, 
                         bufsize=1, universal_newlines=True, **popen_kwargs)

    while True:
        time.sleep(0.1)
        line = docker_log_p.stdout.readline()
        if line:
            logger.debug('JUPYTER: '+line.strip())
        match= re.search(r'https?://127.0.0.1\S+', line)
        if match:
            token_url = match.group(0)
            # replace port in token_url
            token_url = re.sub(r'(?<=127.0.0.1:)\d+', port, token_url)
            docker_log_p.stdout.close()
            docker_log_p.terminate()
            docker_log_p.wait()
            break

    if cwd is not None:
        token_url = token_url.replace('/lab', f'/lab/tree/{cwd}')

    term.boxed_text(
        'Jupyter is running',
        [
            'JupyterLab lab will open in your the Chrome browser.',
            '',
            'To quit jupyter, close the Chrome browser window. '
            'Do NOT close this terminal window.',
            '',
            'If you have not installed the Chrome browser, please do so now.',
            'It is available at https://www.google.com/chrome/',
        ], fg='green')
    click.pause()

    term.echo('Launching Chrome browser') 
    term.echo()

    # term.secho(
    #     f'\nJupyter is running and will open in your the Chrome browser.')
    # term.secho(
    #     f'\nDo NOT close this window. Instead, close the browser tab '
    #     'when you are done with the exercise.', fg='green')

    # term.secho(
    #     f'\nThat will shutdown jupyter, docker, '
    #     'and franklin.', fg='green')
    # click.pause("press Enter to continue")

    from contextlib import redirect_stderr, redirect_stdout

    try:
        with redirect_stderr(LoggerWriter(logger.debug)):
            with redirect_stdout(LoggerWriter(logger.debug)):
                chrome.chrome_open_and_wait(token_url)

    except KeyboardInterrupt:
        pass
    finally:
        with DelayedKeyboardInterrupt():

            term.echo()
            term.echo()
            term.secho('Closing browser window.') 
            sys.stdout.flush()
            time.sleep(0.5)
            term.secho('Stopping Docker container') 
            sys.stdout.flush()
            time.sleep(0.5)
            _docker.kill_container(run_container_id)
            docker_run_p.terminate()
            docker_run_p.wait()
            term.secho('Stopping Docker Desktop') 
            sys.stdout.flush()
            _docker.desktop_stop()
            # term.echo()
            # term.secho('You can now safely close this window', fg='green')
            # term.echo()
            logging.shutdown()

    ##########################

    # webbrowser.open(token_url, new=1)

    # term.secho(
    #     f'\nJupyter is running and should open in your default browser.')
    # term.echo(f'If not, you can access it at this URL:')
    # term.secho(f'{token_url}', nowrap=True, fg='blue')

    # while True:
    #     term.secho('\nPress Q to shut down jupyter and close application', 
    #                fg='green')
    #     c = click.getchar()
    #     click.echo()
    #     if c.upper() == 'Q':

    #         term.secho('Shutting everything down') 
    #         term.echo()
    #         sys.stdout.flush()

    #         # term.secho('Shutting down container', fg='red') 
    #         # sys.stdout.flush()
    #         _docker.kill_container(run_container_id)
    #         docker_run_p.terminate()
    #         docker_run_p.wait()
    #         # term.secho('Shutting down Docker Desktop', fg='yellow') 
    #         # sys.stdout.flush()
    #         _docker.desktop_stop()
    #         # term.secho('Service has stopped.', fg='green')
    #         # term.echo()
    #         term.secho('Jupyter is no longer running and you can close '
    #                    'the tab in your browser.', fg='green')
    #         logging.shutdown()
    #         break


@options.subdirs_allowed
@click.command()
@crash_report
def jupyter(allow_subdirs_at_your_own_risk: bool) -> None:
    """
    Launch Jupyter notebook environment for Franklin exercises.

    This command provides a complete Jupyter development environment by:
    1. Validating the current directory structure
    2. Checking system requirements (internet, disk space, Docker)
    3. Presenting an interactive exercise selection interface
    4. Launching Jupyter in a containerized environment

    Parameters
    ----------
    allow_subdirs_at_your_own_risk : bool
        Flag to bypass subdirectory validation. When False (default),
        prevents running from directories containing subdirectories
        to avoid file conflicts and ensure clean exercise environment.

    Returns
    -------
    None
        This command manages the complete Jupyter session.

    Raises
    ------
    SystemExit
        If subdirectories are found and allow_subdirs_at_your_own_risk is False.

    Examples
    --------
    Run from clean directory:
    >>> franklin jupyter
    
    Override subdirectory check:
    >>> franklin jupyter --allow-subdirs-at-your-own-risk

    Notes
    -----
    - Enforces clean directory structure by default to prevent conflicts
    - Checks internet connectivity for image downloads
    - Validates available disk space before starting
    - Configures Docker Desktop settings automatically
    - Uses interactive exercise selection from GitLab registry
    - Provides detailed user guidance for setup issues

    Warnings
    --------
    Running from directories with subdirectories may cause file conflicts
    or unexpected behavior in the containerized environment.
    """
    if not allow_subdirs_at_your_own_risk:
        for x in os.listdir(os.getcwd()):
            if os.path.isdir(x) and not os.path.basename(x).startswith('.'):
                term.boxed_text(
                    'You have subfolders in your current directory',
                                [
        'Franklin must run from a folder with no other folders inside it.',
        '',
        'You can make an empty folder called "exercise" with this command:',
        '',
        '    mkdir exercise',
        '',
        'and change to that folder with this command:',
        '',                                    
        '    cd exercise',
        '',
        'Then run your franklin command.',
                                ], fg='blue')
                sys.exit(1)

    # Validate system requirements
    system.check_internet_connection()
    system.check_free_disk_space()

    # Configure Docker if available
    if shutil.which('docker'):
        config_fit()

    # Ensure Docker Desktop is running
    _docker.failsafe_start_desktop()
    time.sleep(2)

    # Interactive exercise selection and launch
    image_url = select_image()
    launch_jupyter(image_url)

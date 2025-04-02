import signal 
import shlex
import sys
import os
import re
import shutil
import click
import requests 
import time
from . import utils
from .logger import logger
from . import config as cfg
import subprocess
import platform
from functools import wraps
import webbrowser
import urllib
from importlib.metadata import version as _version
from . import terminal as term
from typing import Tuple, List, Dict, Callable, Any
from pathlib import Path
import shutil


def config_gitui() -> None:
    """
    Copies gitui config files to the user's config directory.
    """

    if utils.system() == 'Windows':
        path = os.path.join(os.getenv('APPDATA'), 'gitui')
    else:
        path = str(Path.home() / '.config/gitui')
        
    if not os.path.exists(path):
        os.makedirs(path)       
    for file in Path('data/gitui').glob('*'):
        print(f'Copying {file} to {path}')
        shutil.copy(file, path)


def as_type(s: str) -> Any:
    """
    Convert string to int, float or bool.

    Parameters
    ----------
    s : 
        String to be converted.

    Returns
    -------
    :
        Representation of the string as int, float or bool.
    """
    if s.lower() in ['true', 'false']:
        return s.lower() == 'true'
    try:
        return float(s)        
    except ValueError:
        try:
            return int(s)
        except ValueError:
            return s
        
###########################################################
# Click
###########################################################

class AliasedGroup(click.Group):
    """
    A click Group that allows for aliases of commands.
    """
    def get_command(self, ctx, cmd_name):
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv
        
        aliases = {
            'rm': 'remove',
            'ls': 'list',
            'up': 'update',
            'dl': 'download',
            'image': 'images',
            'container': 'containers',
        }            
        if cmd_name in aliases:
            return click.Group.get_command(self, ctx, aliases[cmd_name])

    def resolve_command(self, ctx, args):
        # always return the full command name
        _, cmd, args = super().resolve_command(ctx, args)
        return cmd.name, cmd, args


class PrefixAliasedGroup(click.Group):
    """
    A click Group that allows for prefix matching of commands.
    """
    def get_command(self, ctx, cmd_name):
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv

        # see if it is a prefix of a command
        matches = [x for x in self.list_commands(ctx)
                   if x.startswith(cmd_name)]
        matches
        if not matches:
            return None
        elif len(matches) == 1:
            return click.Group.get_command(self, ctx, matches[0])
        ctx.fail(f"Too many matches: {', '.join(sorted(matches))}")

    def resolve_command(self, ctx, args):
        # always return the full command name
        _, cmd, args = super().resolve_command(ctx, args)
        return cmd.name, cmd, args
    

###########################################################
# Keyboard interrupt handling
###########################################################

class DelayedKeyboardInterrupt:
    """
    Context manager to delay KeyboardInterrupt.
    """
    def __enter__(self):
        self.signal_received = False
        self.old_handler = signal.signal(signal.SIGINT, self.handler)
                
    def handler(self, sig, frame):
        self.signal_received = (sig, frame)
        # logging.debug('SIGINT received. Delaying KeyboardInterrupt.')
    
    def __exit__(self, type, value, traceback):
        signal.signal(signal.SIGINT, self.old_handler)
        if self.signal_received:
            self.old_handler(*self.signal_received)


class SuppressedKeyboardInterrupt:
    """
    Context manager to suppress KeyboardInterrupt
    """
    def __enter__(self):
        self.signal_received = False
        self.old_handler = signal.signal(signal.SIGINT, self.handler)
                
    def handler(self, sig, frame):
        self.signal_received = (sig, frame)
        # logging.debug('SIGINT received. Delaying KeyboardInterrupt.')
    
    def __exit__(self, type, value, traceback):
        signal.signal(signal.SIGINT, self.old_handler)


###########################################################
# Crash handling
###########################################################

class Crash(Exception):
    """
    Package dummy Exception raised when a crash is encountered.
    """
    pass

class UpdateCrash(Crash):
    """
    Package dummy Exception raised when a crash during update.
    """
    pass



def crash_email() -> None:
    """
    Open the email client with a prefilled email to the maintainer of Franklin.
    """

    preamble = ("This email is prefilled with information of the crash you can send to the maintainer of Franklin.").upper()

    info = f"Python: {sys.executable}\n"
    info += f'Version of franklin: {package_version('franklin')}\n'    
    info += f'Version of franklin-educator: {package_version('franklin-educator')}\n'
    for k, v in platform.uname()._asdict().items():
        info += f"{k}: {v}\n"
    info += f"Platform: {platform.platform()}\n"
    info += f"Machine: {platform.machine()}\n"
    info += f"Processor: {platform.processor()}\n"
    info += f"Python Version: {platform.python_version()}\n"
    info += f"Python Compiler: {platform.python_compiler()}\n"
    info += f"Python Build: {platform.python_build()}\n"
    info += f"Python Implementation: {platform.python_implementation()}\n"

    log = ''
    if not utils.system() == 'Windows':
        if os.path.exists('franklin.log'):
            with open('franklin.log', 'r') as f:
                log = f.read()

    subject = urllib.parse.quote("Franklin CRASH REPORT")
    body = urllib.parse.quote(f"{preamble}\n\n{info}\n{log}")
    webbrowser.open(f"mailto:?to={cfg.maintainer_email}&subject={subject}&body={body}", new=1)


def crash_report(func: Callable) -> Callable:
    """
    Decorator to handle crashes and open an email client with a prefilled email to the maintainer of Franklin.

    Parameters
    ----------
    func : 
        Function to decorate.

    Returns
    -------
    :
        Decorated function.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if os.environ.get('DEVEL', None):
            return func(*args, **kwargs)
        try:
            ret = func(*args, **kwargs)
        except KeyboardInterrupt:
            logger.exception('KeyboardInterrupt')
            raise
        except utils.UpdateCrash as e:
            logger.exception('Raised: UpdateCrash')
            for line in e.args:
                term.secho(line, fg='red')
            sys.exit(1)
        except utils.Crash as e:
            logger.exception('Raised: Crash')
            term.secho(f"Franklin encountered an unexpected problem.")
            term.secho(f"Your email client should open an email prefilled with relevant information you can send to the maintainer of Franklin")
            term.secho(f"If it does not please send the email to  {cfg.maintainer_email}", fg='red')
            if utils.system() == 'Windows':
                term.secho(f'Please attach the the "franklin.log" file located in your working directory.') 
            crash_email()
            if 'DEVEL' in os.environ:
                raise e
            else:
                term.secho(f"Franklin crashed, sorry!", fg='red')
                sys.exit(1)                
        except SystemExit as e:
            raise e
        except click.Abort as e:
            logger.exception('Raised: Abort')
            raise e
        except:
            logger.exception('CRASH')
            term.secho(f"Franklin encountered an unexpected problem.")
            term.secho(f"Your email client should open an email prefilled with relevant information you can send to the maintainer of Franklin")
            term.secho(f"If it does not please send the email to  {cfg.maintainer_email}", fg='red')
            if utils.system() == 'Windows':
                term.secho(f'Please attach the the "franklin.log" file located in your working directory.') 
            crash_email()
            raise
        return ret
    return wrapper


###########################################################
# Subprocesses
###########################################################

def fmt_cmd(cmd: str) -> List[str]:
    """
    Formats a command string into a list of arguments.

    Parameters
    ----------
    cmd : 
        Command string.

    Returns
    -------
    :
        List of arguments.
    """
    logger.debug(cmd)
    cmd = shlex.split(cmd)
    cmd[0] = shutil.which(cmd[0])
    return cmd


def run_cmd(cmd: str, check: bool=True, timeout: int=None) -> Any:
    """
    Runs a command.

    Parameters
    ----------
    cmd : 
        Command to run.
    check : 
        Whether to check for errors, by default True
    timeout : 
        Timeout in seconds, by default None

    Returns
    -------
    :
        The output of the command.
    """

    cmd = fmt_cmd(cmd)
    try:
        p = subprocess.run(cmd, check=check, 
                capture_output=True, timeout=timeout)
        output = p.stdout.decode()
    except subprocess.TimeoutExpired as e:
        logger.debug(f"Command timeout of {timeout} seconds exceeded.")
        raise e
    except subprocess.CalledProcessError as e:        
        logger.debug(e.output.decode())
        logger.exception('Command failed')
        raise Crash
    return output

###########################################################
# Checks
###########################################################

def package_version(pack) -> str:
    """
    Get the version of the locally installed franklin package.
    """
    try:
        return _version(pack)
    except:
        return None
    

def is_wsl(v: str = platform.uname().release) -> int:
    """
    Detects if Python is running in WSL
    """
    if v.endswith("-Microsoft"):
        return 1
    elif v.endswith("microsoft-standard-WSL2"):
        return 2
    return 0


def wsl_available() -> int:
    """
    Detect if Windows Subsystem for Linux is available from Windows
    """
    if os.name != "nt" or not shutil.which("wsl"):
        return False
    try:
        return is_wsl(
            subprocess.check_output(
                ["wsl", "uname", "-r"], text=True, timeout=15
            ).strip()
        )
    except subprocess.SubprocessError:
        return False


def system():
    """
    Determine the system the code is running on.

    Returns
    -------
    :
        System name. Either: 'Windows', 'WSL', 'WSL2', 'Linux', or 'Darwin'
    """
    plat = platform.system()
    if plat == 'Windows':
        wsl = is_wsl()
        if wsl == 0:
            return 'Windows'
        if wsl == 1:
            return 'WSL'
        if wsl == 2:
            return 'WSL2'
    return plat


###########################################################
# Resources
###########################################################

def jupyter_ports_in_use():
    """
    Get a list of ports in use by Jupyter servers.

    Returns
    -------
    :
        List of ports in use.
    """
        
    output = run_cmd('jupyter server list')
    occupied_ports = [int(x) for x in re.findall(r'(?<=->)\d+', output, re.MULTILINE)]
    occupied_ports = [int(x) for x in re.findall(r'(?<=localhost:)\d+', output, re.MULTILINE)]
    return occupied_ports


def check_internet_connection():
    """
    Check if there is an internet connection.

    Returns
    -------
    :
        True if there is an internet connection, False otherwise
    """
    try:
        request = requests.get("https://hub.docker.com/", timeout=10)    
        logger.debug("Internet connection OK.")
        return True
    except (requests.ConnectionError, requests.Timeout) as exception:
        term.secho("No internet connection. Please check your network.", fg='red')
        sys.exit(1)
        return False


def gb_free_disk():
    """
    Get the amount of free disk space in GB.

    Returns
    -------
    :
        Free disk space in GB.
    """
    return shutil.disk_usage('/').free / 1024**3


def check_free_disk_space():
    """
    Checks if there is enough free disk space to run Franklin, and exits if there is not.
    """

    gb_free = utils.gb_free_disk()
    if gb_free < cfg.required_gb_free_disk:
        term.secho(f"Not enough free disk space. Required: {cfg.required_gb_free_disk} GB, Available: {gb_free:.2f} GB", fg='red')
        sys.exit(1)
    elif gb_free < 2 * cfg.required_gb_free_disk:

        term.boxed_text('You are running low on disk space', [
            f'You are running low on disk space. Franklin needs {cfg.required_gb_free_disk} GB of free disk space to run and you only have {gb_free:.2f} GB left.',
            '',
            'You can use "franklin docker remove" to remove cached Docker content you no longer need. it automatically get downloaded if you should need it again',
            ], fg='magenta')        
        if click.confirm("Do you want to stop to free up space?", default=False):
            sys.exit(1)
    else:
        term.echo()
        term.echo(f"Franklin needs", nl=False)
        term.secho(f" {cfg.required_gb_free_disk:.1f} Gb", nl=False, bold=True)
        term.echo(f" of free disk space to run.")
        # fake progress bar to make the student aware that this check is important
        with click.progressbar(length=100, label='Checking disk space:'.ljust(cfg.pg_ljust), **cfg.pg_options) as bar:
            for i in range(100):
                time.sleep(0.01)
                bar.update(1)
        term.echo(f"Free disk space:", nl=False)
        term.secho(f" {gb_free:.1f} Gb", fg='green', bold=True)



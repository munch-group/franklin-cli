import signal 
import shlex
import sys
import os
import re
import shutil
import click
import requests 
import time
from .config import REQUIRED_GB_FREE_DISK
from . import utils
from .logger import logger
from .config import MAINTAINER_EMAIL, PG_OPTIONS
import subprocess
import platform
from functools import wraps
import webbrowser
import urllib
from importlib.metadata import version as _version
from . import terminal as term

###########################################################
# Click
###########################################################

class AliasedGroup(click.Group):
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
    def __init__(self, message, errors):            
        super().__init__(message)
            
        self.message = errors
        self.errors = errors


def crash_email():

    if os.environ.get('DEVEL', None):
        return

    preamble = ("This email is prefilled with information of the crash you can send to the maintainer of Franklin.").upper()


    info = f'Franklin version: {franklin_version()}\n'
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
    webbrowser.open(f"mailto:?to={MAINTAINER_EMAIL}&subject={subject}&body={body}", new=1)

# BROWSER=wslview

def crash_report(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            ret = func(*args, **kwargs)
        except KeyboardInterrupt:
            logger.exception('KeyboardInterrupt')
            raise
        except utils.Crash as e:
            logger.exception('Raised: Crash')
            term.secho(f"Franklin encountered an unexpected problem.")
            term.secho(f"Your email client should open an email prefilled with relevant information you can send to the maintainer of Franklin")
            term.secho(f"If it does not please send the email to  {MAINTAINER_EMAIL}", fg='red')
            if utils.system() == 'Windows':
                term.secho(f'Please attach the the "franklin.log" file located in your working directory.') 
            crash_email()
            raise
        except SystemExit:
            raise
        except click.Abort:
            logger.exception('Raised: Abort')
            raise        
        except:
            logger.exception('CRASH')
            term.secho(f"Franklin encountered an unexpected problem.")
            term.secho(f"Your email client should open an email prefilled with relevant information you can send to the maintainer of Franklin")
            term.secho(f"If it does not please send the email to  {MAINTAINER_EMAIL}", fg='red')
            if utils.system() == 'Windows':
                term.secho(f'Please attach the the "franklin.log" file located in your working directory.') 
            crash_email()
            raise 
        return ret
    return wrapper


###########################################################
# Subprocesses
###########################################################

def fmt_cmd(cmd):
    logger.debug(cmd)
    cmd = shlex.split(cmd)
    cmd[0] = shutil.which(cmd[0])
    return cmd


def run_cmd(cmd, check=True, capture_output=True, timeout=None):

    cmd = fmt_cmd(cmd)
    try:
        p = subprocess.run(cmd, check=check, 
                                capture_output=capture_output, timeout=timeout)
        output = p.stdout.decode()
    except subprocess.TimeoutExpired as e:
        logger.debug(f"Command timeout of {timeout} seconds exceeded.")
        return False
    except subprocess.CalledProcessError as e:        
        logger.debug(e.output.decode())
        logger.exception('Command failed')
        raise click.Abort()    
    return output

###########################################################
# Checks
###########################################################

def franklin_version():
    try:
        return _version('franklin')
    except:
        return None
    

def is_wsl(v: str = platform.uname().release) -> int:
    """
    detects if Python is running in WSL
    """
    if v.endswith("-Microsoft"):
        return 1
    elif v.endswith("microsoft-standard-WSL2"):
        return 2
    return 0


def wsl_available() -> int:
    """
    detect if Windows Subsystem for Linux is available from Windows
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
        
    output = run_cmd('jupyter server list')
    occupied_ports = [int(x) for x in re.findall(r'(?<=->)\d+', output, re.MULTILINE)]
    occupied_ports = [int(x) for x in re.findall(r'(?<=localhost:)\d+', output, re.MULTILINE)]
    return occupied_ports


def check_internet_connection():
    try:
        request = requests.get("https://hub.docker.com/", timeout=10)    
        logger.debug("Internet connection OK.")
        return True
    except (requests.ConnectionError, requests.Timeout) as exception:
        term.secho("No internet connection. Please check your network.", fg='red')
        sys.exit(1)
        return False


def gb_free_disk():
    return shutil.disk_usage('/').free / 1024**3


def check_free_disk_space():

    gb_free = utils.gb_free_disk()
    if gb_free < REQUIRED_GB_FREE_DISK:
        term.secho(f"Not enough free disk space. Required: {REQUIRED_GB_FREE_DISK} GB, Available: {gb_free:.2f} GB", fg='red')
        sys.exit(1)
    elif gb_free < 2 * REQUIRED_GB_FREE_DISK:
        click.clear()
        term.echo()
        term.echo()
        term.echo()
        term.echo()
        term.echo()
        term.secho('='*75, fg='red')
        term.echo()
        term.secho(f"  You are running low on disk space. Franklin needs {REQUIRED_GB_FREE_DISK} GB of free disk space to run and you only have {gb_free:.2f} GB left.", fg='red', bold=True, blink=True)
        term.echo()
        term.echo(f'  You can use "franklin docker remove" to remove cached Docker content you no longer need. it automatically get downloaded if you should need it again')
        term.echo()
        term.secho('='*75, fg='red')
        term.echo()
        click.pause()
        click.clear()
    else:
        term.echo()
        term.echo(f"Franklin needs", nl=False)
        term.secho(f" {REQUIRED_GB_FREE_DISK:.1f} Gb", nl=False, bold=True)
        term.echo(f" of free disk space to run.")
        # fake progress bar to make the student aware that this check is important
        with click.progressbar(length=100, label='Checking disk space:'.ljust(24), **PG_OPTIONS) as bar:
            for i in range(100):
                time.sleep(0.01)
                bar.update(1)
        term.echo(f"Free disk space:", nl=False)
        term.secho(f" {gb_free:.1f} Gb", fg='green', bold=True)



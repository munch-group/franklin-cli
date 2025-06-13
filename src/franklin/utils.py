import signal 
import shlex
import sys
import os
import re
import shutil
import click
import requests 
import stat
import shutil
import time
from . import utils
from .logger import logger
from . import config as cfg
from .crash import crash_report, Crash
import subprocess
from functools import wraps
from importlib.metadata import version as _version
from . import terminal as term
from typing import Tuple, List, Dict, Callable, Any
from pathlib import Path
import shutil

# from functools import wraps

# def decorator_with_arguments(verbose=False):
#     def decorator(func):
#         @wraps(func)
#         def wrapper(*args, **kwargs):

#             if verbose:
#                 click.echo(f"Running {func.__name__} with arguments: {args}, {kwargs}")

#             return func(*args, **kwargs)

#         return wrapper
#     return decorator

# @decorator_with_arguments(verbose=True)
# def foo(s):
#     print(s)

# foo('Hello, world!')

def rmtree(path: str) -> None:
    """
    shutil.rmtree with error handling.

    Parameters
    ----------
    path : 
        path to the directory to remove.
    """
    def on_rm_error(func, path, exc_info):
        os.chmod(path, stat.S_IWRITE) # make writable and retry
        func(path)
    shutil.rmtree(path, onexc=on_rm_error)


_banner = """
        ▗▄▄▄▖▗▄▄▖  ▗▄▖ ▗▖  ▗▖▗▖ ▗▖▗▖   ▗▄▄▄▖▗▖  ▗▖
        ▐▌   ▐▌ ▐▌▐▌ ▐▌▐▛▚▖▐▌▐▌▗▞▘▐▌     █  ▐▛▚▖▐▌
        ▐▛▀▀▘▐▛▀▚▖▐▛▀▜▌▐▌ ▝▜▌▐▛▚▖ ▐▌     █  ▐▌ ▝▜▌
        ▐▌   ▐▌ ▐▌▐▌ ▐▌▐▌  ▐▌▐▌ ▐▌▐▙▄▄▖▗▄█▄▖▐▌  ▐▌
"""


def show_banner():
    """
    Displays the Franklin banner.
    """
    click.clear()
    logger.debug('###################### FRANKLIN #######################')
    for line in _banner.splitlines():
        term.secho(line, nowrap=True, center=True, fg='green', log=False)
    term.echo()


def is_educator():
    cmd = f'ssh -T git@{cfg.gitlab_domain}'
    p = subprocess.run(utils.fmt_cmd(cmd), capture_output=True)
    if not p.returncode and p.stdout.decode().startswith('Welcome to GitLab'):
        return True
    return False


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


def run_cmd(cmd: str, check: bool=True, timeout: int=None, 
            stderr2stdout=False) -> Any:
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
    stderr2stdout : 
        Whether to redirect stderr to stdout, by default False

    Returns
    -------
    :
        The output of the command.
    """
    kwargs = {}
    if stderr2stdout:
        kwargs['stderr'] = subprocess.STDOUT
    cmd = fmt_cmd(cmd)
    try:
        p = subprocess.run(cmd, check=check, 
                capture_output=True, timeout=timeout, **kwargs)
        output = p.stdout.decode()
    except subprocess.TimeoutExpired as e:
        logger.debug(f"Command timeout of {timeout} seconds exceeded.")
        raise e
    except subprocess.CalledProcessError as e:        
        logger.debug(e.output.decode())
        logger.exception('Command failed')
        raise Crash
    return output

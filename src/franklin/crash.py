import os
import sys
import platform
import inspect
import webbrowser
import urllib.parse
import pyperclip
import requests
import json
import click
from functools import wraps
from subprocess import CalledProcessError
from importlib.metadata import packages_distributions

from .logger import logger
#from . import crash
from . import config as cfg
from .system import package_version
from . import terminal as term
from typing import Callable
from . import system


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


def gather_crash_info(include_log=True) -> str:
    """
    Gathers information about the system and the crash.
    """
    info = f"python: {sys.executable}\n"
    info += f'franklin: {package_version("franklin")}\n'    
    info += f'franklin-educator: {package_version("franklin-educator")}\n'
    for k, v in platform.uname()._asdict().items():
        info += f"{k}: {v}\n"
    info += f"platform: {platform.platform()}\n"
    info += f"machine: {platform.machine()}\n"
    info += f"processor: {platform.processor()}\n"
    info += f"python version: {platform.python_version()}\n"
    info += f"python compiler: {platform.python_compiler()}\n"
    info += f"python build: {platform.python_build()}\n"
    info += f"python implementation: {platform.python_implementation()}\n"

    if include_log:
        if os.path.exists('franklin.log'):
            with open('franklin.log', 'r') as f:
                log = f.read()
        info += f"\n\nFranklin log:\n{log}\n"

    return info


def crash_email() -> None:
    """
    Open the email client with a prefilled email to the maintainer of Franklin.
    """

    preamble = ("This email is prefilled with information of the crash you can"
    "send to the maintainer of Franklin.").upper()

    info = gather_crash_info(include_log=False)

    log = ''
    if not system.system() == 'Windows':
        if os.path.exists('franklin.log'):
            with open('franklin.log', 'r') as f:
                log = f.read()

    subject = urllib.parse.quote("Franklin CRASH REPORT")
    body = urllib.parse.quote(f"{preamble}\n\n{info}\n{log}")
    webbrowser.open(
        f"mailto:?to={cfg.maintainer_email}&subject={subject}&body={body}", 
        new=1)


def crash_report(func: Callable) -> Callable:
    """
    Decorator to handle crashes and open an email client with a prefilled email
    to the maintainer of Franklin.

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

        def create_github_issue_and_exit(title, body, repository):

            term.secho(
                f"\nFranklin crashed - sorry.", 
                fg='red')
            term.secho(
                '\nThe error hes been reported to the maintainers of Franklin '
                'and will be fixed in the next release. Once available, '
                'franklin will be updated automatically.'
            )
            url = cfg.github_issues_template_url.format(repository_name=repository)
            headers = {
                "Authorization": f"token {cfg.github_write_issue_token}",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json"
            }
            data = {
                "title": title,
                "body": body,
                "labels": ['bug']
            }
            response = requests.post(url, headers=headers, data=json.dumps(data))
            response.raise_for_status()  # Raises an HTTPError for bad responses        
            issue_data = response.json()
            sys.exit(1)


            pyperclip.copy(gather_crash_info())

        # def msg_and_exit():
        #     term.secho(
        #         f"\nFranklin encountered an unexpected problem.", fg='red')
        #     # term.secho(
        #     #     f'\nPlease open an email to {cfg.maintainer_email} with '
        #     #     'subject "Franklin crash". When you press Enter in this '
        #     #     'window, the crash information is copied to your clipboard '
        #     #     'So you can paste it into the email body before sending it')
        #     term.secho(
        #         f'\nPlease report this by submitting an issue on GitHub with '
        #         'a descriptive title and the error information pasted into '
        #         'the description field.')
        #     click.pause("Press Enter open issue page to copy the error information to your "
        #                 "clipboard.")

        #     frame = inspect.trace()[-1]
        #     module = inspect.getmodule(frame[0])
        #     package_name = 'franklin'
        #     if module is not None and  module.__name__.startswith('franklin_'):
        #         package_name = module.__name__.split('.')[0].replace('_', '-')

        #     # distributions = packages_distributions()
        #     # package = distributions.get(__name__.split('.')[0])[0]
        #     url = f'https://github.com/munch-group/{package_name}/issues'

        #     pyperclip.copy(gather_crash_info())

        #     webbrowser.open(url, new=1)

        #     sys.exit(1)   

        if os.environ.get('DEVEL', None):
            return func(*args, **kwargs)
        try:
            ret = func(*args, **kwargs)

        except KeyboardInterrupt as e:
            logger.exception('KeyboardInterrupt')
            if 'DEVEL' in os.environ:
                raise e
            raise click.Abort()
        
        except (CalledProcessError, Crash, UpdateCrash) as e:
            logger.exception(f'Raised: {e.__class__.__name__}')
            if 'DEVEL' in os.environ:
                raise e            
            for line in e.args:
                term.secho(line, fg='red')
            sys.exit(1)

        # except crash.UpdateCrash as e:
        #     logger.exception('Raised: UpdateCrash')
        #     for line in e.args:
        #         term.secho(line, fg='red')
        #     sys.exit(1)

        # except crash.Crash as e:
        #     logger.exception('Raised: Crash')
        #     if 'DEVEL' in os.environ:
        #         raise e
        #     for line in e.args:
        #         term.secho(line, fg='red')
        #     create_github_issue_and_exit()         

        except SystemExit as e:
            raise e

        except click.Abort as e:
            logger.exception('Raised: Abort')
            raise e

        except Exception as e:
            logger.exception('CRASH')
            # Gather crash info and create title
            crash_info = gather_crash_info()
            error_msg = str(e) if str(e) else "Unknown error"
            title = f"Crash: {error_msg[:100]}"  # Limit title length
            
            # Determine which repository based on module
            frame = inspect.trace()[-1]
            module = inspect.getmodule(frame[0])
            repository = 'franklin'
            if module is not None and module.__name__.startswith('franklin_'):
                repository = module.__name__.split('.')[0].replace('_', '-')
            
            create_github_issue_and_exit(title, crash_info, repository)

        return ret
    return wrapper

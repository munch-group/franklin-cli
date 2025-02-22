import signal 
import shlex
import sys
import shutil
import click
import requests 
from .config import REQUIRED_GB_FREE_DISK
from . import utils
from textwrap import wrap
from .logger import logger
from .config import ANACONDA_CHANNEL, MAINTAINER_EMAIL, WRAP_WIDTH
from subprocess import Popen, PIPE

class CleanupAndTerminate(Exception):
    pass


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


# def print_exercise_tree(exercise_dict, image_name):

#     print(exercise_list)
#     image_tree = defaultdict(lambda: defaultdict(str))
#     for course, exercise in exercise_dict:
#         # c, w, v = image_name.split('-')
#         # image_tree[c.replace('_', ' ')][w.replace('_', ' ')][v.replace('_', ' ')] = image_name
#         image_tree[course][exercise] = image_name


def format_cmd(cmd):
    cmd = shlex.split(cmd)
    cmd[0] = shutil.which(cmd[0]) 
    return cmd


def gb_free_disk():
    return shutil.disk_usage('/').free / 1024**3


def wrap(text):
    """
    Wraps text to fit terminal width or WRAP_WIDTH, whatever
    is smaller
    """
    nr_leading_nl = len(text) - len(text.lstrip('\n'))
    text = text.lstrip('\n')
    
    initial_indent = text[:len(text) - len(text.lstrip())]
    text = text.lstrip()
    
    trailing_ws = text[len(text.rstrip()):]   
    text = text.rstrip()

    text = click.wrap_text(text, width=max((shutil.get_terminal_size().columns)/2, WRAP_WIDTH), 
                initial_indent=initial_indent, subsequent_indent=initial_indent, 
                preserve_paragraphs=True)
    
    text = '\n' * nr_leading_nl + text + trailing_ws
    return text



def secho(text='', nowrap=False, **kwargs):
    """
    Wrapper for secho that wraps text.
    kwargs are passed to click.secho
    """
    if not nowrap:
        text = wrap(text)
    for line in text.strip().splitlines():
        logger.debug(line.strip())
    click.secho(text, **kwargs)


def echo(text='', nowrap=False, **kwargs):
    secho(text, nowrap=nowrap, **kwargs)


def update_client(update):
    if not update:
        logger.debug('Update check skipped')
    else:
        click.echo('Updating client...', nl=False)
        # cmd = f"{os.environ['CONDA_EXE']} update -y -c {ANACONDA_CHANNEL} --no-update-deps franklin"
        cmd = f"conda update -y -c {ANACONDA_CHANNEL} --no-update-deps franklin"
        logger.debug(cmd)
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        if stdout:
            [logger.debug(x) for x in stdout.decode().splitlines()]
        if stderr:
            [logger.debug(x) for x in stderr.decode().splitlines()]
        if p.returncode:
            logger.debug(f"Update failed with return code {p.returncode}")

            if stderr and 'PackageNotInstalledError' in stderr.decode():
                msg = f"""
                The package is not installed as a conda package in this environment.
                Please install the package with the following command:
                
                conda install -c {ANACONDA_CHANNEL} franklin
                """
                click.echo(msg)
            msg = f"""
            Could not update client. Please try again later.
            If problem persists, please email {MAINTAINER_EMAIL}
            with a screenshot of the error message.
            """
            click.echo(msg)
            sys.exit()
        click.echo('done.')


def _check_internet_connection():
    try:
        request = requests.get("https://hub.docker.com/", timeout=2)        
        return True
    except (requests.ConnectionError, requests.Timeout) as exception:
        utils.secho("No internet connection. Please check your network.", fg='red')
        sys.exit(1)
        return False


def _check_free_disk_space():

    gb_free = utils.gb_free_disk()
    if gb_free < REQUIRED_GB_FREE_DISK:
        utils.secho(f"Not enough free disk space. Required: {REQUIRED_GB_FREE_DISK} GB, Available: {gb_free:.2f} GB", fg='red')
        sys.exit(1)
    elif gb_free < 2 * REQUIRED_GB_FREE_DISK:
        click.clear()
        utils.echo()
        utils.echo()
        utils.echo()
        utils.echo()
        utils.echo()
        utils.secho('='*75, fg='red')
        utils.echo()
        utils.secho(f"  You are running low on disk space. Franklin needs {REQUIRED_GB_FREE_DISK} GB of free disk space to run and you only have {gb_free:.2f} GB left.", fg='red', bold=True, blink=True)
        utils.echo()
        utils.echo(f'  You can use "franklin docker remove" to remove cached Docker content you no longer need. it automatically get downloaded if you should need it again')
        utils.echo()
        utils.secho('='*75, fg='red')
        utils.echo()
        click.pause()
        click.clear()
    else:
        utils.echo(f"  Free space on disk: ", nl=False)
        utils.secho(f"{gb_free:.2f} GB", fg='green', bold=True)



class TroubleShooting():
    def __init__(self, color='red'):
        self.color = color

    def __enter__(self):
        logger.debug('START TROUBLESHOOTING')
        click.secho('Franklin is troubleshooting...', fg=self.color, nl=False)
        return self
    
    def __exit__(self, type, value, traceback):
        click.secho(' done.', fg=self.color)
        logger.debug('END TROUBLESHOOTING')

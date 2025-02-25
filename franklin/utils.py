import signal 
import shlex
import sys
import shutil
import click
import requests 
import time
from .config import REQUIRED_GB_FREE_DISK
from . import utils
from textwrap import wrap
import platform
from .logger import logger
from .config import ANACONDA_CHANNEL, MAINTAINER_EMAIL, WRAP_WIDTH, MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT, BOLD_TEXT_ON_WINDOWS, PG_OPTIONS
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


def _cmd(cmd, log=True, **kwargs):
    if log:
        logger.debug(cmd)
    cmd = cmd.split()
    cmd[0] = shutil.which(cmd[0])
    return cmd


def gb_free_disk():
    return shutil.disk_usage('/').free / 1024**3


def _check_window_size():

    def _box(text):
        window_box = \
            '|' + '-'*(MIN_WINDOW_WIDTH-2) + '|\n' + \
        ('|' + ' '*(MIN_WINDOW_WIDTH-2) + '|\n') * (MIN_WINDOW_HEIGHT-3) + \
            '| ' + text.ljust(MIN_WINDOW_WIDTH-3) + '|\n' + \
            '|' + '-'*(MIN_WINDOW_WIDTH-2) + '|' 
        return '\n'*150 + window_box


    ts = shutil.get_terminal_size()
    if ts.columns < MIN_WINDOW_WIDTH or ts.lines < MIN_WINDOW_HEIGHT:
        while True:
            ts = shutil.get_terminal_size()
            if ts.columns >= MIN_WINDOW_WIDTH and ts.lines >= MIN_WINDOW_HEIGHT:
                break
            click.secho(_box('Please resize the window to at least fit this square'), fg='red', bold=True)
            time.sleep(0.1)
        click.secho(_box('Thanks!'), fg='green', bold=True)
        click.pause()

    text = 'Please resize the window to at least fit this square'


def wrap(text, width=None):
    """
    Wraps text to fit terminal width or WRAP_WIDTH, whatever
    is smaller
    """
    if width is None:
        width = WRAP_WIDTH

    nr_leading_nl = len(text) - len(text.lstrip('\n'))
    text = text.lstrip('\n')
    
    initial_indent = text[:len(text) - len(text.lstrip())]
    text = text.lstrip()
    
    trailing_ws = text[len(text.rstrip()):]   
    text = text.rstrip()

    text = click.wrap_text(text, width=max((shutil.get_terminal_size().columns)/2, width), 
                initial_indent=initial_indent, subsequent_indent=initial_indent, 
                preserve_paragraphs=True)
    
    text = '\n' * nr_leading_nl + text + trailing_ws
    return text



def secho(text='', center=False, nowrap=False, **kwargs):
    """
    Wrapper for secho that wraps text.
    kwargs are passed to click.secho
    """
    if not nowrap:
        text = wrap(text)
    if center:
        cent = []
        for line in text.strip().splitlines():
            line = line.strip()
            if line:
                line = line.center(MIN_WINDOW_WIDTH)
            cent.append(line)
        text = '\n'.join(cent)        
    for line in text.strip().splitlines():
        try:
            logger.debug(line.strip())
        except UnicodeEncodeError:
            pass
    if platform.system() == 'Windows' and not BOLD_TEXT_ON_WINDOWS:
        kwargs['bold'] = False
    click.secho(text, **kwargs)


def echo(text='', nowrap=False, **kwargs):
    secho(text, nowrap=nowrap, **kwargs)


def _check_internet_connection():
    try:
        request = requests.get("https://hub.docker.com/", timeout=2)    
        logger.debug("Internet connection OK.")
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
        utils.echo(f"Franklin needs", nl=False)
        utils.secho(f" {REQUIRED_GB_FREE_DISK:.1f} Gb", nl=False, bold=True)
        utils.echo(f" of free disk space to run.")
        # fake progress bar to make the student aware that this check is important
        with click.progressbar(length=100, label='Checking disk space', **PG_OPTIONS) as bar:
            for i in range(100):
                time.sleep(0.01)
                bar.update(1)
        utils.echo(f"Free disk space:", nl=False)
        utils.secho(f" {gb_free:.1f} Gb", fg='green', bold=True)



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

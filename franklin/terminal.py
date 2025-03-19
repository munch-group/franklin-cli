import shutil
from .config import WRAP_WIDTH, PG_OPTIONS, MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT, BOLD_TEXT_ON_WINDOWS
import click
import time
from . import utils
from .logger import logger
from . import terminal as term

def check_window_size():

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


def dummy_progressbar(seconds, label='Hang on...', **kwargs):
    pg_options = PG_OPTIONS.copy()
    pg_options.update(kwargs)
    with click.progressbar(length=100, label=label, **pg_options) as bar:
        for i in range(100):
            time.sleep(seconds/100)
            bar.update(1)


def wrap(text, width=None, indent=True, initial_indent=None, subsequent_indent=None):
    """
    Wraps text to fit terminal width or WRAP_WIDTH, whatever
    is smaller
    """
    if width is None:
        width = WRAP_WIDTH

    nr_leading_nl = len(text) - len(text.lstrip('\n'))
    text = text.lstrip('\n')
    
    if initial_indent is None:
        initial_indent = text[:len(text) - len(text.lstrip())]
    text = text.lstrip()

    if subsequent_indent is None:
        subsequent_indent = initial_indent

    trailing_ws = text[len(text.rstrip()):]   
    text = text.rstrip()

    if not indent:
        initial_indent = ''
        subsequent_indent = ''
    print(text, width, initial_indent, subsequent_indent)
    text = click.wrap_text(text, width=max((shutil.get_terminal_size().columns)/2, width), 
                initial_indent=initial_indent, subsequent_indent=subsequent_indent, 
                preserve_paragraphs=True)
    
    text = '\n' * nr_leading_nl + text + trailing_ws
    return text


def secho(text='', width=None, center=False, nowrap=False, log=True,
          indent=True, initial_indent=None, subsequent_indent=None, **kwargs):
    """
    Wrapper for secho that wraps text.
    kwargs are passed to click.secho
    """
    if width is None:
        width = WRAP_WIDTH
    if not nowrap:
        text = wrap(text, width=width, 
                    indent=indent,
                    initial_indent=initial_indent, 
                    subsequent_indent=subsequent_indent)
    if center:
        cent = []
        for line in text.strip().splitlines():
            line = line.strip()
            if line:
                line = line.center(width)
            cent.append(line)
        text = '\n'.join(cent)        
    if log:
        for line in text.strip().splitlines():
            try:
                logger.debug(line.strip())
            except UnicodeEncodeError:
                line = str.decode('utf-8',errors='ignore')
                logger.debug(line.strip())
                

                pass
    if utils.system() == 'Windows' and not BOLD_TEXT_ON_WINDOWS:
        kwargs['bold'] = False
    click.secho(text, **kwargs)


def echo(text='', width=None, nowrap=False, log=True, indent=True, 
         initial_indent=None, subsequent_indent=None, **kwargs):
    
    secho(text, width=width, nowrap=nowrap, log=log, indent=indent, 
          initial_indent=initial_indent, subsequent_indent=subsequent_indent, **kwargs)


def boxed_text(header, lines=[], prompt='', **kwargs):
    term.echo()
    term.secho(f"{header}:", **kwargs)
    term.secho('='*WRAP_WIDTH, **kwargs)
    term.echo()
    for line in lines:
        term.echo(f"  {line}")
    term.echo()
    term.echo(f"  {prompt}")
    term.echo()
    term.secho('='*WRAP_WIDTH, **kwargs)
    term.echo()
    if prompt:
        click.pause('')


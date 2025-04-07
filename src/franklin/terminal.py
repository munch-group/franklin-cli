import shutil
from . import config as cfg
import click
import time
from . import utils
from .logger import logger
from . import terminal as term
from typing import Tuple, List, Dict, Callable, Any

def check_window_size() -> None:
    """
    Check if the window is at least cfg.min_window_width x cfg.min_window_height
    If not, prompt the user to resize the window.
    """

    def _box(text):
        window_box = \
            '|' + '-'*(cfg.min_window_width-2) + '|\n' + \
        ('|' + ' '*(cfg.min_window_width-2) + '|\n') * (cfg.min_window_height-3) + \
            '| ' + text.ljust(cfg.min_window_width-3) + '|\n' + \
            '|' + '-'*(cfg.min_window_width-2) + '|' 
        return '\n'*150 + window_box


    ts = shutil.get_terminal_size()
    if ts.columns < cfg.min_window_width or ts.lines < cfg.min_window_height:
        while True:
            ts = shutil.get_terminal_size()
            if ts.columns >= cfg.min_window_width and ts.lines >= cfg.min_window_height:
                break
            click.secho(_box('Please resize the window to at least fit this square'), fg='red', bold=True)
            time.sleep(0.1)
        click.secho(_box('Thanks!'), fg='green', bold=True)
        click.pause()

    text = 'Please resize the window to at least fit this square'


def dummy_progressbar(seconds: str, label: str='Hang on...', ljust=None, **kwargs: dict) -> None:
    """
    Dummy progressbar that waits for `seconds` seconds
    and displays a progressbar with `label`.

    Parameters
    ----------
    seconds : 
        Number of seconds to wait
    label :     
        Label for progressbar, by default 'Hang on...'
    """
    pg_options = cfg.pg_options.copy()
    if ljust is None:
        ljust = max(len(label), cfg.pg_ljust)
    pg_options.update(kwargs)
    with click.progressbar(length=100, label=label.ljust(ljust), **pg_options) as bar:
        for i in range(100):
            time.sleep(seconds/100)
            bar.update(1)


def wrap(text: str, width: int=None, indent: bool=True, initial_indent: str=None, subsequent_indent: str=None) -> str:
    """
    Wrap text to fit the terminal width.

    Parameters
    ----------
    text : 
        Text to wrap
    width : 
        Width of the terminal, by default None
    indent : 
        Whether to indent the text, by default True
    initial_indent : 
        String to prepend to the first line, by default None
    subsequent_indent : 
        String to prepend to subsequent lines, by default None

    Returns
    -------
    :
        Wrapped text.
    """
    if width is None:
        width = cfg.wrap_width

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

    text = click.wrap_text(text, width=max((shutil.get_terminal_size().columns)/2, width), 
                initial_indent=initial_indent, subsequent_indent=subsequent_indent, 
                preserve_paragraphs=True)
    
    text = '\n' * nr_leading_nl + text + trailing_ws
    return text


def secho(text: str='', width: int=None, center: bool=False, nowrap: bool=False, log: bool=True,
          indent: bool=True, initial_indent: str=None, subsequent_indent: str=None, **kwargs: dict) -> None:
    """
    Print text to the terminal with optional word wrapping and centering.

    Parameters
    ----------
    text : 
        Text to print, by default ''
    width : 
        Width of the terminal, by default None.
    center : 
        Whether to center the text, by default False.
    nowrap : 
        Whether to wrap the text, by default False
    log : 
        Whether to log the text, by
        default True
    indent : 
        Whether to indent the text, by default True
    initial_indent : 
        String to prepend to the first line, by
    subsequent_indent : 
        String to prepend to subsequent lines, by"
    """
    if width is None:
        width = cfg.wrap_width
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
    if utils.system() == 'Windows' and not cfg.bold_text_on_windows:
        kwargs['bold'] = False
    click.secho(text, **kwargs)


def echo(text: str='', width: int=None, nowrap: bool=False, log: bool=True, indent: bool=True, 
         initial_indent: str=None, subsequent_indent: str=None, **kwargs: dict) -> None:
    """
    Print text to the terminal with optional word wrapping.

    Parameters
    ----------
    text : 
        Text to print, by default ''
    width : 
        Width of the terminal, by default None
    nowrap : 
        Whether to wrap the text, by default False
    log : 
        Whether to log the text, by default True
    indent : 
        Whether to indent the text, by default True
    initial_indent : 
        String to prepend to the first line, by default None
    subsequent_indent : 
        String to prepend to subsequent lines, by default None
    """
    
    secho(text, width=width, nowrap=nowrap, log=log, indent=indent, 
          initial_indent=initial_indent, subsequent_indent=subsequent_indent, **kwargs)


def boxed_text(header: str, lines: list=[], prompt: str='', **kwargs: dict) -> None:
    """
    Print text between two horizontal lines.

    Parameters
    ----------
    header : 
        Header text over the box
    lines : 
        List text lines to print in box.
    prompt : 
        Prompt text at the bottom of the box.
    """
    term.echo()
    term.secho(f"{header}:", **kwargs)
    term.secho('='*cfg.wrap_width, **kwargs)
    term.echo()
    for line in lines:
        term.echo(f"  {line}", width=cfg.wrap_width)
    term.echo()
    if prompt:
        term.echo(f"  {prompt}")
        term.echo()
    term.secho('='*cfg.wrap_width, **kwargs)
    term.echo()
    if prompt:
        click.pause('')


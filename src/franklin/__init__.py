import click
# from pkg_resources import iter_entry_points
from importlib.metadata import entry_points
from click_plugins import with_plugins
from . import docker as _docker
from . import config as cfg
from . import update as _update
from . import gitlab as _gitlab
from . import terminal as term
from . import desktop
from . import config as cfg
from . import options
from . import jupyter as _jupyter
from .utils import AliasedGroup
from .crash import crash_report

# @with_plugins(iter_entry_points('franklin.plugins'))
@with_plugins(entry_points().select(group='franklin.plugins'))
@click.group(cls=AliasedGroup, 
             context_settings={"auto_envvar_prefix": "FRANKLIN"}, 
             epilog=f'See {cfg.documentation_url} for more details')
@click.version_option(package_name='franklin')
@options.update
@crash_report
def franklin(update: bool) -> None:
    """
    A tool to download notebook exercises and run jupyter 
    in a way that fits each exercise.    
    """
    print(update)
    term.check_window_size()
    # utils.show_banner()
    if update:
        _update.update_packages()
    desktop.ensure_docker_installed(lambda _: None)
    desktop.config_set('UseResourceSaver', False)

franklin.add_command(_update.update)

franklin.add_command(_jupyter.jupyter)

franklin.add_command(_docker.docker)

franklin.add_command(_gitlab.download)

franklin.add_command(_docker.cleanup)

franklin.add_command(_docker.show)


@click.group(hidden=True)
def press():
    ...        

@press.group()
def big():
    ...

@big.group()
def red():
    ...

@red.group()
def self():
    ...

@self.group()
def destruct():
    ...

@destruct.command()
def button():
    """A button command that does something."""
    import time
    click.echo("Self destruct will commence in ...")   
    for i in range(10, 0, -1):
        term.secho(f"\r{i} ", end='', fg='red', flush=True)
        time.sleep(1)


destruct.add_command(button)

import click
from pkg_resources import iter_entry_points
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


@with_plugins(iter_entry_points('franklin.plugins'))
@click.group(cls=AliasedGroup, context_settings={"auto_envvar_prefix": "FRANKLIN"}, epilog=f'See {cfg.documentation_url} for more details')
@click.version_option(package_name='franklin')
@options.update
def franklin(update: bool) -> None:
    """
    A tool to download notebook exercises and run jupyter in a way that fits each exercise.    
    """
    term.check_window_size()
    # utils.show_banner()
    if update:
        _update.update_client()
    desktop.ensure_docker_installed(lambda _: None)
    desktop.config_set('UseResourceSaver', False)

franklin.add_command(_update.update)

franklin.add_command(_jupyter.jupyter)

franklin.add_command(_docker.docker)

franklin.add_command(_gitlab.download)

franklin.add_command(_docker.cleanup)



@click.group(hidden=True)
def press():
    ...        

franklin.add_command(press)

@click.group()
def big():
    ...

press.add_command(big)

@click.group()
def red():
    ...

big.add_command(red)

@click.group()
def self():
    ...

red.add_command(self)

@click.group()
def destruct():
    ...

self.add_command(destruct)

@click.command()
def button():
    """A button command that does something."""
    click.echo("Button pressed!")   

destruct.add_command(button)

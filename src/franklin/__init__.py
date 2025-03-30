import click
from . import docker as _docker
from . import jupyter as _jupyter
from .utils import AliasedGroup
from .config import REQUIRED_GB_FREE_DISK
from . import howto as _howto
from . import update as _update
from . import gitlab as _gitlab
from . import terminal as term

from pkg_resources import iter_entry_points
from click_plugins import with_plugins

@with_plugins(iter_entry_points('franklin.plugins'))
@click.group(cls=AliasedGroup)
def franklin():
    """
    Franklin is a tool for running Jupyter servers predefined as Docker containers. 
    For more information relevant to students, instructors, and professors, see the
    online at https://munch-group.org/franklin.
    """

franklin.add_command(_update.update)
franklin.add_command(_docker.docker)
franklin.add_command(_jupyter.jupyter)
franklin.add_command(_howto.howto)

@with_plugins(iter_entry_points('franklin.exercise.plugins'))
@click.group()
def exercise():
    """Franklin exercises"""
    pass

@exercise.command('download')
def _download():
    """Download selected exercise from GitLab"""
    try:
        import franklin_educator
        term.boxed_text("Are you an educator?",
                        ['It seems you are an educator. If you intend upload to edit and '
                         'upload changes to an exercise, you must use "franklin git down" instead.'],
                        fg='red')
        click.confirm("Continue?", default=False, abort=True)
    except ImportError:
        pass
    _gitlab.download()


franklin.add_command(exercise)
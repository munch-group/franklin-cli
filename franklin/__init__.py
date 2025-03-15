import click
from . import docker as _docker
from . import jupyter as _jupyter
from . import utils
from .utils import AliasedGroup
import time
import sys
from .config import REQUIRED_GB_FREE_DISK
from . import update as _update
from . import tldr as _tldr
from . import gitlab as _gitlab

@click.group(cls=AliasedGroup)
def franklin():
    """
    Franklin is a tool for running Jupyter servers predefined as Docker containers. 
    For more information relevant to students, instructors, and professors, see the
    online at https://munch-group.org/franklin.
    """



# franklin.add_command(_update.update)


franklin.add_command(_jupyter.jupyter)
franklin.add_command(_docker.docker)
franklin.add_command(_tldr.tldr)
franklin.add_command(_gitlab.gitlab)


# @franklin.command()
# def rosalind():
#     click.echo_via_pager(utils.wrap(about))

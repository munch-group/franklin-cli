import click
from . import docker as _docker
from . import jupyter as _jupyter
from . import utils
import time
import sys
from .config import REQUIRED_GB_FREE_DISK

@click.group()
def franklin():
    """
    Bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla 
    bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla
    bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla
    bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla.

    \b
    Bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla 

    Bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla 
    bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla
    bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla
    bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla.    
    """



franklin.add_command(_jupyter.jupyter)
franklin.add_command(_docker.docker)
# franklin.add_command(_devel.devel)
# franklin.add_command(_about.about)


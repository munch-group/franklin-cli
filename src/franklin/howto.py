
import click
from . import utils
from .utils import crash_report
from . import terminal as term

from pkg_resources import iter_entry_points
from click_plugins import with_plugins

@with_plugins(iter_entry_points('franklin.howto.plugins'))
@click.group()
def howto():
    """How to ..."""
    pass

@howto.command()
@crash_report
def docker():
    """What is docker?"""

    term.echo()
    term.secho('Docker', fg='green', center=True, width=70)

    term.echo('''  \
lakdj alksdjf alksdjf lkas dlfkajs dlfajs dlfkaj sldkjf alsdkjf alskdjf lakjsd flalsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  akjs dflakjsd fasdlkf alskjdf alsdjkf asdf

alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la                
               ''', width=70)


@howto.command()
@crash_report
def image():
    """What is a docker image?"""

    term.echo()
    term.secho('Image', fg='green', center=True, width=70)

    term.echo('''  \
lakdj alksdjf alksdjf lkas dlfkajs dlfajs dlfkaj sldkjf alsdkjf alskdjf lakjsd flalsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  akjs dflakjsd fasdlkf alskjdf alsdjkf asdf

alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la                
               ''', width=70)


@howto.command()
@crash_report
def container():
    """What is a docker container?"""

    term.echo()
    term.secho('Container', fg='green', center=True, width=70)

    term.echo('''  \
lakdj alksdjf alksdjf lkas dlfkajs dlfajs dlfkaj sldkjf alsdkjf alskdjf lakjsd flalsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  akjs dflakjsd fasdlkf alskjdf alsdjkf asdf

alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la                
               ''', width=70)


@howto.command()
@crash_report
def terminal():
    """What is a terminal?"""

    term.echo()
    term.secho('Terminal', fg='green', center=True, width=70)

    term.echo('''  \
lakdj alksdjf alksdjf lkas dlfkajs dlfajs dlfkaj sldkjf alsdkjf alskdjf lakjsd flalsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  akjs dflakjsd fasdlkf alskjdf alsdjkf asdf

alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la                
               ''', width=70)


@howto.command()
@crash_report
def jupyter():
    """What is jupyter?"""

    term.echo()
    term.secho('Jupyter', fg='green', center=True, width=70)

    term.echo('''  \
lakdj alksdjf alksdjf lkas dlfkajs dlfajs dlfkaj sldkjf alsdkjf alskdjf lakjsd flalsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  akjs dflakjsd fasdlkf alskjdf alsdjkf asdf

alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la                
               ''', width=70)










    # click.echo_via_pager(
    # """\
    # alskd flakjs dlfkajs ldfkja sldkfj asldkfj                          
    # """)

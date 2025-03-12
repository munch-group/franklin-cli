
import click
from . import utils
from .utils import crash_report


@click.group()
def tldr():
    """TLDRs on concepts in Franklin"""
    pass

@tldr.command()
@crash_report
def docker():
    """What is docker?"""

    utils.echo()
    utils.secho('Docker', fg='green', center=True, width=70)

    utils.echo('''  \
lakdj alksdjf alksdjf lkas dlfkajs dlfajs dlfkaj sldkjf alsdkjf alskdjf lakjsd flalsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  akjs dflakjsd fasdlkf alskjdf alsdjkf asdf

alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la                
               ''', width=70)


@tldr.command()
@crash_report
def image():
    """What is a docker image?"""

    utils.echo()
    utils.secho('Image', fg='green', center=True, width=70)

    utils.echo('''  \
lakdj alksdjf alksdjf lkas dlfkajs dlfajs dlfkaj sldkjf alsdkjf alskdjf lakjsd flalsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  akjs dflakjsd fasdlkf alskjdf alsdjkf asdf

alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la                
               ''', width=70)



@tldr.command()
@crash_report
def container():
    """What is a docker container?"""

    utils.echo()
    utils.secho('Container', fg='green', center=True, width=70)

    utils.echo('''  \
lakdj alksdjf alksdjf lkas dlfkajs dlfajs dlfkaj sldkjf alsdkjf alskdjf lakjsd flalsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  akjs dflakjsd fasdlkf alskjdf alsdjkf asdf

alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la                
               ''', width=70)



@tldr.command()
@crash_report
def terminal():
    """What is a terminal?"""

    utils.echo()
    utils.secho('Terminal', fg='green', center=True, width=70)

    utils.echo('''  \
lakdj alksdjf alksdjf lkas dlfkajs dlfajs dlfkaj sldkjf alsdkjf alskdjf lakjsd flalsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  akjs dflakjsd fasdlkf alskjdf alsdjkf asdf

alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la                
               ''', width=70)




@tldr.command()
@crash_report
def server():
    """What is a server?"""

    utils.echo()
    utils.secho('Server', fg='green', center=True, width=70)

    utils.echo('''  \
lakdj alksdjf alksdjf lkas dlfkajs dlfajs dlfkaj sldkjf alsdkjf alskdjf lakjsd flalsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  akjs dflakjsd fasdlkf alskjdf alsdjkf asdf

alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la                
               ''', width=70)



@tldr.command()
@crash_report
def jupyter():
    """What is jupyter?"""

    utils.echo()
    utils.secho('Jupyter', fg='green', center=True, width=70)

    utils.echo('''  \
lakdj alksdjf alksdjf lkas dlfkajs dlfajs dlfkaj sldkjf alsdkjf alskdjf lakjsd flalsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  akjs dflakjsd fasdlkf alskjdf alsdjkf asdf

alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la  alsk fjlajs dflkjas dlfjas dlfkjas dflajsdf asldkfja sldfj alsfjk alskdjf la                
               ''', width=70)










    # click.echo_via_pager(
    # """\
    # alskd flakjs dlfkajs ldfkja sldkfj asldkfj                          
    # """)

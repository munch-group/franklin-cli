import signal 
import shlex
import sys
import shutil
import click
from textwrap import wrap
from .logger import logger
from .config import ANACONDA_CHANNEL, MAINTAINER_EMAIL
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

def format_cmd(cmd):
    cmd = shlex.split(cmd)
    cmd[0] = shutil.which(cmd[0]) 
    return cmd

def wrap_text(text):
    return "\n".join(wrap(' '.join(text.split()), 80))    

def update_client(update):
    if not update:
        logger.debug('Update check skipped')
    else:
        click.echo('Updating client...', nl=False)
        # cmd = f"{os.environ['CONDA_EXE']} update -y -c {ANACONDA_CHANNEL} --no-update-deps franklin"
        cmd = f"conda update -y -c {ANACONDA_CHANNEL} --no-update-deps franklin"
        logger.debug(cmd)
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        if stdout:
            [logger.debug(x) for x in stdout.decode().splitlines()]
        if stderr:
            [logger.debug(x) for x in stderr.decode().splitlines()]
        if p.returncode:
            logger.debug(f"Update failed with return code {p.returncode}")

            if stderr and 'PackageNotInstalledError' in stderr.decode():
                msg = f"""
                The package is not installed as a conda package in this environment.
                Please install the package with the following command:
                
                conda install -c {ANACONDA_CHANNEL} franklin
                """
                click.echo(msg)
            msg = f"""
            Could not update client. Please try again later.
            If problem persists, please email {MAINTAINER_EMAIL}
            with a screenshot of the error message.
            """
            click.echo(msg)
            sys.exit()
        click.echo('done.')

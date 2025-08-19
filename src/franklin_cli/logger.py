import sys
import logging
from importlib.metadata import version
ver = version(__package__)

logger = logging.getLogger(__name__)
formatter = logging.Formatter(
    fmt=f'%(asctime)s v{ver} - %(levelname)s: %(message)s', 
    datefmt= "%y-%m-%d-%H:%M:%S")
handler = logging.FileHandler(filename=f'{__package__}.log')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

# logger.debug('This is a debug message')
# logger.info('This is an info message')
# logger.warning('This is a warning message')
# logger.error('This is an error message')
# logger.critical('This is a critical message')

class LoggerWriter:
    def __init__(self, level):
        # self.level is really like using log.debug(message)
        # at least in my case
        self.level = level

    def write(self, message):
        # if statement reduces the amount of newlines that are
        # printed to the logger
        if message != '\n':
            self.level(message)

    def flush(self):
        # create a flush method so things can be flushed when
        # the system wants to. Not sure if simply 'printing'
        # sys.stderr is the correct way to do it, but it seemed
        # to work properly for me.
        self.level(sys.stderr)
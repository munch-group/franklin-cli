import logging
from importlib.metadata import version
ver = version(__package__)

logger = logging.getLogger(__name__)
formatter = logging.Formatter(fmt=f'%(asctime)s v{ver} - %(levelname)s: %(message)s', datefmt= "%y-%m-%d-%H:%M:%S")
handler = logging.FileHandler(filename=f'{__package__}.log')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

# logger.debug('This is a debug message')
# logger.info('This is an info message')
# logger.warning('This is a warning message')
# logger.error('This is an error message')
# logger.critical('This is a critical message')
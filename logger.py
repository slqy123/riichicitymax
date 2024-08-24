import logging
import sys
from colorlog import ColoredFormatter

logger = logging.getLogger('riichi')

logger.setLevel(logging.DEBUG)

formatter = ColoredFormatter(
    "%(asctime)s - %(log_color)s%(levelname)s%(reset)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    reset=True,
)

handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(formatter)
handler.setLevel(logging.DEBUG)

logger.addHandler(handler)

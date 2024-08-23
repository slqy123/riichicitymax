import logging
from colorlog import ColoredFormatter

logger = logging.getLogger('riichi')

logger.setLevel(logging.DEBUG)

formatter = ColoredFormatter(
    "%(asctime)s - %(log_color)s%(levelname)s%(reset)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    reset=True,
)

handler = logging.StreamHandler()
handler.setFormatter(formatter)
handler.setLevel(logging.DEBUG)

logger.addHandler(handler)

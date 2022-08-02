from pathlib import Path

from loko_orchestrator.config.app_config import fsdao
from loko_orchestrator.utils.logger_utils import logger


def content_reader(path, binary=False):
    if binary:
        logger.debug("reading binary file: %s" % path)
        with fsdao.get(Path(path), "rb") as f:
            return f.read()
    else:
        logger.debug("reading file:  %s" % path)
        with fsdao.get(Path(path), "r") as f:
            return f.read()

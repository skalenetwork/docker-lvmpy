#   -*- coding: utf-8 -*-
#
#   This file is part of docker-lvmpy
#
#   Copyright (C) 2019-Present SKALE Labs
#
#   docker-lvmpy is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   docker-lvmpy is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with docker-lvmpy.  If not, see <https://www.gnu.org/licenses/>

import logging
import os
from logging import StreamHandler, Formatter
from logging.handlers import RotatingFileHandler

from .config import (
    LOG_BACKUP_COUNT,
    LOG_DIR,
    LOG_FILE_SIZE_BYTES,
    LOG_FORMAT,
    LOG_PATH
)


def init_logging():
    ensure_log_dir()
    configure_logging()


def ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def configure_logger(logger):
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handlers = [
        StreamHandler(),
        RotatingFileHandler(
            LOG_PATH, maxBytes=LOG_FILE_SIZE_BYTES,
            backupCount=LOG_BACKUP_COUNT
        )
    ]
    for handler in handlers:
        handler.setFormatter(Formatter(LOG_FORMAT))
        logger.addHandler(handler)


def configure_logging():
    lvmpy_logger = logging.getLogger('.'.join(__name__.split('.')[:-1]))
    werkzeug_logger = logging.getLogger('werkzeug')
    urllib3_logger = logging.getLogger('urllib3')

    loggers = [lvmpy_logger, werkzeug_logger, urllib3_logger]
    for logger in loggers:
        configure_logger(logger)

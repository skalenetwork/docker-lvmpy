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

import os


MOUNTPOINT_BASE = '/mnt/'
PHYSICAL_VOLUME = os.getenv('PHYSICAL_VOLUME')
VOLUME_GROUP = os.getenv('VOLUME_GROUP')

FILESTORAGE_MAPPING = os.getenv('FILESTORAGE_MAPPING')

LOG_PATH = '/var/log/docker-lvmpy/lvmpy.log'
LOG_FILE_SIZE_MB = 100
LOG_FILE_SIZE_BYTES = LOG_FILE_SIZE_MB * 1000001
LOG_BACKUP_COUNT = 3
LOG_FORMAT = '[%(asctime)s %(levelname)s] %(name)s:%(lineno)d - %(threadName)s - %(message)s'  # noqa

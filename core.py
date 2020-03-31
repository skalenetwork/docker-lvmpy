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
import subprocess
import time
from functools import partial
from threading import Lock

from config import MOUNTPOINT_BASE, PHYSICAL_VOLUME, VOLUME_GROUP

logger = logging.getLogger(__name__)


LOGICAL_DEVICE_PREFIX = '/dev/mapper/{}-{}'
UNMOUNT_RETRIES_NUMBER = 5
TIMEOUT = 2


class LvmPyError(Exception):
    pass


volume_lock = Lock()

subprocess.run = partial(subprocess.run, stderr=subprocess.PIPE,
                         stdout=subprocess.PIPE)


def run_cmd(cmd, retries=1):
    res = None
    for retry in range(retries):
        logger.info(f'Command {" ".join(cmd)} try {retry}')
        res = subprocess.run(cmd)
        if res.returncode == 0:
            return res.stdout.decode('utf-8')
        else:
            stderr = res.stderr.decode('utf-8')
            cmd_line = ' '.join(cmd)
            logger.error(f'Command {cmd_line} try {retry} failed with {stderr}')
            time.sleep(TIMEOUT)
    raise LvmPyError(f'Command {cmd_line} failed after {retries} tries')


def volume_mountpoint(volume):
    return os.path.join(MOUNTPOINT_BASE, f'{VOLUME_GROUP}-{volume}')


def volume_device(volume):
    # lvm swaps all dashes to en dashes in block device name
    block_device_name = volume.replace('-', '--')
    return LOGICAL_DEVICE_PREFIX.format(VOLUME_GROUP, block_device_name)


def lsblk_device(volume):
    # lvm swaps all dashes to en dashes in block device name
    block_device_name = volume.replace('-', '--')
    return f'{VOLUME_GROUP}-{block_device_name}'


def physical_volumes():
    stdout = run_cmd(['pvs', '-o', 'name'])
    pvs = list(filter(
        None,
        map(lambda x: x.strip(), stdout.split('\n'))
    ))[1:]
    return pvs


def ensure_physical_volume(physical_volume=PHYSICAL_VOLUME):
    pvs = physical_volumes()
    if physical_volume in pvs:
        logger.warning(f'Physical volume {physical_volume} already created')
        return

    with volume_lock:
        run_cmd(['pvcreate', physical_volume, '-y'])


def volume_groups():
    res = subprocess.run(['vgs', '-o', 'name'])
    if res.returncode != 0:
        stderr = res.stderr.decode('utf-8')
        logger.error(f'Getting volume groups list failed {stderr}')
        raise LvmPyError('Getting volume groups list failed')

    stdout = res.stdout.decode('utf-8')
    vgs = list(filter(
        None,
        map(lambda x: x.strip(), stdout.split('\n'))
    ))[1:]
    return vgs


def ensure_volume_group(name=VOLUME_GROUP, physical_volume=PHYSICAL_VOLUME):
    vgs = volume_groups()
    if name in vgs:
        logger.warning(f'Volume group {name} already created')
        return

    with volume_lock:
        run_cmd(['vgcreate', name, physical_volume])


def create(name, size):
    logger.info(f'Creating volume with size {size}')
    with volume_lock:
        run_cmd(['lvcreate', '-L', f'{size}B', '-n', name, VOLUME_GROUP])
        res = subprocess.run(['mkfs.btrfs', '-f', volume_device(name)])
        if res.returncode != 0:
            stderr = res.stderr.decode('utf-8')
            cmd_line = ' '.join(res.args)
            logger.error(f'Command {cmd_line} failed with {stderr}')

            # Remove
            mountpoint = volume_mountpoint(name)
            if os.path.ismount(mountpoint):
                run_cmd(['umount', volume_device(name)])
            run_cmd(['lvremove', '-f', volume_device(name)])

            raise LvmPyError(f'Command {cmd_line} failed')


def remove(name):
    mountpoint = volume_mountpoint(name)
    if os.path.ismount(mountpoint):
        unmount(name)
    with volume_lock:
        run_cmd(['lvremove', '-f', volume_device(name)])


def mount(name):
    logger.info(f'Mounting volume {name}')
    mountpoint = volume_mountpoint(name)
    if os.path.ismount(mountpoint):
        logger.warning(f'Volume {name} is already mounted on {mountpoint}')
        unmount(name)
    if not os.path.exists(mountpoint):
        with volume_lock:
            run_cmd(['mkdir', mountpoint])

    with volume_lock:
        run_cmd(['mount', volume_device(name), mountpoint])
    return mountpoint


def unmount(name):
    with volume_lock:
        run_cmd(['umount', volume_device(name)], retries=UNMOUNT_RETRIES_NUMBER)


def path(name):
    stdout = run_cmd(['findmnt', volume_device(name), '--output', 'source'])
    if not stdout:
        return None

    mountpoint = list(filter(None, stdout.split('\n')))[1]
    return mountpoint


def volumes():
    stdout = run_cmd(['lvs', '-o', 'name', '-S', f'vg_name={VOLUME_GROUP}'])
    lvs = list(filter(
        None,
        map(lambda x: x.strip(), stdout.split('\n'))
    ))[1:]
    return lvs


def get(name):
    lvs = volumes()
    if name not in lvs:
        return None
    return name

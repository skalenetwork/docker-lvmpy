#   -*- coding: utf-8 -*-
#
#   This file is part of SKALE.py
#
#   Copyright (C) 2019-Present SKALE Labs
#
#   SKALE.py is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   SKALE.py is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with SKALE.py.  If not, see <https://www.gnu.org/licenses/>.

import logging
import os
import subprocess

from functools import partial

from config import MOUNTPOINT_BASE, PHYSICAL_VOLUME, VOLUME_GROUP

logger = logging.getLogger(__name__)


LOGICAL_DEVICE_PREFIX = '/dev/mapper/{}-{}'


class LvmPyError(Exception):
    pass


# TODO: refactor to remove redundant boilerplate related to exception handling
subprocess.run = partial(subprocess.run, stderr=subprocess.PIPE,
                         stdout=subprocess.PIPE)


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
    res = subprocess.run(['pvs', '-o', 'name'])
    if res.returncode != 0:
        stderr = res.stderr.decode('utf-8')
        logger.error(f'Getting physiscal volumes list failed {stderr}')
        raise LvmPyError('Getting physiscal volumes list failed')

    stdout = res.stdout.decode('utf-8')
    pvs = list(filter(
        None,
        map(lambda x: x.strip(), stdout.split('\n'))
    ))[1:]
    return pvs


def ensure_physical_volume(block_device=PHYSICAL_VOLUME):
    pvs = physical_volumes()
    if block_device in pvs:
        logger.warning(f'Physical volume {block_device} already created')
        return

    res = subprocess.run(['pvcreate', block_device, '-y'])
    if res.returncode != 0:
        stderr = res.stderr.decode('utf-8')
        logger.error(f'Physical volume creation failed with {stderr}')
        raise LvmPyError('Phisical volume creation failed')


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

    res = subprocess.run('vgcreate', name, physical_volume)
    if res.returncode != 0:
        stderr = res.stderr.decode('utf-8')
        logger.error(f'Creating volume group {name} failed with {stderr}')
        raise LvmPyError('Volume group Creation failed')


def create(name, size):
    logger.info(f'Creatig volume with size {size}')
    res = subprocess.run(['lvcreate', '-L', f'{size}K',
                          '-n', name, VOLUME_GROUP])
    if res.returncode != 0:
        stderr = res.stderr.decode('utf-8')
        logger.error(f'Creating {name} failed with {stderr}')
        raise LvmPyError('Volume creation failed')

    res = subprocess.run(['mkfs.btrfs', '-f', volume_device(name)])
    if res.returncode != 0:
        stderr = res.stderr.decode('utf-8')
        logger.error(f'Formating {name} as btrfs failed with {stderr}')
        remove(name)
        raise LvmPyError('Formating failed')


def remove(name):
    res = subprocess.run(['lvremove', '-f', volume_device(name)])
    if res.returncode != 0:
        stderr = res.stderr.decode('utf-8')
        logger.error(f'Removing {name} failed with {stderr}')
        raise LvmPyError('Removing failed')


def mount(name):
    mountpoint = volume_mountpoint(name)
    if not os.path.exists(mountpoint):
        res = subprocess.run(['mkdir', mountpoint])
        if res.returncode != 0:
            stderr = res.stderr.decode('utf-8')
            logger.error(f'Mountpoint creation for {name} '
                         f'failed with {stderr}')
            raise LvmPyError('Mountpoint creation failed')

    res = subprocess.run([
        'mount', volume_device(name), mountpoint],
        stdout=subprocess.PIPE
    )
    if res.returncode != 0:
        stderr = res.stderr.decode('utf-8')
        logger.error(f'Mounting {name} failed with {stderr}')
        raise LvmPyError('Mounting failed')
    return mountpoint


def unmount(name):
    res = subprocess.run(['umount', volume_device(name)])
    if res.returncode != 0:
        stderr = res.stderr.decode('utf-8')
        logger.error(f'Unmounting {name} failed with {stderr}')
        raise LvmPyError('Unmounting failed')


def path(name):
    res = subprocess.run(['findmnt', volume_device(name),
                          '--output', 'source'])
    if res.returncode != 0:
        stderr = res.stdout.decode('utf-8')
        logger.error(f'Getting mountpoint for {name} failed with {stderr}')
        raise LvmPyError('Getting mountpoint for volume failed')

    stdout = res.stdout.decode('utf-8')
    if not stdout:
        return None

    mountpoint = list(filter(None, stdout.split('\n')))[1]
    return mountpoint


def volumes():
    res = subprocess.run(['lvs', '-o', 'name',
                          '-S', f'vg_name={VOLUME_GROUP}'])
    if res.returncode != 0:
        stderr = res.stdout.decode('utf-8')
        logger.error(f'Getting volumes list failed with {stderr}')
        raise LvmPyError('Getting volumes list failed')

    stdout = res.stdout.decode('utf-8')
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

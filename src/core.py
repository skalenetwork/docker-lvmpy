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
from threading import Lock

from .config import (
    FILESTORAGE_MAPPING,
    MOUNTPOINT_BASE,
    PHYSICAL_VOLUME,
    SHARED_VOLUMES,
    VOLUME_GROUP,
)

logger = logging.getLogger(__name__)


LOGICAL_DEVICE_PREFIX = '/dev/mapper/{}-{}'


def compose_exponantional_timeouts(retries: int = 1) -> list:
    return [2 ** power for power in range(retries)]


class LvmPyError(Exception):
    pass


volume_lock = Lock()


def run_cmd(cmd, retries=3):
    res, err = None, None
    timeouts = compose_exponantional_timeouts(retries)
    lines = ' '.join(cmd)
    for attempt, timeout in enumerate(timeouts):
        logger.info(f'Command [{lines}] attempt {attempt}')
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            logger.info(f'Command [{lines}] success')
            return res.stdout
        else:
            err = res.stderr
            logger.error(
                f'Command [{lines}] attempt {attempt} '
                f'failed with {err}, out: {res.stdout}. Sleeping for {timeout}s'
            )
            time.sleep(timeout)
    raise LvmPyError(f'Command [{lines}] failed, error: {err}')


def volume_mountpoint(volume):
    return os.path.join(MOUNTPOINT_BASE, f'{VOLUME_GROUP}-{volume}')


def volume_device(volume):
    # lvm swaps all dashes to en dashes in block device name
    block_device_name = volume.replace('-', '--')
    return LOGICAL_DEVICE_PREFIX.format(VOLUME_GROUP, block_device_name)


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


def remove_physical_volume(physical_volume=PHYSICAL_VOLUME):
    if physical_volume in physical_volumes():
        run_cmd(['pvremove', physical_volume, '-y'])


def remove_volume_group(volume_group=VOLUME_GROUP):
    if volume_group in volume_groups():
        run_cmd(['vgremove', volume_group, '-y'])


def volume_groups():
    res = subprocess.run(['vgs', '-o', 'name'], capture_output=True, text=True)
    if res.returncode != 0:
        logger.error(f'Getting volume groups list failed {res.stderr}')
        raise LvmPyError('Getting volume groups list failed')

    vgs = list(filter(
        None,
        map(lambda x: x.strip(), res.stdout.split('\n'))
    ))[1:]
    return vgs


def ensure_volume_group(name=VOLUME_GROUP, physical_volume=PHYSICAL_VOLUME):
    vgs = volume_groups()
    if name in vgs:
        logger.warning(f'Volume group {name} already created')
        ensure_group_active(group=name)
        return

    ensure_physical_volume(physical_volume=physical_volume)

    with volume_lock:
        run_cmd(['vgcreate', name, physical_volume])


def create(name: str, size_unit: str) -> None:
    if size_unit.endswith('b'):
        size_unit = size_unit[:-1]
    logger.info(f'Creating volume with size {size_unit}b')
    with volume_lock:
        run_cmd(['lvcreate', '-L', f'{size_unit}b', '-n', name, VOLUME_GROUP, '-y'])
    res = subprocess.run(['mkfs.btrfs', '-f', volume_device(name)], capture_output=True, text=True)
    if res.returncode != 0:
        cmd_line = ' '.join(res.args)
        logger.error(f'Command {cmd_line} failed with {res.stderr}')
        remove(name)
        raise LvmPyError(f'Command {cmd_line} failed')


def remove(name: str) -> None:
    if name in SHARED_VOLUMES:
        logger.warning('Attempt to remove shared %s volume', name)
        return
    mountpoint = volume_mountpoint(name)
    logger.info(f'Removing device with {mountpoint}')
    if os.path.ismount(mountpoint):
        unmount(name)
    with volume_lock:
        run_cmd(['lvremove', '-f', volume_device(name)])
    logger.info(f'Checking if we need to remove {mountpoint}')
    if os.path.exists(mountpoint):
        logger.info(f'Removing {mountpoint}')
        os.rmdir(mountpoint)


def mount(name: str) -> str:
    is_shared = name in SHARED_VOLUMES
    logger.info('Mounting volume %s, shared: %s', name, is_shared)
    mountpoint = volume_mountpoint(name)
    device = volume_device(name)
    logger.info('Mountpoint for %s: %s, device: %s', name, mountpoint, device)
    if is_shared:
        with volume_lock:
            if os.path.ismount(mountpoint):
                logger.info(
                    'Shared volume %s is already mounted onto %s',
                    name, mountpoint
                )
            else:
                if not os.path.exists(mountpoint):
                    os.makedirs(mountpoint)
                run_cmd(['mount', device, mountpoint])
            return mountpoint

    if os.path.ismount(mountpoint):
        logger.info('%s mountpoint is already in use', mountpoint)
        unmount(name)
    if not os.path.exists(mountpoint):
        os.makedirs(mountpoint)

    with volume_lock:
        run_cmd(['mount', device, mountpoint])

    filestorage_path = os.path.join(mountpoint, 'filestorage')
    filestorage_link_path = os.path.join(FILESTORAGE_MAPPING, name)
    if os.path.islink(filestorage_link_path):
        os.unlink(filestorage_link_path)
    os.symlink(
        filestorage_path,
        filestorage_link_path,
        target_is_directory=True
    )
    logger.info(f'Symlink was created in {filestorage_link_path}')
    return mountpoint


def physical_volume_from_group(group: str) -> str | None:
    vgs = volume_groups()
    if group not in vgs:
        return None

    return run_cmd(['vgs', '-o', 'pv_name', group, '--noheadings']).strip()


def unmount(name):
    if name in SHARED_VOLUMES:
        logger.warning('Attempt to umount shared %s volume', name)
        return

    with volume_lock:
        run_cmd(['umount', volume_device(name)])

    os.remove(os.path.join(FILESTORAGE_MAPPING, name))


def path(name: str) -> str:
    mountpoint = volume_mountpoint(name)
    return mountpoint if os.path.ismount(mountpoint) else ''


def volumes(group=VOLUME_GROUP):
    stdout = run_cmd(['lvs', '-o', 'name', '-S', f'vg_name={group}'])
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


def get_block_device_size(device: str = PHYSICAL_VOLUME) -> int:
    """ Returns size of specified block device in bytes """
    result = run_cmd(['blockdev', '--getsize64', device], retries=1)
    size = int(result.strip())
    return size


def get_inactive_volumes(group: str = VOLUME_GROUP) -> list:
    output = run_cmd(['lvscan'])
    if not output:  # no volumes
        return []
    inactive = []
    for line in output.split('\n'):
        result = list(filter(lambda s: s.strip() != '', line.split()))
        if not result:
            break
        status, device = result[:2]
        # device example: '/dev/test/t1'
        device = device[2:-1]  # remove colums and / at the beginning
        _, device_group, volume = device.split('/')
        if device_group == group and status == 'inactive':
            inactive.append(volume)
    return inactive


def activate_group(group: str = VOLUME_GROUP) -> None:
    logger.info(f'Changing {group} to active')
    with volume_lock:
        run_cmd(['vgchange', '-ay', group])


def ensure_group_active(group: str = VOLUME_GROUP) -> None:
    groups = volume_groups()
    if group in groups:
        inactive = get_inactive_volumes(group=group)
        if len(inactive) > 0:
            logger.warning(
                f'Volume group {group} is not active. Inactive volumes: {inactive}'
            )
            activate_group(group=group)
    else:
        logger.error('Group %s does not exist', group)

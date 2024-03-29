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
# from threading import Lock
from multiprocessing import Lock
from typing import Optional

import psutil

from .config import (
    MOUNTPOINT_BASE,
    PHYSICAL_VOLUME,
    VOLUME_GROUP,
    FILESTORAGE_MAPPING,
    SHARED_VOLUMES
)

logger = logging.getLogger(__name__)


LOGICAL_DEVICE_PREFIX = '/dev/mapper/{}-{}'
UNMOUNT_RETRIES_NUMBER = 3
DEFAULT_RETRY_NUMBER = 3


def compose_exponantional_timeouts(retries: int = 1) -> list:
    return [2 ** power for power in range(retries)]


class LvmPyError(Exception):
    pass


volume_lock = Lock()

subprocess.run = partial(subprocess.run, stderr=subprocess.PIPE,
                         stdout=subprocess.PIPE)


def run_cmd(cmd, retries=3):
    res, err = None, None
    timeouts = compose_exponantional_timeouts(retries)
    lines = ' '.join(cmd)
    for attempt, timeout in enumerate(timeouts):
        logger.info(f'Command [{lines}] attempt {attempt}')
        res = subprocess.run(cmd)
        if res.returncode == 0:
            logger.info(f'Command [{lines}] success')
            return res.stdout.decode('utf-8')
        else:
            err = res.stderr.decode('utf-8')
            out = res.stdout.decode('utf-8')
            logger.error(
                f'Command [{lines}] attempt {attempt} '
                f'failed with {err}, out: {out}. Sleeping for {timeout}s'
            )
            time.sleep(timeout)
    raise LvmPyError(f'Command [{lines}] failed, error: {err}')


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


def remove_physical_volume(physical_volume=PHYSICAL_VOLUME):
    if physical_volume in physical_volumes():
        run_cmd(['pvremove', physical_volume, '-y'])


def remove_volume_group(volume_group=VOLUME_GROUP):
    if volume_group in volume_groups():
        run_cmd(['vgremove', volume_group, '-y'])


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
        run_cmd(['lvcreate', '-L', f'{size_unit}b', '-n', name, VOLUME_GROUP])
    res = subprocess.run(['mkfs.btrfs', '-f', volume_device(name)])
    if res.returncode != 0:
        stderr = res.stderr.decode('utf-8')
        cmd_line = ' '.join(res.args)
        logger.error(f'Command {cmd_line} failed with {stderr}')
        remove(name)
        raise LvmPyError(f'Command {cmd_line} failed')


def remove(name: str, is_schain=True) -> None:
    if name in SHARED_VOLUMES:
        logger.warning('Attempt to remove shared %s volume', name)
        return
    mountpoint = volume_mountpoint(name)
    logger.info(f'Removing device with {mountpoint}')
    if os.path.ismount(mountpoint):
        unmount(name, is_schain)
    with volume_lock:
        run_cmd(['lvremove', '-f', volume_device(name)])
    logger.info(f'Checking if we need to remove {mountpoint}')
    if os.path.exists(mountpoint):
        logger.info(f'Removing {mountpoint}')
        os.rmdir(mountpoint)


def mount(name: str, is_schain=True) -> str:
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
        unmount(name, is_schain)
    if not os.path.exists(mountpoint):
        os.makedirs(mountpoint)

    with volume_lock:
        run_cmd(['mount', device, mountpoint])

    if is_schain and not is_shared:
        filestorage_path = os.path.join(mountpoint, 'filestorage')
        filestorage_link_path = os.path.join(FILESTORAGE_MAPPING, name)
        os.symlink(
            filestorage_path,
            filestorage_link_path,
            target_is_directory=True
        )
        logger.info(f'Symlink was created in {filestorage_link_path}')
    return mountpoint


def physical_volume_from_group(group: str) -> str:
    vgs = volume_groups()
    if group not in vgs:
        return None

    return run_cmd(
        ['sudo', 'vgs', '-o', 'pv_name', group, '--noheadings']
    ).strip()


def path_user(path):
    res = subprocess.run(['fuser', path])
    if res.returncode == 0:
        str_pids = res.stdout.decode('utf-8').strip().split()
        return list(map(int, str_pids))
    else:
        return []


def file_in_path_user(path):
    logger.info(f'Checking who is using files in {path} ...')
    files = os.listdir(path)
    if len(files) == 0:
        return []
    filepath = os.path.join(path, files[0])
    logger.info(f'Checking filepath {filepath} ...')
    return path_user(filepath)


def log_lsof_for_volume_device(volume):
    device = volume_device(volume)
    logger.info(f'Checking lsof for {device}')
    cmd = ['lsof', '+f', '--', device]
    res = subprocess.run(cmd)
    out = res.stdout.decode('utf-8')
    err = res.stderr.decode('utf-8')
    logger.info(f'Lsof returned err: {err}; out: {out}')


def device_users(name):
    path = volume_device(name)
    return path_user(path)


def mountpoint_users(name):
    path = volume_mountpoint(name)
    return path_user(path)


def file_users(name):
    path = volume_mountpoint(name)
    return file_in_path_user(path)


def process_info(pid):
    ps = psutil.Process(pid)
    return ps.as_dict()


def log_consumers(consumers):
    for pid in consumers:
        info = process_info(pid)
        logger.info(f'PID {pid}: {info}')


def unmount(name, is_schain=True):
    if name in SHARED_VOLUMES:
        logger.warning('Attempt to umount shared %s volume', name)
        return

    log_lsof_for_volume_device(name)

    device_consumers = device_users(name)
    logger.info(f'Device is used by {len(device_consumers)}: '
                f'{device_consumers}')
    log_consumers(device_consumers)

    mountpoint_consumers = mountpoint_users(name)
    logger.info(f'Mountpoint is used by {len(mountpoint_consumers)}: '
                f'{mountpoint_consumers}')
    log_consumers(mountpoint_consumers)

    file_consumers = file_users(name)
    logger.info(f'File is used by {len(file_consumers)}: '
                f'{file_consumers}')
    log_consumers(file_consumers)

    device = volume_device(name)
    cmd = ['umount', device]
    with volume_lock:
        run_cmd(cmd, retries=UNMOUNT_RETRIES_NUMBER)

    if is_schain:
        link_name = os.path.join(FILESTORAGE_MAPPING, name)
        os.remove(link_name)


def path(name):
    stdout = run_cmd(['findmnt', volume_device(name), '--output', 'source'])
    if not stdout:
        return None

    result = list(filter(None, stdout.split('\n')))[1]
    return result


def volumes(group=VOLUME_GROUP):
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


def get_block_device_size(device: str = PHYSICAL_VOLUME) -> int:
    """ Returns size of specified block device in bytes """
    result = run_cmd(['blockdev', '--getsize64', device], retries=1)
    size = int(result.strip())
    return size


def get_inactive_volumes(group: Optional[str] = VOLUME_GROUP) -> list:
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
        _, group, volume = device.split('/')
        if group == group and status == 'inactive':
            inactive.append(volume)
    return inactive


def activate_group(group: Optional[str] = VOLUME_GROUP) -> None:
    logger.info(f'Changing {group} to active')
    with volume_lock:
        run_cmd(['vgchange', '-ay', group])


def ensure_group_active(group: Optional[str] = VOLUME_GROUP) -> None:
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

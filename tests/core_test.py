import os
import time
from multiprocessing import Process

import mock
import pytest

from config import FILESTORAGE_MAPPING
from core import (
    create, remove, volumes, LvmPyError,
    mount, path, unmount,
    get as get_volume,
    device_users,
    ensure_volume_group,
    file_users,
    get_inactive_volumes,
    mountpoint_users,
    physical_volume_from_group,
    run_cmd,
    volume_device,
    volume_mountpoint
)

FIRST_VOLUME_NAME = 'vol-a'
SECOND_VOLUME_NAME = 'vol_b'
SHARED_VOLUME = 'shared-space'


def test_create_remove(vg):
    create(FIRST_VOLUME_NAME, '250m')
    create(SECOND_VOLUME_NAME, '300M')

    lvs = volumes()
    assert FIRST_VOLUME_NAME in lvs
    assert SECOND_VOLUME_NAME in lvs

    with pytest.raises(LvmPyError):
        create(FIRST_VOLUME_NAME, '250m')

    remove(FIRST_VOLUME_NAME)
    remove(SECOND_VOLUME_NAME)

    lvs = volumes()
    assert FIRST_VOLUME_NAME not in lvs
    assert SECOND_VOLUME_NAME not in lvs
    assert not os.path.isdir(volume_mountpoint(FIRST_VOLUME_NAME))
    assert not os.path.isdir(volume_mountpoint(SECOND_VOLUME_NAME))


def test_remove_not_existing(vg):
    def timeouts_mock(retries):
        return [1 for _ in range(retries)]
    with mock.patch('core.compose_exponantional_timeouts', timeouts_mock):
        with pytest.raises(LvmPyError):
            remove('Not-existing-volume')


def test_create_small_size(vg):
    with pytest.raises(LvmPyError):
        create(FIRST_VOLUME_NAME, '1m')


def test_get_volume(vg):
    create(FIRST_VOLUME_NAME, '250m')

    name = get_volume(FIRST_VOLUME_NAME)
    assert name == FIRST_VOLUME_NAME
    assert get_volume('Not-existing-volume') is None

    remove(FIRST_VOLUME_NAME)


def test_mount_unmount(vg):
    create(FIRST_VOLUME_NAME, '250m')

    mount(FIRST_VOLUME_NAME)

    mountpoint = path(FIRST_VOLUME_NAME)
    assert mountpoint == '/dev/mapper/schains-vol--a'
    assert os.path.islink(os.path.join(FILESTORAGE_MAPPING, FIRST_VOLUME_NAME))

    unmount(FIRST_VOLUME_NAME)
    with pytest.raises(LvmPyError):
        path(FIRST_VOLUME_NAME)

    remove(FIRST_VOLUME_NAME)
    assert not os.path.exists(
        os.path.join(
            FILESTORAGE_MAPPING,
            FIRST_VOLUME_NAME
        )
    )


@pytest.fixture
def tmp_shared(vg):
    yield SHARED_VOLUME
    if SHARED_VOLUME in volumes():
        device = volume_device(SHARED_VOLUME)
        mountpoint = volume_mountpoint(SHARED_VOLUME)
        if os.path.ismount(mountpoint):
            run_cmd(['umount', device])


def test_create_remove_shared(vg, tmp_shared):
    create(SHARED_VOLUME, '250m')
    lvs = volumes()
    assert SHARED_VOLUME in lvs

    remove(SHARED_VOLUME)
    lvs = volumes()
    assert SHARED_VOLUME in lvs


def aquire_volume(volume_name):
    timeout_before_unmount = 20
    mount(volume_name)
    volume_filename = os.path.join(
        volume_mountpoint(volume_name),
        'test'
    )
    with open(volume_filename, 'w'):
        time.sleep(timeout_before_unmount)
    unmount(volume_name)


def test_device_users(vg):
    create(FIRST_VOLUME_NAME, '250m')

    p = Process(target=aquire_volume, args=(FIRST_VOLUME_NAME,))
    p.start()
    time.sleep(10)
    device_consumers_running = device_users(FIRST_VOLUME_NAME)
    p.join()
    device_consumers_finished = device_users(FIRST_VOLUME_NAME)
    remove(FIRST_VOLUME_NAME)

    assert isinstance(device_consumers_running, list)
    assert device_consumers_finished == []


def test_mountpoint_users(vg):
    create(SECOND_VOLUME_NAME, '250m')

    p = Process(target=aquire_volume, args=(SECOND_VOLUME_NAME,))
    p.start()
    time.sleep(3)
    mountpoint_consumers_running = mountpoint_users(SECOND_VOLUME_NAME)
    p.join()
    mountpoint_consumers_finished = mountpoint_users(SECOND_VOLUME_NAME)
    remove(SECOND_VOLUME_NAME)

    assert isinstance(mountpoint_consumers_running, list)
    assert mountpoint_consumers_finished == []


def test_file_users(vg):
    create(SECOND_VOLUME_NAME, '250m')

    p = Process(target=aquire_volume, args=(SECOND_VOLUME_NAME,))
    p.start()
    time.sleep(3)
    file_consumers_running = file_users(SECOND_VOLUME_NAME)
    p.join()
    file_consumers_finished = file_users(SECOND_VOLUME_NAME)
    remove(SECOND_VOLUME_NAME)

    assert isinstance(file_consumers_running, list)
    assert file_consumers_finished == []


def test_physical_volume_from_group(pv, vg):
    block_device = physical_volume_from_group(vg)
    assert block_device == pv
    block_device = physical_volume_from_group('not-existing-vg')
    assert block_device is None


def test_volume_group_activation(pv, vg):
    assert get_inactive_volumes(group=vg) == []
    create(FIRST_VOLUME_NAME, '250m')
    assert get_inactive_volumes(group=vg) == []
    run_cmd(['vgchange', '-an', vg])
    assert get_inactive_volumes(group=vg) == [FIRST_VOLUME_NAME]
    ensure_volume_group(name=vg)
    assert get_inactive_volumes(group=vg) == []

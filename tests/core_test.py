import os
from unittest import mock

import pytest

from src.config import FILESTORAGE_MAPPING
from src.core import (
    LvmPyError,
    create,
    ensure_volume_group,
    get_inactive_volumes,
    mount,
    path,
    physical_volume_from_group,
    remove,
    run_cmd,
    unmount,
    volume_device,
    volume_mountpoint,
    volumes,
)
from src.core import get as get_volume

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
    with mock.patch('src.core.compose_exponantional_timeouts', timeouts_mock):
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

    assert path(FIRST_VOLUME_NAME) == volume_mountpoint(FIRST_VOLUME_NAME)
    assert os.path.islink(os.path.join(FILESTORAGE_MAPPING, FIRST_VOLUME_NAME))

    unmount(FIRST_VOLUME_NAME)
    assert path(FIRST_VOLUME_NAME) == ''

    remove(FIRST_VOLUME_NAME)
    assert not os.path.exists(
        os.path.join(
            FILESTORAGE_MAPPING,
            FIRST_VOLUME_NAME
        )
    )


@pytest.fixture
def shared(vg):
    try:
        create(SHARED_VOLUME, '250m')
        yield SHARED_VOLUME
    finally:
        if SHARED_VOLUME in volumes():
            device = volume_device(SHARED_VOLUME)
            mountpoint = volume_mountpoint(SHARED_VOLUME)
            if os.path.ismount(mountpoint):
                run_cmd(['umount', device])
            run_cmd(['lvremove', '-f', volume_device(SHARED_VOLUME)])


def test_create_remove_shared(vg, shared):
    lvs = volumes()
    assert SHARED_VOLUME in lvs

    remove(SHARED_VOLUME)
    lvs = volumes()
    assert SHARED_VOLUME in lvs


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

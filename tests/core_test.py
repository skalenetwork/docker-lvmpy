import pytest

from core import (
    create, remove, volumes, LvmPyError,
    mount, path, unmount,
    get as get_volume
)

FIRST_VOLUME_NAME = 'vol-a'
SECOND_VOLUME_NAME = 'vol_b'


def test_create_remove(vg):
    create(FIRST_VOLUME_NAME, '250m')
    create(SECOND_VOLUME_NAME, '300m')

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


def test_remove_not_existing(vg):
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

    unmount(FIRST_VOLUME_NAME)
    with pytest.raises(LvmPyError):
        path(FIRST_VOLUME_NAME)

    remove(FIRST_VOLUME_NAME)

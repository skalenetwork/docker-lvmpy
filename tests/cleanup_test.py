import pytest

from src.core import (
    physical_volumes,
    run_cmd,
    volume_groups
)
from src.cleanup import (
    cleanup_lvmpy_aritifacts,
    is_block_device_exist,
    is_cleanup_needed,
    is_lvmpy_environment_valid
)


@pytest.fixture
def lvm_volume(vg):
    name = 'test-volume'
    size = 1024
    run_cmd(['lvcreate', '-L', f'{size}B', '-n', name, vg])
    yield name
    run_cmd(['lvremove', vg, '-y'])


def test_is_lvmpy_environment_valid_same_block_device(pv, vg):
    assert is_lvmpy_environment_valid(pv, vg)


def test_is_lvmpy_environment_valid_diff_block_device_no_volumes(pv, vg):
    block_device = 'block-device'
    assert is_lvmpy_environment_valid(block_device, vg)


def test_is_lvmpy_environment_valid_diff_block_device_with_volumes(
    pv, vg, lvm_volume
):
    block_device = 'block-device'
    assert not is_lvmpy_environment_valid(block_device, vg)


def test_is_block_device_exists(pv, vg):
    assert is_block_device_exist(pv)
    block_device = 'not-existing-block_device'
    assert not is_block_device_exist(block_device)


def test_is_cleanup_needed_same_block_device(pv, vg):
    assert not is_cleanup_needed(pv, vg)


def test_is_cleanup_needed_another_block_device(pv, vg):
    another_bd = 'another-block-device'
    assert is_cleanup_needed(another_bd, vg)


def test_is_cleanup_needed_no_vg():
    device = 'not-exising-device'
    group = 'not-existing-group'
    assert not is_cleanup_needed(device, group)


def test_cleanup_lvmpy_aritifacts(pv, vg):
    cleanup_lvmpy_aritifacts(vg)
    assert volume_groups() == []
    assert physical_volumes() == []

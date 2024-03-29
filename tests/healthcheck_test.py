import docker
import mock
import pytest

from src.health import (
    EndpointCheck,
    PreinstallCheck,
    heal_service
)
from src.core import run_cmd


@pytest.fixture
def hc():
    h = PreinstallCheck(container='test-container', volume='test-volume')
    yield h
    h.remove_simple_container()
    h.remove_volume_using_driver()


def test_healthcheck(vg, hc):
    hc.run()


def test_healthcheck_volume_creation_failed(vg, hc):
    class VolumeCreationError(Exception):
        pass

    with mock.patch.object(hc, 'create_volume_using_driver',
                           side_effect=VolumeCreationError('Test error')):
        with pytest.raises(VolumeCreationError):
            hc.run()


def test_healthcheck_volume_removing_failed(vg, hc):
    class VolumeRemovingError(Exception):
        pass

    with mock.patch.object(hc, 'remove_volume_using_driver',
                           side_effect=VolumeRemovingError('Test error')):
        with pytest.raises(VolumeRemovingError):
            hc.run()


def test_healthcheck_container_creation_failed(vg, hc):
    class ContainerCreationError(Exception):
        pass

    with mock.patch.object(hc, 'create_simple_container',
                           side_effect=ContainerCreationError('Test error')):
        with pytest.raises(ContainerCreationError):
            hc.run()


def test_healthcheck_container_removing_failed(vg, hc):
    class ContainerRemovingError(Exception):
        pass

    with mock.patch.object(hc, 'remove_simple_container',
                           side_effect=ContainerRemovingError('Test error')):
        # Docker won't be able to remove volume because it will be in use
        with pytest.raises(docker.errors.APIError):
            hc.run()


def test_healthcheck_volume_status_failed(vg, hc):
    class VolumeStatusError(Exception):
        pass
    with mock.patch.object(hc, 'check_volume_status',
                           side_effect=VolumeStatusError('Test error')):
        with pytest.raises(VolumeStatusError):
            hc.run()


def test_healthcheck_container_status_failed(vg, hc):
    class ContainerStatusError(Exception):
        pass
    with mock.patch.object(hc, 'check_container_status',
                           side_effect=ContainerStatusError('Test error')):
        with pytest.raises(ContainerStatusError):
            hc.run()


@pytest.fixture
def disable_btrfs():
    run_cmd(['modprobe', '-r', 'btrfs'])
    yield
    run_cmd(['modprobe', 'btrfs'])


@pytest.mark.skip('Works only on some systems')
def test_btrfs_not_loaded(vg, hc, disable_btrfs):
    with pytest.raises(docker.errors.APIError):
        hc.run()


def test_heal_service():
    r = heal_service()
    assert r is False
    broken_ec = EndpointCheck(url='http://127.0.0.1:3333')
    r = heal_service(broken_ec)
    assert r is True

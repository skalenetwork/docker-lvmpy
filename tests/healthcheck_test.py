import mock

from core import LvmPyError
from healthcheck import healthcheck


def test_healthcheck(vg):
    result = healthcheck(vg)
    assert result == {'status': 'ok', 'data': 'Success'}


@mock.patch('healthcheck.create_volume',
            side_effect=LvmPyError('Test error'))
def test_healthcheck_creation_failed(vg):
    result = healthcheck(vg)
    assert result == {
        'status': 'error',
        'data': 'Volume creation failed with: "Test error"'
    }


@mock.patch('healthcheck.remove_volume',
            side_effect=LvmPyError('Test error'))
def test_healthcheck_removing_failed(vg):
    result = healthcheck(vg)
    assert result == {
        'status': 'error',
        'data': 'Volume removing failed with: "Test error"'
    }

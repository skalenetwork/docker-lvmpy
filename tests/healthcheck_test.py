import mock
from docker.errors import APIError

from healthcheck import healthcheck


def test_healthcheck(vg):
    result = healthcheck()
    assert result == {'status': 'ok', 'data': 'Success'}


@mock.patch('healthcheck.create_volume_using_driver',
            side_effect=APIError('Test error'))
def test_healthcheck_creation_failed(create_volume_mock, vg):
    result = healthcheck()
    assert result == {
        'status': 'error',
        'data': 'Volume creation failed with: "Test error"'
    }


@mock.patch('healthcheck.create_volume_using_driver')
@mock.patch('healthcheck.remove_volume_using_driver',
            side_effect=APIError('Test error'))
def test_healthcheck_removing_failed(create_volume_mock,
                                     remove_volume_using_driver, vg):
    result = healthcheck(vg)
    assert result == {
        'status': 'error',
        'data': 'Volume removing failed with: "Test error"'
    }

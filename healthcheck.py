import sys

from core import (
    create as create_volume,
    remove as remove_volume
)

MIN_BTRFS_VOLUME_SIZE = 209715200


def healthcheck(volume_group: str, size: int = MIN_BTRFS_VOLUME_SIZE) -> dict:
    volume_name = 'healthcheck-volume'
    try:
        create_volume(volume_name, size=size)
    except Exception as err:
        return {
            'status': 'error',
            'data': f'Volume creation failed with: "{str(err)}"'
        }

    try:
        remove_volume(volume_name)
    except Exception as err:
        return {
            'status': 'error',
            'data': f'Volume removing failed with: "{str(err)}"'
        }

    return {'status': 'ok', 'data': 'Success'}


def main():
    volume_group = sys.argv[1]
    result = healthcheck(volume_group)
    if result['status'] == 'error':
        print('Error: {result["data"]')
        exit(1)
    else:
        print('Healthcheck passed')

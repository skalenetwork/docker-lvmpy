import docker

MIN_BTRFS_VOLUME_SIZE = 209715200


client = docker.from_env()


def create_volume_using_driver(name: str,
                               size: int) -> docker.models.volumes.Volume:
    return client.volumes.create(
        name=name, driver='lvmpy',
        driver_opts={'size': str(size)},
    )


def remove_volume_using_driver(volume: docker.models.volumes.Volume):
    return volume.remove()


def healthcheck(size: int = MIN_BTRFS_VOLUME_SIZE) -> dict:
    volume_name = 'healthcheck-volume'
    volume = None
    try:
        volume = create_volume_using_driver(name=volume_name, size=size)
    except Exception as err:
        return {
            'status': 'error',
            'data': f'Volume creation failed with: "{str(err)}"'
        }

    try:
        remove_volume_using_driver(volume)
    except Exception as err:
        return {
            'status': 'error',
            'data': f'Volume removing failed with: "{str(err)}"'
        }

    return {'status': 'ok', 'data': 'Success'}


def main():
    result = healthcheck()
    if result['status'] == 'error':
        print(f'Error: {result["data"]}')
        exit(1)
    else:
        print('Healthcheck passed')


if __name__ == '__main__':
    main()

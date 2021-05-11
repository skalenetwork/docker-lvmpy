import traceback
from contextlib import contextmanager

import docker

MIN_BTRFS_VOLUME_SIZE = 209715200


class Healthcheck:
    def __init__(
        self, container: str,
        volume: str,
        volume_size: int = MIN_BTRFS_VOLUME_SIZE
    ):
        self.container = container
        self.volume = volume
        self.volume_size = volume_size
        self.client = docker.from_env()
        self.exc_type = None
        self.exc_value = None
        self.tb = None

    def create_volume_using_driver(self) -> docker.models.volumes.Volume:
        print('Creating lvmpy volume ...')
        driver = 'lvmpy'
        self.client.volumes.create(
            name=self.volume, driver=driver,
            driver_opts={'size': str(self.volume_size)},
        )
        print('Lvmpy volume was created')

    def remove_volume_using_driver(self):
        print('Removing lvmpy volume ...')
        try:
            self.client.volumes.get(self.volume).remove()
        except docker.errors.NotFound:
            print(f'No such volume {self.volume}')
            return
        print('Lvmpy volume was removed')

    def create_simple_container(self) -> docker.models.containers.Container:
        print('Creating simple container ...')
        mount_path = '/test'
        mode = 'rw'
        image = 'alpine:latest'
        self.client.containers.run(
            name=self.container,
            image=image,
            command='sleep 30',
            detach=True,
            volumes={
                self.volume: {'bind': mount_path, 'mode': mode}
            }
        )
        print('Simple container was created')

    def remove_simple_container(self):
        print('Removing simple container ...')
        try:
            self.client.containers.get(self.container).remove(force=True)
        except docker.errors.NotFound:
            print(f'No such container {self.container}')
            return
        print('Simple container was removed')

    def check_volume_status(self):
        self.client.volumes.get(self.volume)

    def check_container_status(self):
        c = self.client.containers.get(self.container)
        assert c.status == 'running', f'Actual status: {c.status}'

    @contextmanager
    def lvmpy_volume(self):
        try:
            yield self.create_volume_using_driver()
        finally:
            self.remove_volume_using_driver()

    @contextmanager
    def lvmpy_container(self):
        try:
            yield self.create_simple_container()
        finally:
            self.remove_simple_container()

    def run(self):
        with self.lvmpy_volume():
            with self.lvmpy_container():

                from sh import lsmod
                _ = next(
                    filter(lambda s: 'btrfs' in s, lsmod().split('\n')))
                _ = next(
                    filter
                    (lambda s: s.startswith('btrfs'), lsmod().split('\n')))
                self.check_volume_status()
                self.check_container_status()


def main():
    hc = Healthcheck(
        container='healthcheck-container',
        volume='healthcheck-volume'
    )
    try:
        hc.run()
    except Exception:
        traceback.print_exc()
        print('Driver is not healthy')
        exit(1)
    else:
        print('Driver is healthy')


if __name__ == '__main__':
    main()

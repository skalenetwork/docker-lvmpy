import traceback
from contextlib import contextmanager
from functools import partial

import docker

MIN_BTRFS_VOLUME_SIZE = 209715200


def is_btrfs_loaded():
    from sh import lsmod
    modules = list(
        filter(lambda s: s.startswith('btrfs'), lsmod().split('\n'))
    )
    return modules != []


class ContainerNotRunningError(Exception):
    pass


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
            command='sleep 500',
            cap_add=['SYS_ADMIN'],
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
        if c.status != 'running':
            raise ContainerNotRunningError(f'{self.container} is not running')

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

    @contextmanager
    def btrfs_snapshot(self):
        c = self.client.containers.get(self.container)
        c.erun = partial(c.exec_run, workdir='/test')
        try:
            print('Installing btrfs-progs')
            r = c.exec_run(['apk', 'add', 'btrfs-progs'])
            assert r.exit_code == 0, r
            print('Creating subvolume')
            r = c.erun(['btrfs', 'subvolume', 'create', 'test-sub'])
            assert r.exit_code == 0, r
            print('Creating snapshot')
            r = c.erun([
                'btrfs',
                'subvolume',
                'snapshot',
                'test-sub',
                'test-snap'
            ])
            assert r.exit_code == 0, r
            yield 'Subvolume and snapshots are created'
        finally:
            print('Removing subvolume')
            r = c.erun(['btrfs', 'subvolume', 'delete', 'test-sub'])
            assert r.exit_code == 0, r
            print('Removing snapshot')
            r = c.erun(['btrfs', 'subvolume', 'delete', 'test-snap'])
            assert r.exit_code == 0, r

    def run(self):
        with self.lvmpy_volume():
            with self.lvmpy_container():
                self.check_volume_status()
                self.check_container_status()
                with self.btrfs_snapshot() as msg:
                    print(msg)


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

import logging
import sys
import time
import traceback
from contextlib import contextmanager
from typing import Optional

import docker
import requests

from config import VOLUME_LIST_ROUTE
from core import (
    activate_volumes,
    activate_volume_group,
    run_cmd
)

MIN_BTRFS_VOLUME_SIZE = 209715200


logger = logging.getLogger(__name__)


def is_btrfs_loaded():
    from sh import lsmod
    modules = list(
        filter(lambda s: s.startswith('btrfs'), lsmod().split('\n'))
    )
    return modules != []


class ContainerNotRunningError(Exception):
    pass


class ExecFailedError(Exception):
    pass


class EndpointCheck:
    def __init__(self, url: str = VOLUME_LIST_ROUTE):
        self.url = url

    def run(self) -> bool:
        retries = 5
        res, code, err = None, None, None
        for attempt in range(retries):
            logger.debug(f'Checking lvmpy endpoint. Attempt: {attempt}')
            try:
                res = requests.post(self.url)
                code = res.status_code
            except Exception as e:
                err = e
                logger.exception('Error during checking lvmpy health')
            else:
                break
            time.sleep(2)

        if code == 200:
            logger.info('Lvmpy is healthy %s', res)
            return True
        else:
            logger.error('Lvmpy is not healthy %d %s', code, err)
            return False


class PreinstallCheck:
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
        print('Creating lvmpy volume')
        driver = 'lvmpy'
        self.client.volumes.create(
            name=self.volume, driver=driver,
            driver_opts={'size': str(self.volume_size)},
        )
        print('Lvmpy volume was created')

    def remove_volume_using_driver(self):
        print('Removing lvmpy volume')
        try:
            self.client.volumes.get(self.volume).remove()
        except docker.errors.NotFound:
            print(f'No such volume {self.volume}')
            return
        print('Lvmpy volume was removed')

    def create_simple_container(self) -> docker.models.containers.Container:
        print('Creating simple container')
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
        print('Removing simple container')
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

        def crun(*args, **kwargs):
            r = c.exec_run(*args, **kwargs, workdir='/test')
            if r.exit_code != 0:
                print('Command failed {r}')
                raise ExecFailedError(r.output)

        try:
            print('Installing btrfs-progs')
            crun(['apk', 'add', 'btrfs-progs'])
            print('Creating subvolume')
            crun(['btrfs', 'subvolume', 'create', 'test-sub'])
            print('Creating snapshot')
            crun(['btrfs', 'subvolume', 'snapshot', 'test-sub', 'test-snap'])
            yield 'Subvolume and snapshots are created'
        finally:
            print('Removing subvolume')
            crun(['btrfs', 'subvolume', 'delete', 'test-sub'])
            print('Removing snapshot')
            crun(['btrfs', 'subvolume', 'delete', 'test-snap'])

    def run(self):
        with self.lvmpy_volume():
            with self.lvmpy_container():
                self.check_volume_status()
                self.check_container_status()
                with self.btrfs_snapshot() as msg:
                    print(msg)


def heal_service(ec: Optional[EndpointCheck] = None) -> bool:
    ec = ec or EndpointCheck()
    if not ec.run():
        print('Lvmpy is ill. Restarting the service')
        res = run_cmd(['systemctl', 'restart', 'docker-lvmpy'])
        print(f'Lvmpy restart command result: {res}')
        print('Lvmpy has been restarted')
        return True
    return False


def ensure_volumes_active(group: str) -> None:
    activate_volume_group(group=group)
    activate_volumes(group=group)


def main():
    if len(sys.argv) > 1:
        vg = sys.argv[1]
        ensure_volumes_active(vg)
    pc = PreinstallCheck(
        container='healthcheck-container',
        volume='healthcheck-volume'
    )
    try:
        pc.run()
    except Exception:
        traceback.print_exc()
        print('Driver is not healthy')
        exit(1)
    else:
        print('Driver is healthy')


if __name__ == '__main__':
    main()

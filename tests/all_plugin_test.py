import os
import pathlib
import requests
import subprocess
import time
from concurrent.futures import as_completed, ProcessPoolExecutor

import docker
import pytest

from src.config import FILESTORAGE_MAPPING
from src.core import run_cmd, volumes, volume_device, volume_mountpoint

PHYSICAL_VOLUME = os.getenv('PHYSICAL_VOLUME')
VOLUME_GROUP = 'schains'
VOLUME = 'pytest_docker_lvm'
DRIVER = 'lvmpy'
SIZE = 200
IMAGE = 'pytest-ubuntu'
CONTAINER = 'pytest_lvmpy'

NUMBER_OF_CONTAINERS = 6
ITERATIONS = 2

SHARED_VOLUME = 'shared-space'


client = docker.client.from_env()


def test_create_remove_docker_py_info(capfd):
    res = subprocess.run(['docker', 'volume', 'create', '-d', DRIVER,
                          '--opt', f'size={SIZE}M', '--name', VOLUME])
    assert res.returncode == 0

    assert VOLUME in [v.name for v in client.volumes.list()]
    assert client.volumes.get(VOLUME).name == VOLUME

    res = subprocess.run(['docker', 'volume', 'remove', VOLUME])
    assert res.returncode == 0

    assert VOLUME not in client.volumes.list()


def test_create_remove_lsblk_info(capfd):
    res = subprocess.run(['docker', 'volume', 'create', '-d', DRIVER,
                          '--opt', f'size={SIZE}M', '--name', VOLUME])
    assert res.returncode == 0

    res = subprocess.call(['lsblk', '-l', '-o', 'name,size,type'])
    captured = capfd.readouterr()
    lines = list(filter(None, captured.out.split('\n')))
    cleanuped_lines = list(
        filter(None, map(lambda line: line.strip().split(), lines)))
    expected = [f'{VOLUME_GROUP}-{VOLUME}', f'{SIZE}M', 'lvm']
    assert expected in cleanuped_lines

    res = subprocess.run(['docker', 'volume', 'remove', VOLUME])
    assert res.returncode == 0

    res = subprocess.call(['lsblk', '-l', '-o', 'name'])
    captured = capfd.readouterr()
    lines = captured.out.split('\n')
    assert f'{VOLUME_GROUP}-{VOLUME}' not in lines


def test_container_exec_using_volume(capfd):
    res = subprocess.run(['docker', 'build', 'tests/container',
                          '--tag', IMAGE])
    assert res.returncode == 0
    res = subprocess.run(['docker', 'volume', 'create', '-d', DRIVER,
                          '--opt', f'size={SIZE}M', '--name', VOLUME])

    assert res.returncode == 0
    res = subprocess.run(['docker', 'run', '--cap-add', 'SYS_ADMIN',
                          '-d', f'--name={CONTAINER}', '-v',
                          f'{VOLUME}://btrfs//', IMAGE, 'sleep', '10'])
    assert res.returncode == 0
    res = subprocess.run(['docker', 'exec', CONTAINER,
                          'ls', '-altr', '//btrfs//'])
    assert res.returncode == 0

    res = subprocess.run(['docker', 'exec', CONTAINER,
                          'btrfs', 'sub', 'create', '//btrfs//x'])
    assert res.returncode == 0

    res = subprocess.run(['docker', 'rm', '-f', CONTAINER])
    assert res.returncode == 0

    res = subprocess.run(['docker', 'volume', 'rm', VOLUME])
    assert res.returncode == 0


def create_volumes(volumes_number=NUMBER_OF_CONTAINERS):
    volumes = [
        client.volumes.create(name=f'test{i}', driver='lvmpy', driver_opts={})
        for i in range(volumes_number)
    ]
    return volumes


def remove_volumes(volumes):
    for volume in volumes:
        volume.remove(force=True)


def create_containers(container_number=NUMBER_OF_CONTAINERS):
    containers = [
        client.containers.run(image=IMAGE,
                              name=f'test{i}',
                              detach=True,
                              cap_add=['SYS_ADMIN'],
                              volumes={f'test{i}': {
                                  'bind': '/data', 'mode': 'rw'}
                              })
        for i in range(container_number)
    ]
    for c in containers:
        print(c)
    return containers


def remove_containers(containers):
    for c in containers:
        c.remove(force=True)
    print('Containers removed')


def restart_containers(containers):
    for c in containers:
        c.restart()
    print('Containers restarted')


def running_containers_number():
    return len(client.containers.list())


def test_containers_creation():
    volumes = create_volumes()
    try:
        containers = create_containers()
        time.sleep(15)
    finally:
        run_cmd(['systemctl', '-l', 'status', 'docker-lvmpy'])
        remove_containers(containers)
        remove_volumes(volumes)


def create_remove_volume(name):
    sleep_interval = 2
    iterations = 10
    for i in range(iterations):
        volume = client.volumes.create(
            name=name,
            driver='lvmpy', driver_opts={}
        )
        time.sleep(sleep_interval)
        volume.remove(force=True)
        time.sleep(sleep_interval)


def test_concurrent_volume_creation():
    assert client.volumes.list() == []
    thread_number = 20
    max_workers = 5
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                create_remove_volume,
                f'test{i}'
            )
            for i in range(thread_number)
        ]
        for future in futures:
            future.result()
    assert client.volumes.list() == []


def test_docker_system_restart():
    for iteration in range(ITERATIONS):
        volumes = create_volumes()
        containers = create_containers()
        time.sleep(15)
        subprocess.run(['systemctl', 'restart', 'docker'])
        time.sleep(15)
        restart_containers(containers)
        time.sleep(15)
        assert running_containers_number() == NUMBER_OF_CONTAINERS, iteration
        time.sleep(15)
        remove_containers(containers)
        remove_volumes(volumes)


def test_get_block_device_size():
    response = requests.get(
        'http://127.0.0.1:7373/physical-volume-size',
        json={'Name': None}
    )
    data = response.json()
    assert data['Err'] == ''
    assert data['Name'] == PHYSICAL_VOLUME
    assert data['Size'] > 0

    response = requests.get(
        'http://127.0.0.1:7373/physical-volume-size',
        json={'Name': PHYSICAL_VOLUME}
    )
    data = response.json()
    assert data['Err'] == ''
    assert data['Name'] == PHYSICAL_VOLUME
    assert data['Size'] > 0

    response = requests.get(
        'http://127.0.0.1:7373/physical-volume-size',
        json={'Name': '/dev/None'}
    )
    data = response.json()
    assert data['Err'] == 'No such volume'


def test_container_mapping():
    volumes = create_volumes(1)
    containers = create_containers(1)
    link_path = os.path.join(FILESTORAGE_MAPPING, volumes[0].name)

    assert pathlib.Path(link_path).is_symlink(), link_path

    remove_containers(containers)
    remove_volumes(volumes)
    assert not os.path.exists(link_path), link_path


@pytest.fixture
def shared_volume():
    v = client.volumes.create(
        name=SHARED_VOLUME,
        driver='lvmpy',
        driver_opts={}
    )
    try:
        yield v
    finally:
        if SHARED_VOLUME in volumes():
            device = volume_device(SHARED_VOLUME)
            mountpoint = volume_mountpoint(SHARED_VOLUME)
            if os.path.ismount(mountpoint):
                run_cmd(['umount', device])
            run_cmd(['lvremove', '-f', device])


def test_shared_volume(shared_volume):
    c1, c2 = None, None
    try:
        c1 = client.containers.run(
            image=IMAGE,
            name='test-shared-0',
            detach=True,
            cap_add=['SYS_ADMIN'],
            volumes={SHARED_VOLUME: {'bind': '/data', 'mode': 'rw'}}
        )
        c2 = client.containers.run(
            image=IMAGE,
            name='test-shared-1',
            detach=True,
            cap_add=['SYS_ADMIN'],
            volumes={SHARED_VOLUME: {'bind': '/data', 'mode': 'rw'}}
        )
        time.sleep(3)
    finally:
        if c1:
            c1.remove(force=True)
        if c2:
            c2.remove(force=True)


def create_remove_container(name, volumes):
    client = docker.client.from_env()
    c1 = client.containers.run(
        image=IMAGE,
        name=name,
        detach=True,
        cap_add=['SYS_ADMIN'],
        volumes=volumes
    )
    time.sleep(3)
    c1.remove(force=True)
    return 'Success'


def test_shared_volume_concurrent(shared_volume):
    with ProcessPoolExecutor(max_workers=5) as e:
        futures = [
            e.submit(
                create_remove_container,
                name=f'test-{i}',
                volumes={SHARED_VOLUME: {'bind': '/data', 'mode': 'rw'}}
            )
            for i in range(3)
        ]
        for f in as_completed(futures):
            assert f.result() == 'Success'

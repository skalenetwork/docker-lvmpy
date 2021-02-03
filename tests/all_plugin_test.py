import subprocess
import time
from concurrent.futures import ProcessPoolExecutor
import docker


VOLUME_GROUP = 'schains'
VOLUME = 'pytest_docker_lvm'
DRIVER = 'lvmpy'
SIZE = 200
IMAGE = 'pytest-ubuntu'
CONTAINER = 'pytest_lvmpy'

NUMBER_OF_CONTAINERS = 6
ITERATIONS = 2


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


def create_volumes():
    volumes = [
        client.volumes.create(name=f'test{i}', driver='lvmpy', driver_opts={})
        for i in range(NUMBER_OF_CONTAINERS)
    ]
    return volumes


def remove_volumes(volumes):
    for volume in volumes:
        volume.remove(force=True)


def create_containers():
    containers = [
        client.containers.run(image=IMAGE,
                              name=f'test{i}',
                              detach=True,
                              cap_add=['SYS_ADMIN'],
                              volumes={f'test{i}': {
                                  'bind': '/data', 'mode': 'rw'}
                              })
        for i in range(NUMBER_OF_CONTAINERS)
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
    containers = create_containers()
    time.sleep(15)
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

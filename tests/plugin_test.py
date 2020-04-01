import subprocess
import time
import docker


VOLUME_GROUP = 'schains'
VOLUME = 'pytest_docker_lvm'
DRIVER = 'lvmpy'
SIZE = 200
IMAGE = 'pytest-ubuntu'
CONTAINER = 'pytest_lvmpy'

NUMBER_OF_CONTAINERS = 6
ITERATIONS = 20


client = docker.client.from_env()


def test_create_remove(capfd):
    res = subprocess.run(['docker', 'volume', 'create', '-d', DRIVER,
                          '--opt', f'size={SIZE}M', '--name', VOLUME])
    assert res.returncode == 0
    captured = capfd.readouterr()

    res = subprocess.call(['docker', 'volume', 'ls'])
    captured = capfd.readouterr()
    lines = captured.out.split('\n')
    assert f'{DRIVER}               {VOLUME}' in lines

    res = subprocess.run(['docker', 'volume', 'remove', VOLUME])
    assert res.returncode == 0
    captured = capfd.readouterr()

    res = subprocess.call(['docker', 'volume', 'ls'])
    captured = capfd.readouterr()
    lines = captured.out.split('\n')
    assert f'{DRIVER}               {VOLUME}' not in lines


def test_create_remove_lsblk_info(capfd):
    res = subprocess.run(['docker', 'volume', 'create', '-d', DRIVER,
                          '--opt', f'size={SIZE}M', '--name', VOLUME])
    assert res.returncode == 0

    res = subprocess.call(['lsblk', '-l', '-o', 'name,size,type'])
    captured = capfd.readouterr()
    lines = list(filter(None, captured.out.split('\n')))
    expected = list(filter(None, lines[-1].split(' ')))
    assert expected == [f'{VOLUME_GROUP}-{VOLUME}', f'{SIZE}M', 'lvm']

    res = subprocess.run(['docker', 'volume', 'remove', VOLUME])
    assert res.returncode == 0

    res = subprocess.call(['lsblk', '-l', '-o', 'name'])
    captured = capfd.readouterr()
    lines = captured.out.split('\n')
    assert f'{VOLUME_GROUP}-{VOLUME}' not in lines


def test_create_docker_container(capfd):
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
    for v in volumes:
        print(v)


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


def test_containers_creation():
    create_volumes()
    containers = create_containers()
    time.sleep(15)
    remove_containers(containers)


def test_docker_system_restart():
    create_volumes()
    containers = create_containers()
    time.sleep(15)
    subprocess.run(['systemctl', 'restart', 'docker'])
    time.sleep(15)
    remove_containers(containers)

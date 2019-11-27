import subprocess

# from config import VOLUME_GROUP


VOLUME_GROUP = 'schains'
VOLUME = 'pytest_docker_lvm'
DRIVER = 'lvmpy'
SIZE = 200
IMAGE = 'pytest-ubuntu'
CONTAINER = 'pytest_lvmpy'


def test_create_remove(capfd):
    res = subprocess.run(['docker', 'volume', 'create', '-d', DRIVER,
                          '--opt', f'size={SIZE}M', '--name', VOLUME])
    assert res.returncode == 0
    captured = capfd.readouterr()

    res = subprocess.run(['docker', 'volume', 'ls'])
    assert res.returncode == 0
    captured = capfd.readouterr()
    lines = captured.out.split('\n')
    assert f'{DRIVER}               {VOLUME}' in lines

    res = subprocess.run(['docker', 'volume', 'remove', VOLUME])
    assert res.returncode == 0
    captured = capfd.readouterr()

    res = subprocess.run(['docker', 'volume', 'ls'])
    assert res.returncode == 0
    captured = capfd.readouterr()
    lines = captured.out.split('\n')
    assert f'{DRIVER}               {VOLUME}' not in lines


def test_create_remove_lsblk_info(capfd):
    res = subprocess.run(['docker', 'volume', 'create', '-d', DRIVER,
                          '--opt', f'size={SIZE}M', '--name', VOLUME])
    assert res.returncode == 0

    res = subprocess.run(['lsblk', '-l', '-o', 'name,size,type'])
    assert res.returncode == 0
    captured = capfd.readouterr()
    lines = list(filter(None, captured.out.split('\n')))
    expected = list(filter(None, lines[-1].split(' ')))
    assert expected == [f'{VOLUME_GROUP}-{VOLUME}', f'{SIZE}M', 'lvm']

    res = subprocess.run(['docker', 'volume', 'remove', VOLUME])
    assert res.returncode == 0

    res = subprocess.run(['lsblk', '-l', '-o', 'name'])
    assert res.returncode == 0
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
    res = subprocess.run(['docker', 'run', '-d', f'--name={CONTAINER}', '-v',
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

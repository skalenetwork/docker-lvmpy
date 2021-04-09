import os
import subprocess

import docker
import pytest

PHYSICAL_VOLUME = os.getenv('PHYSICAL_VOLUME')
VOLUME_GROUP = os.getenv('VOLUME_GROUP')

client = docker.from_env()


def run_install(block_device=PHYSICAL_VOLUME, volume_group=VOLUME_GROUP):
    res = subprocess.run(
        ['scripts/install.sh'],
        env={
            'PHYSICAL_VOLUME': block_device,
            'VOLUME_GROUP': volume_group
        }
    )
    if res.returncode != 0:
        print(res.stderr.decode('utf-8'))
        res.check_returncode()


def run_update(block_device=PHYSICAL_VOLUME, volume_group=VOLUME_GROUP):
    res = subprocess.run(
        ['scripts/update.sh'],
        env={
            'PHYSICAL_VOLUME': block_device,
            'VOLUME_GROUP': volume_group
        }
    )
    if res.returncode != 0:
        res.check_returncode()


def create_loop_back_device():
    res = subprocess.run(
        ['dd', 'if=/dev/zero', 'of=loopbackfile2.img', 'bs=400M', 'count=10'])
    res = subprocess.run(['losetup', '-fP', 'loopbackfile2.img'])
    res = subprocess.run(
        "losetup --list -a | grep loopbackfile2.img |  awk '{print $1}'",
        shell=True
    )
    bd = res.stdout.decode('utf-8')
    return bd


def remove_volumes_hard():
    res = subprocess.run(['lvremove', 'schains', '-y'])
    if res.returncode != 0:
        print(res.stderr.decode('utf-8'))
        res.check_returncode()


def test_install():
    run_install()
    run_update()
    client.volumes.create(
        name='test-volume',
        driver='lvmpy',
        driver_opts={'size': '200M'}
    )
    run_update()
    bd = create_loop_back_device()
    with pytest.raises(subprocess.CalledProcessError):
        run_update(block_device=bd)
    remove_volumes_hard()
    run_update(block_device=bd)

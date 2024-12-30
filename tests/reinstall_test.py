import os
import subprocess

import docker
import pytest

from src.install import setup

PHYSICAL_VOLUME = os.getenv('PHYSICAL_VOLUME')
VOLUME_GROUP = os.getenv('VOLUME_GROUP')

client = docker.from_env()


def run_install(block_device=PHYSICAL_VOLUME, volume_group=VOLUME_GROUP):
    setup(block_device=block_device, volume_group=volume_group)


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
    client.volumes.create(
        name='test-volume',
        driver='lvmpy',
        driver_opts={'size': '200M'}
    )
    run_install()
    bd = create_loop_back_device()
    with pytest.raises(subprocess.CalledProcessError):
        run_install(block_device=bd)
    remove_volumes_hard()
    run_install(block_device=bd)

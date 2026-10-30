import json
import logging
import os

from .cleanup import cleanup_volumes
from .config import (
    DOCKER_PLUGIN_CONFIG_PATH,
    DOCKER_PLUGIN_DIR,
    ETC_CONFIG_PATH,
    ETC_DIR,
    FILESTORAGE_MAPPING,
    LOG_DIR,
    PHYSICAL_VOLUME,
    PORT,
    SERVICE_DIR,
    SERVICE_EXEC_START,
    SERVICE_NAME,
    SERVICE_PATH,
    VOLUME_GROUP,
)
from .core import LvmPyError, run_cmd

logger = logging.getLogger(__name__)


def create_folders():
    logger.info('Creating folders')
    for path in (
        DOCKER_PLUGIN_DIR,
        ETC_DIR,
        LOG_DIR,
        SERVICE_DIR
    ):
        os.makedirs(path, exist_ok=True)


def stop_service(name=SERVICE_NAME):
    logger.info('Stopping service %s', name)
    run_cmd(['systemctl', 'daemon-reload'])
    try:
        run_cmd(['systemctl', 'stop', name])
        run_cmd(['systemctl', 'disable', name])
    except LvmPyError as e:
        logger.warning('Lvmpy service cannot be stopped %s', e)


def start_service(name=SERVICE_NAME):
    logger.info('Starting service %s', name)
    run_cmd(['systemctl', 'daemon-reload'])
    run_cmd(['systemctl', 'enable', name])
    run_cmd(['systemctl', 'start', name])


def load_btrfs_kernel_module():
    logger.info('Loading btrfs kernel module')
    run_cmd(['modprobe', 'btrfs'])


def generate_systemd_service_config(exec_start=SERVICE_EXEC_START):
    return f"""
[Unit]
Description=python lvm docker plugin
After=network.target
Before=docker.service

[Service]
Type=simple
ExecStart={exec_start}
EnvironmentFile={ETC_CONFIG_PATH}
Restart=on-failure
KillSignal=SIGINT

[Install]
WantedBy=multi-user.target
"""


def generate_plugin_config():
    return {
        'Name': 'lvmpy',
        'Description': 'A simple volume driver for lvm volumes written in python',
        'Addr': f'http://127.0.0.1:{PORT}'
    }


def generate_etc_config(block_device, volume_group, filestorage_mapping):
    return '\n'.join([
        f'PHYSICAL_VOLUME={block_device}',
        f'VOLUME_GROUP={volume_group}',
        f'FILESTORAGE_MAPPING={filestorage_mapping}'
    ])


def generate_config_files(
    block_device=PHYSICAL_VOLUME,
    volume_group=VOLUME_GROUP,
    filestorage_mapping=FILESTORAGE_MAPPING,
    exec_start=SERVICE_EXEC_START,
):
    logger.info('Generating config files. Exec start [%s]', exec_start)

    docker_plugin_config = generate_plugin_config()

    with open(DOCKER_PLUGIN_CONFIG_PATH, 'w') as docker_plugin_config_file:
        json.dump(docker_plugin_config, docker_plugin_config_file)

    service_config = generate_systemd_service_config(exec_start=exec_start)

    with open(SERVICE_PATH, 'w') as service_file:
        service_file.write(service_config)

    etc_config = generate_etc_config(
        block_device=block_device,
        volume_group=volume_group,
        filestorage_mapping=filestorage_mapping
    )
    with open(ETC_CONFIG_PATH, 'w') as etc_config_file:
        etc_config_file.write(etc_config)


def setup(
    block_device=PHYSICAL_VOLUME,
    volume_group=VOLUME_GROUP,
    filestorage_mapping=FILESTORAGE_MAPPING,
    exec_start=SERVICE_EXEC_START,
):
    stop_service()
    load_btrfs_kernel_module()
    cleanup_volumes(
        block_device=block_device,
        volume_group=volume_group
    )
    create_folders()
    generate_config_files(
        block_device=block_device,
        volume_group=volume_group,
        filestorage_mapping=filestorage_mapping,
        exec_start=exec_start,
    )
    start_service()


def main():
    print('Setting up docker-lvmpy server')
    setup()
    print('Setup of docker-lvmpy completed')


if __name__ == '__main__':
    main()

import os
from scripts.install import (
    create_folders,
    ensure_config_files
)


def test_ensure_config_files():
    create_folders()
    ensure_config_files(
        block_device='/dev/sdt',
        volume_group='schains',
        filestorage_mapping='/mnt/filestorage'
    )
    assert os.path.isfile('/etc/docker-lvmpy/lvm-environment')
    with open('/etc/docker-lvmpy/lvm-environment') as etc_file:
        etc_content = etc_file.read()
        assert etc_content == 'PHYSICAL_VOLUME=/dev/sdt\nVOLUME_GROUP=schains\nFILESTORAGE_MAPPING=/mnt/filestorage'  # noqa

    assert os.path.isfile('/etc/systemd/system/docker-lvmpy.service')
    with open('/etc/systemd/system/docker-lvmpy.service') as service_file:
        service_content = service_file.read()
        assert service_content == '\n[Unit]\nDescription=python lvm docker plugin\nConflicts=getty@tty1.service\nAfter=network.target\n\n[Service]\nType=simple\nWorkingDirectory=/opt/docker-lvmpy/\nExecStart=/usr/local/bin/lvmpy\nEnvironmentFile=/etc/docker-lvmpy/lvm-environment\nRestart=on-failure\nKillSignal=SIGINT\nStandardError=syslog\nNotifyAccess=all\n\n[Install]\nWantedBy=multi-user.target\n'  # noqa

    assert os.path.isfile('/etc/docker/plugins/lvmpy.json')
    with open('/etc/docker/plugins/lvmpy.json') as plugin_file:
        plugin_content = plugin_file.read()
        assert plugin_content == '{"Name": "lvmpy", "Description": "A simple volume driver for lvm volumes written in python", "Addr": "http://127.0.0.1:7373"}'  # noqa

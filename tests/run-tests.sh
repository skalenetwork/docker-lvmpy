#!/usr/bin/env bash
set -ea

export FILESTORAGE_MAPPING=$(realpath ./filestorage)

. tests/prepare.sh
export PYTHONPATH=${PYTHONPATH}:.

echo 'Installing docker-lvmpy'
VOLUME_GROUP=schains PHYSICAL_VOLUME=$BLOCK_DEVICE python3 -m src.install

cat /var/log/docker-lvmpy/lvmpy.log | tail -n 298
systemctl status docker-lvmpy

echo 'Running install tests'
VOLUME_GROUP=schains PHYSICAL_VOLUME=$BLOCK_DEVICE py.test --cov=. --ignore=tests/reinstall_test.py tests/

echo 'Updating docker-lvmpy'
VOLUME_GROUP=schains PHYSICAL_VOLUME=$BLOCK_DEVICE python3 -m src.install

echo 'Running update tests'
VOLUME_GROUP=schains PHYSICAL_VOLUME=$BLOCK_DEVICE py.test --cov=. --ignore=tests/reinstall_test.py tests/

BLOCK_DEVICE=$BLOCK_DEVICE tests/finalize.sh

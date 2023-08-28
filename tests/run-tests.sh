#!/usr/bin/env bash
set -ea

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PROJECT_DIR=$(dirname $DIR)

export FILESTORAGE_MAPPING=$(realpath ./filestorage)

export PYTHONPATH=${PYTHONPATH}:$PROJECT_DIR

. tests/prepare.sh

echo 'Installing docker-lvmpy'
VOLUME_GROUP=schains PHYSICAL_VOLUME=$BLOCK_DEVICE python3 -m src.install

journalctl -xe > all.log && cat all.log


# cat /var/log/docker-lvmpy/lvmpy.log | tail -n 298
# systemctl status docker-lvmpy
#
# echo 'Running install tests'
# VOLUME_GROUP=schains PHYSICAL_VOLUME=$BLOCK_DEVICE py.test --cov=. --ignore=tests/reinstall_test.py tests/
#
# echo 'Updating docker-lvmpy'
# VOLUME_GROUP=schains PHYSICAL_VOLUME=$BLOCK_DEVICE python3 -m src.install
#
# echo 'Running update tests'
# VOLUME_GROUP=schains PHYSICAL_VOLUME=$BLOCK_DEVICE py.test --cov=. --ignore=tests/reinstall_test.py tests/

BLOCK_DEVICE=$BLOCK_DEVICE tests/finalize.sh

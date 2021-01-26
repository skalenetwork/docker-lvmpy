#!/usr/bin/env bash
set -e

. tests/prepare.sh
export PYTHONPATH=${PYTHONPATH}:.

echo 'Installing docker-lvmpy'
VOLUME_GROUP=schains PHYSICAL_VOLUME=$BLOCK_DEVICE scripts/install.sh

echo 'Running install tests'
py.test tests/plugin_test.py
VOLUME_GROUP=schains PHYSICAL_VOLUME=$BLOCK_DEVICE py.test tests/core_test.py $@

echo 'Updating docker-lvmpy'
VOLUME_GROUP=schains PHYSICAL_VOLUME=$BLOCK_DEVICE scripts/update.sh

echo 'Running update tests'
py.test tests/plugin_test.py
VOLUME_GROUP=schains PHYSICAL_VOLUME=$BLOCK_DEVICE py.test tests/core_test.py $@

BLOCK_DEVICE=$BLOCK_DEVICE tests/finalize.sh

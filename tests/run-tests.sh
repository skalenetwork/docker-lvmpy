#!/usr/bin/env bash
set -e

. tests/prepare.sh
export PYTHONPATH=${PYTHONPATH}:.

echo 'Installing docker-lvmpy'
VOLUME_GROUP=schains PHYSICAL_VOLUME=$BLOCK_DEVICE scripts/install.sh

echo 'Running install tests'
VOLUME_GROUP=schains PHYSICAL_VOLUME=$BLOCK_DEVICE py.test --cov=. tests/

echo 'Updating docker-lvmpy'
VOLUME_GROUP=schains PHYSICAL_VOLUME=$BLOCK_DEVICE scripts/update.sh

echo 'Running update tests'
VOLUME_GROUP=schains PHYSICAL_VOLUME=$BLOCK_DEVICE py.test --cov=. tests/

BLOCK_DEVICE=$BLOCK_DEVICE tests/finalize.sh

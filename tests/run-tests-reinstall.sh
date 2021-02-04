#!/usr/bin/env bash
set -e

. tests/prepare.sh
export PYTHONPATH=${PYTHONPATH}:.

VOLUME_GROUP=schains PHYSICAL_VOLUME=$BLOCK_DEVICE py.test tests/reinstall_test.py $@

BLOCK_DEVICE=$BLOCK_DEVICE tests/finalize.sh

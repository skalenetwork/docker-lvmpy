set -e
source tests/prepare.sh
export PYTHONPATH=${PYTHONPATH}:.

py.test tests/plugin_test.py
VOLUME_GROUP=schains PHYSICAL_VOLUME=$BLOCK_DEVICE py.test tests/core_test.py $@

export BLOCK_DEVICE
tests/finalize.sh

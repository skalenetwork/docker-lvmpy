set -e
tests/prepare.sh
export PYTHONPATH=${PYTHONPATH}:.

py.test tests/plugin_test.py
if [ -z ${BLOCK_DEVICE} ]; then
    VOLUME_GROUP=schains PHYSICAL_VOLUME=/dev/loop0 py.test tests/core_test.py $@
else
    VOLUME_GROUP=schains PHYSICAL_VOLUME=${BLOCK_DEVICE} py.test tests/core_test.py $@
fi

tests/finalize.sh

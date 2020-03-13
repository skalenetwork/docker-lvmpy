tests/prepare.sh
export PYTHONPATH=${PYTHONPATH}:.

py.test tests/plugin_test.py
VOLUME_GROUP=schains PHYSICAL_VOLUME=/dev/loop0 py.test tests/core_test.py $@

tests/finalize.sh

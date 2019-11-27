export PYTHONPATH=${PYTHONPATH}:.

VOLUME_GROUP=test_schains PHYSICAL_VOLUME=/dev/sda py.test tests/ $@

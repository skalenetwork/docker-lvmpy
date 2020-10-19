#!/usr/bin/env bash
set -e

: "${PHYSICAL_VOLUME?Need to set PHYSICAL_VOLUME}"
: "${VOLUME_GROUP?Need to set VOLUME_GROUP}"


CODE_PATH=/opt/docker-lvmpy/
DOCKER_PLUGIN_CONFIG=/etc/docker/plugins/
SYSTEMD_CONFIG_PATH=/etc/systemd/system/
DRIVER_CONFIG=/etc/docker-lvmpy/
LOG_PATH=/var/log/docker-lvmpy

if [[ ! -d $CODE_PATH ]]; then
    mkdir -p $CODE_PATH
fi
if [[ ! -d $DOCKER_PLUGIN_CONFIG ]]; then
    mkdir -p $DOCKER_PLUGIN_CONFIG
fi
if [[ ! -d $SYSTEMD_CONFIG_PATH ]]; then
    mkdir -p $SYSTEMD_CONFIG_PATH
fi
if [[ ! -d $DRIVER_CONFIG ]]; then
    mkdir -p $DRIVER_CONFIG
fi
if [[ ! -d $LOG_PATH ]]; then
    mkdir -p $LOG_PATH
fi


systemctl daemon-reload
systemctl stop docker-lvmpy || true

cp docker/lvmpy.json $DOCKER_PLUGIN_CONFIG
cp systemd/docker-lvmpy.service $SYSTEMD_CONFIG_PATH
cp app.py core.py config.py requirements.txt $CODE_PATH
echo "PHYSICAL_VOLUME=$PHYSICAL_VOLUME" > $DRIVER_CONFIG/lvm-environment
echo "VOLUME_GROUP=$VOLUME_GROUP" >> $DRIVER_CONFIG/lvm-environment

cd $CODE_PATH
source venv/bin/activate
pip install -r requirements.txt

systemctl daemon-reload
systemctl enable docker-lvmpy
systemctl restart docker-lvmpy

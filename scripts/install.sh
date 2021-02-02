#!/usr/bin/env bash
set -e

: "${PHYSICAL_VOLUME?Need to set PHYSICAL_VOLUME}"
: "${VOLUME_GROUP?Need to set VOLUME_GROUP}"

CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
BASE_DIR="$(dirname "$CURRENT_DIR")"
CODE_PATH=/opt/docker-lvmpy/
DOCKER_PLUGIN_CONFIG=/etc/docker/plugins/
SYSTEMD_CONFIG_PATH=/etc/systemd/system/
DRIVER_CONFIG=/etc/docker-lvmpy/
LOG_PATH=/var/log/docker-lvmpy/

apt update
apt install auditd python3-dev python3-pip -y

echo 'Ensuring required directories ...'
mkdir -p $CODE_PATH $DOCKER_PLUGIN_CONFIG $DRIVER_CONFIG $LOG_PATH

systemctl daemon-reload
systemctl stop docker-lvmpy || true

echo 'Creating required files ...'
cd $BASE_DIR
cp docker/lvmpy.json $DOCKER_PLUGIN_CONFIG
cp systemd/docker-lvmpy.service $SYSTEMD_CONFIG_PATH
cp app.py core.py config.py cleanup.py healthcheck.py requirements.txt $CODE_PATH
echo "PHYSICAL_VOLUME=$PHYSICAL_VOLUME" > $DRIVER_CONFIG/lvm-environment
echo "VOLUME_GROUP=$VOLUME_GROUP" >> $DRIVER_CONFIG/lvm-environment

echo 'Installing requirements ...'
cd $CODE_PATH
pip3 install virtualenv
virtualenv --python=python3 venv
. venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=$CODE_PATH
echo PV $PHYSICAL_VOLUME : VG $VOLUME_GROUP
python cleanup.py $PHYSICAL_VOLUME $VOLUME_GROUP

echo 'Enabling service ...'
systemctl daemon-reload
systemctl enable docker-lvmpy
systemctl restart docker-lvmpy
echo 'Service is up'

python healthcheck.py $VOLUME_GROUP
echo 'Done'

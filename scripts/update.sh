set -e

CODE_PATH=/opt/docker-lvmpy/
DOCKER_PLUGIN_CONFIG=/etc/docker/plugins/
SYSTEMD_CONFIG_PATH=/etc/systemd/system/
DRIVER_CONFIG=/etc/docker-lvmpy/

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

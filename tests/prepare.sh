echo 'Creating loopback block device'
dd if=/dev/zero of=loopbackfile.img bs=1000M count=10
losetup -fP loopbackfile.img
losetup -a
echo 'Block device created from file'
echo 'Installing docker-lvmpy'
VOLUME_GROUP=schains PHYSICAL_VOLUME=/dev/loop0 scripts/install.sh

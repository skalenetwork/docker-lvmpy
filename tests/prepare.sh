if [ ${START_OPERATION} == 'update']; then
    echo 'Updating docker-lvmpy'
    VOLUME_GROUP=schains PHYSICAL_VOLUME=$BLOCK_DEVICE scripts/update.sh
else
    if [ -z ${BLOCK_DEVICE} ]; then
        echo 'Creating loopback block device'
        dd if=/dev/zero of=loopbackfile.img bs=400M count=10
        losetup -fP loopbackfile.img
        losetup -a
        echo 'Block device created from file'
        BLOCK_DEVICE="$(losetup --list -a | grep loopbackfile.img |  awk '{print $1}')"
        export BLOCK_DEVICE
    fi
    echo 'Installing docker-lvmpy'
    VOLUME_GROUP=schains PHYSICAL_VOLUME=$BLOCK_DEVICE scripts/install.sh
fi

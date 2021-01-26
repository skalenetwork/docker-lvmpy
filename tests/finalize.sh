#!/bin/bash
set -e

echo "Disable docker-lvmpy service"
systemctl disable docker-lvmpy
echo "Removing all volumes from schain volume group"
lvremove schains --yes
echo "Removing volume group schain"
vgremove schains
echo "Cleaning up $BLOCK_DEVICE"
pvremove $BLOCK_DEVICE
echo "Unmount $BLOCK_DEVICE"
umount -q $BLOCK_DEVICE

BLOCK_DEVICE="$(losetup --list -a | grep loopbackfile.img |  awk '{print $1}')"
if [ ! -z ${BLOCK_DEVICE} ]; then
    echo "Removing $BLOCK_DEVICE"
    losetup -d $BLOCK_DEVICE
    echo 'Removing loopbackfile.img'
    rm -f loopbackfile.img
fi

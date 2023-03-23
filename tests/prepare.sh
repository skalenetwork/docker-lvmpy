#!/usr/bin/env bash
set -ea

if [ -z ${BLOCK_DEVICE} ]; then
    echo 'Creating loopback block device'
    dd if=/dev/zero of=loopbackfile.img bs=400M count=10
    losetup -fP loopbackfile.img
    echo 'Block device created from file'
    BLOCK_DEVICE="$(losetup --list -a | grep loopbackfile.img |  awk '{print $1}')"
    export BLOCK_DEVICE
fi

mkdir ${FILESTORAGE_MAPPING} || true
systemctl stop docker-lvmpy || true

scripts/build.sh test test
cp dist/lvmpy-test-Linux-x86_64 /usr/local/bin/lvmpy
chmod +x /usr/local/bin/lvmpy

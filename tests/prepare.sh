#!/usr/bin/env bash
set -e

if [ -z ${BLOCK_DEVICE} ]; then
    echo 'Creating loopback block device'
    dd if=/dev/zero of=loopbackfile.img bs=400M count=10
    losetup -fP loopbackfile.img
    echo 'Block device created from file'
    BLOCK_DEVICE="$(losetup --list -a | grep loopbackfile.img |  awk '{print $1}')"
    export BLOCK_DEVICE
fi

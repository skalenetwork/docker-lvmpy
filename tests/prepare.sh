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

printf '#!/bin/sh\ncd "%s" && exec .venv/bin/python -m src.main\n' "$PWD" > /usr/local/bin/lvmpy
chmod +x /usr/local/bin/lvmpy

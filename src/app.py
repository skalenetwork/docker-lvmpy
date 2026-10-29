#   -*- coding: utf-8 -*-
#
#   This file is part of docker-lvmpy
#
#   Copyright (C) 2019-Present SKALE Labs
#
#   docker-lvmpy is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   docker-lvmpy is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with docker-lvmpy.  If not, see <https://www.gnu.org/licenses/>

import json
import logging
import time

from flask import Flask, Response, g, request

from .config import PHYSICAL_VOLUME, PORT
from .core import LvmPyError, ensure_volume_group, get_block_device_size
from .core import create as create_volume
from .core import get as get_volume
from .core import mount as mount_volume
from .core import path as volume_path
from .core import remove as remove_volume
from .core import unmount as unmount_volume
from .core import volumes as list_volumes
from .log import init_logging

logger = logging.getLogger(__name__)


app = Flask(__name__)

DEFAULT_SIZE = '256m'


def response(data: dict, code: int) -> Response:
    return Response(response=json.dumps(data),
                    status=code, mimetype='application/json')


def ok(out_data: dict = None):
    if out_data is None:
        out_data = {}
    return response({**out_data, 'Err': ''}, 200)


def error(err, code: int = 400):
    return response({'Err': err}, code)


@app.before_request
def save_time():
    g.start_time = time.time()


@app.before_request
def ensure_vg():
    ensure_volume_group()


@app.errorhandler(500)
def handle_500(e):
    logger.error(f'Request failed with 500 code, err=[{e}]')
    return error(err='InternalServerError', code=500)


@app.teardown_request
def log_elapsed(_exc: BaseException | None) -> None:
    elapsed = round(time.time() - g.start_time, 2)
    logger.info(f'Request elapsed time: {elapsed}s')


@app.route('/')
def index():
    return ok()


@app.route('/physical-volume-size')
def physical_volume_size():
    data = request.get_json(force=True)
    name = data.get('Name') or PHYSICAL_VOLUME
    try:
        return ok({
            'Name': name,
            'Size': get_block_device_size(name)
        })
    except LvmPyError as e:
        logger.info('Block device size request failed %s', e)
        return error('No such volume', code=400)


@app.route('/Plugin.Activate', methods=['POST'])
def activate():
    return ok({"Implements": ["VolumeDriver"]})


@app.route('/VolumeDriver.Create', methods=['POST'])
def create():
    data = request.get_json(force=True)
    name = data['Name']
    options = data.get('Opts', {})
    if options is None:
        options = {}
    size_str = options.get('size') or DEFAULT_SIZE
    logger.info(f'Create volume options={options}, size_str={size_str}')

    create_volume(name, size_str)
    return ok()


@app.route('/VolumeDriver.Remove', methods=['POST'])
def remove():
    data = request.get_json(force=True)
    name = data['Name']
    remove_volume(name)
    return ok()


@app.route('/VolumeDriver.Mount', methods=['POST'])
def mount():
    data = request.get_json(force=True)
    name = data['Name']
    mountpoint = mount_volume(name)
    return ok(out_data={'Mountpoint': mountpoint})


@app.route('/VolumeDriver.Unmount', methods=['POST'])
def unmount():
    data = request.get_json(force=True)
    name = data['Name']
    unmount_volume(name)
    return ok()


@app.route('/VolumeDriver.Path', methods=['POST'])
def path():
    data = request.get_json(force=True)
    name = data['Name']
    mountpoint = volume_path(name)

    return ok(out_data={'Mountpoint': mountpoint})


@app.route('/VolumeDriver.Get', methods=['POST'])
def get():
    data = request.get_json(force=True)
    name = data['Name']
    name = get_volume(name)
    if name is None:
        return error('No such volume')

    return ok({
        "Volume": {
            "Name": name,
            "Status": {},
        },
        "Err": "",
    })


@app.route('/VolumeDriver.List', methods=['POST'])
def volumes_list():
    volumes = list_volumes()
    volumes_data = [{'Name': volume, 'Status': {}} for volume in volumes]
    data = {'Volumes': volumes_data, 'Err': ''}
    return ok(out_data=data)


@app.route('/VolumeDriver.Capabilities', methods=['POST'])
def capabilites():
    return ok({
        "Capabilities": {
            "Scope": "global"
        }
    })


def run():
    init_logging()
    app.run(host='127.0.0.1', port=PORT)

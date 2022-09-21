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
import warning
from logging import StreamHandler
from logging.handlers import RotatingFileHandler

from flask import Flask, Response, g, request
from werkzeug.exceptions import InternalServerError

from core import (
    create as create_volume,
    ensure_volume_group,
    get as get_volume,
    get_block_device_size,
    is_configured,
    mount as mount_volume,
    path as volume_path,
    remove as remove_volume,
    unmount as unmount_volume,
    volumes as list_volumes
)
from config import (
    DEFAULT_CONFIG_FILE,
    LOG_BACKUP_COUNT,
    LOG_FILE_SIZE_BYTES,
    LOG_FORMAT,
    LOG_PATH,
    PHYSICAL_VOLUME
)


logging.basicConfig(
    format=LOG_FORMAT,
    handlers=[
        StreamHandler(),
        RotatingFileHandler(
            LOG_PATH, maxBytes=LOG_FILE_SIZE_BYTES,
            backupCount=LOG_BACKUP_COUNT
        )
    ],
    level=logging.INFO
)

logger = logging.getLogger(__name__)

app = Flask(__name__)

HOST = '127.0.0.1'
PORT = 7373
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


@app.errorhandler(InternalServerError)
def handle_500(e):
    logger.error(f'Request failed with 500 code, err={e}')
    return error(err=e.args[0], code=500)


@app.before_first_request
def enusre_configuration():
    while not is_configured():
        warning.warn(
            'Config is incorrect! Waiting for the valid configuration in %s',
            DEFAULT_CONFIG_FILE
        )
    ensure_volume_group()


@app.before_request
def save_time():
    g.start_time = time.time()


@app.teardown_request
def log_elapsed(response):
    elapsed = round(time.time() - g.start_time, 2)
    logger.info(f'Request elapsed time: {elapsed}s')
    return response


@app.route('/')
def index():
    return ok()


@app.route('/physical-volume-size')
def physical_volume_size():
    data = request.get_json(force=True)
    name = data.get('Name') or PHYSICAL_VOLUME
    return ok({
        'Name': name,
        'Size': get_block_device_size(name)
    })


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
    is_schain = data.get('is_schain', True)
    mountpoint = mount_volume(name, is_schain)
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


def main():
    app.run(host=HOST, port=PORT)


if __name__ == '__main__':
    main()

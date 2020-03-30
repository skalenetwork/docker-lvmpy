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

from flask import Flask, request, Response

from core import (
    ensure_physical_volume,
    ensure_volume_group,
    create as create_volume,
    remove as remove_volume,
    mount as mount_volume,
    unmount as unmount_volume,
    path as volume_path,
    get as get_volume,
    volumes as list_volumes,
    LvmPyError
)
from config import LOG_PATH


logging.basicConfig(
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    handlers=[logging.StreamHandler(),
              logging.FileHandler(LOG_PATH)],
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

HOST = '0.0.0.0'
PORT = 7373
DEFAULT_SIZE = '256m'


def response(data, code):
    return Response(response=json.dumps(data),
                    status=code, mimetype='application/json')


def ok(out_data={}):
    return response({**out_data, 'Err': ''}, 200)


def error(err, code=400):
    return response({'Err': err}, code)


@app.before_first_request
def enusre_lvm():
    ensure_physical_volume()
    ensure_volume_group()


@app.route('/')
def index():
    return ok()


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

    try:
        create_volume(name, size_str)
    except LvmPyError:
        return error('Create operation failed. Recheck input data')
    return ok()


@app.route('/VolumeDriver.Remove', methods=['POST'])
def remove():
    data = request.get_json(force=True)
    name = data['Name']
    try:
        remove_volume(name)
    except LvmPyError:
        return error('Remove operation failed. Recheck input data')
    return ok()


@app.route('/VolumeDriver.Mount', methods=['POST'])
def mount():
    data = request.get_json(force=True)
    name = data['Name']
    try:
        mountpoint = mount_volume(name)
    except LvmPyError:
        return error('Mount operation failed. Recheck input data')
    return ok(out_data={'Mountpoint': mountpoint})


@app.route('/VolumeDriver.Unmount', methods=['POST'])
def unmount():
    data = request.get_json(force=True)
    name = data['Name']
    try:
        unmount_volume(name)
    except LvmPyError:
        return error('Unmount operation failed. Recheck input data')

    return ok()


@app.route('/VolumeDriver.Path', methods=['POST'])
def path():
    data = request.get_json(force=True)
    name = data['Name']
    try:
        mountpoint = volume_path(name)
    except LvmPyError:
        return error('Path operation failed. Recheck input data')

    return ok(out_data={'Mountpoint': mountpoint})


@app.route('/VolumeDriver.Get', methods=['POST'])
def get():
    data = request.get_json(force=True)
    name = data['Name']
    try:
        name = get_volume(name)
        if name is None:
            return error('No such volume')
    except LvmPyError:
        return error('Get operation failed. Recheck input data')

    return ok({
        "Volume": {
            "Name": name,
            "Status": {},
        },
        "Err": "",
    })


@app.route('/VolumeDriver.List', methods=['POST'])
def volumes_list():
    try:
        volumes = list_volumes()
    except LvmPyError:
        return error('List operation failed. Recheck input data')

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

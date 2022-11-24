import pytest
from config import PHYSICAL_VOLUME, VOLUME_GROUP
from core import (
    ensure_physical_volume, ensure_volume_group,
    remove_physical_volume, remove_volume_group
)


@pytest.fixture(scope='module')
def pv():
    try:
        ensure_physical_volume(PHYSICAL_VOLUME)
        yield PHYSICAL_VOLUME
    finally:
        remove_physical_volume(PHYSICAL_VOLUME)


@pytest.fixture(scope='module')
def vg(pv):
    try:
        ensure_volume_group(VOLUME_GROUP, pv)
        yield VOLUME_GROUP
    finally:
        remove_volume_group(VOLUME_GROUP)

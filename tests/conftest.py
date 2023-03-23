import pytest
from src.config import PHYSICAL_VOLUME, VOLUME_GROUP
from src.core import (
    ensure_physical_volume, ensure_volume_group,
    remove, remove_physical_volume, remove_volume_group,
    volumes
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
        vols = volumes(vg=VOLUME_GROUP)
        for v in vols:
            remove(v)
        remove_volume_group(VOLUME_GROUP)

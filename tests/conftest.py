import pytest
from core import ensure_physical_volume, ensure_volume_group


@pytest.fixture(scope='module')
def vg():
    ensure_physical_volume()
    ensure_volume_group()
    yield

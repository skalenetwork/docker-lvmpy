import logging
import sys

from .core import (
    LvmPyError,
    physical_volume_from_group,
    remove_physical_volume,
    remove_volume_group,
    volume_groups,
    volumes,
)

logger = logging.getLogger(__name__)


def is_lvmpy_environment_valid(block_device: str, volume_group: str) -> bool:
    pv = physical_volume_from_group(volume_group)
    lvs = volumes(volume_group)
    return pv == block_device or lvs == []


def is_cleanup_needed(block_device: str, volume_group: str) -> bool:
    if volume_group not in volume_groups():
        return False
    if physical_volume_from_group(volume_group) == block_device:
        return False
    return True


def cleanup_lvmpy_aritifacts(volume_group: str) -> None:
    pv = physical_volume_from_group(volume_group)
    remove_volume_group(volume_group)
    remove_physical_volume(pv)


def cleanup_volumes(block_device, volume_group) -> None:
    logger.info('Cleaning up volumes')
    if not is_lvmpy_environment_valid(block_device, volume_group):
        print(
            'Lvmpy cannot be created. '
            f'Volume group {volume_group} exists with volumes',
            file=sys.stderr
        )
        sys.exit(1)
    if is_cleanup_needed(block_device, volume_group):
        print('Cleaning lvmpy artifacts ...')
        try:
            cleanup_lvmpy_aritifacts(volume_group)
        except LvmPyError as err:
            print(f'Cleaning failed with error: {err}')
            sys.exit(2)
    print('Lvmpy cleanup finished')

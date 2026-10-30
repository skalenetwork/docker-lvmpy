import logging
import time

import requests

from .config import VOLUME_LIST_ROUTE
from .core import run_cmd
from .log import init_logging

logger = logging.getLogger(__name__)


class EndpointCheck:
    def __init__(self, url: str = VOLUME_LIST_ROUTE):
        self.url = url

    def run(self) -> bool:
        retries = 5
        res, code, err = None, None, None
        for attempt in range(retries):
            logger.debug(f'Checking lvmpy endpoint. Attempt: {attempt}')
            try:
                res = requests.post(self.url, timeout=10)
                code = res.status_code
            except Exception as e:
                err = e
                logger.exception('Error during checking lvmpy health')
            else:
                break
            time.sleep(2)

        if code == 200:
            logger.info('Lvmpy is healthy %s', res)
            return True
        else:
            logger.error('Lvmpy is not healthy %s %s', code, err)
            return False


def heal_service(ec: EndpointCheck | None = None) -> bool:
    init_logging()
    ec = ec or EndpointCheck()
    if not ec.run():
        print('Lvmpy is ill. Restarting the service')
        res = run_cmd(['systemctl', 'restart', 'docker-lvmpy'])
        print(f'Lvmpy restart command result: {res}')
        print('Lvmpy has been restarted')
        return True
    return False

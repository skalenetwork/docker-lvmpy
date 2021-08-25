import logging

import crontab

from config import CRON_LOG_PATH


logger = logging.getLogger(__name__)


def init_cron():
    logger.info('Ensuring cron job for healing lvmpy')
    cron_line = f'/opt/docker-lvmpy/venv/bin/python -c "import healthcheck; healthcheck.heal_service()" >> {CRON_LOG_PATH}'  # noqa
    with crontab.CronTab(user='root') as c:
        if cron_line not in [c.command for c in c]:
            job = c.new(
                command=cron_line
            )
            job.minute.every(1)


if __name__ == '__main__':
    init_cron()

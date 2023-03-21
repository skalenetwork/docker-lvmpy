import logging

import crontab

from .config import CRON_LOG_PATH, CRON_SCHEDULE_MINUTES


logger = logging.getLogger(__name__)


def init_cron():
    logger.info('Ensuring cron job for healing lvmpy')
    cron_line = f'cd /opt/docker-lvmpy && venv/bin/python -c "import health; health.heal_service()" >> {CRON_LOG_PATH} 2>&1'  # noqa
    with crontab.CronTab(user='root') as c:
        if cron_line not in [c.command for c in c]:
            job = c.new(
                command=cron_line
            )
            job.minute.every(CRON_SCHEDULE_MINUTES)


if __name__ == '__main__':
    init_cron()

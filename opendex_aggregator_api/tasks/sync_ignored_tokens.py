import logging
from datetime import datetime, timedelta
from time import sleep

from opendex_aggregator_api.ignored_tokens import IGNORED_TOKENS
from opendex_aggregator_api.services import mvx_index
from opendex_aggregator_api.utils.redis_utils import redis_lock_and_do

_must_stop = False


def stop():
    global _must_stop
    _must_stop = True


def loop():
    logging.info('Starting ignored tokens sync')

    delta = timedelta(minutes=5)
    start = datetime.min
    while not _must_stop:
        now = datetime.now()
        if now - start > delta:

            redis_lock_and_do('sync_ignored_tokens',
                              lambda: _sync_ignored_tokens(),
                              task_ttl=timedelta(seconds=10),
                              lock_ttl=timedelta(seconds=60))

            logging.info(f'Ignored tokens synced '
                         f'@ {datetime.utcnow().isoformat()}')
            start = now

        sleep(1)

    logging.info('Stopping ignored tokens sync')


def _sync_ignored_tokens():
    ignored_tokens = mvx_index.fetch_paused_tokens()

    IGNORED_TOKENS.clear()
    IGNORED_TOKENS.extend(ignored_tokens)

    logging.info(f'Ignored tokens: {IGNORED_TOKENS}')

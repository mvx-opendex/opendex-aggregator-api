import logging
import os
import threading

from fastapi import FastAPI

from jex_dex_aggregator_api.tasks import sync_dex_aggregator

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(process)d] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

THREAD_SYNC_DEX_AGGREGATOR = threading.Thread(
    target=sync_dex_aggregator.sync_dex_aggregator_pools)


async def lifespan(app: FastAPI):
    no_task = os.environ.get('NO_TASKS', False)
    if not no_task:

        THREAD_SYNC_DEX_AGGREGATOR.start()

    yield

    if not no_task:
        sync_dex_aggregator.stop()


app = FastAPI(lifespan=lifespan)


@app.get('/ready')
def read_root():
    ready = sync_dex_aggregator.is_ready()

    return {'ready': ready}

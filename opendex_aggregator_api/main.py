import logging
import os
import threading

from fastapi import FastAPI

from opendex_aggregator_api.routers import evaluations, routes
from opendex_aggregator_api.tasks import sync_pools

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(process)d] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

THREAD_SYNC_DEX_AGGREGATOR = threading.Thread(target=sync_pools.loop)


async def lifespan(app: FastAPI):
    no_task = os.environ.get('NO_TASKS', False)
    if not no_task:

        THREAD_SYNC_DEX_AGGREGATOR.start()

    try:
        yield
    except:
        pass

    if not no_task:
        sync_pools.stop()


app = FastAPI(lifespan=lifespan)
app.include_router(evaluations.router)
app.include_router(routes.router)


@app.get('/ready')
def read_root():
    ready = sync_pools.is_ready()

    return {'ready': ready}

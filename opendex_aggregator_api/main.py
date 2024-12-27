import logging
import os
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from opendex_aggregator_api.routers import (evaluations, multi_eval, routes,
                                            tokens)
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(evaluations.router)
app.include_router(multi_eval.router)
app.include_router(routes.router)
app.include_router(tokens.router)


@app.get('/ready')
def read_root():
    ready = sync_pools.is_ready()

    return {'ready': ready}

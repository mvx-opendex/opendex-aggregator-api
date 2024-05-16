
import base64
import pickle
from datetime import timedelta
from typing import List

from jex_dex_aggregator_api.pools.model import SwapPool
from jex_dex_aggregator_api.pools.pools import AbstractPool
from jex_dex_aggregator_api.utils.redis_utils import redis_get, redis_set

_SWAP_POOLS: List[SwapPool] = []


def get_swap_pools() -> List[SwapPool]:
    return _SWAP_POOLS


def set_swap_pools(pools: List[SwapPool]):
    global _SWAP_POOLS
    _SWAP_POOLS = pools


def get_dex_aggregator_pool(sc_address: str, token_in: str, token_out: str) -> AbstractPool:
    key = f'dex-agg-pool_{sc_address}_{token_in}_{token_out}'

    return redis_get(key,
                     lambda serialized: pickle.loads(base64.b64decode(serialized)))


def set_dex_aggregator_pool(sc_address: str, token_in: str, token_out: str, pool: AbstractPool):
    key = f'dex-agg-pool_{sc_address}_{token_in}_{token_out}'

    redis_set(key,
              base64.b64encode(pickle.dumps(pool)),
              timedelta(seconds=60))

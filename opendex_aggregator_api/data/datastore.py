
import base64
import json
import pickle
from datetime import timedelta
from typing import List, Optional

from opendex_aggregator_api.data.model import Esdt
from opendex_aggregator_api.pools.model import SwapPool
from opendex_aggregator_api.pools.pools import AbstractPool
from opendex_aggregator_api.utils.redis_utils import redis_get, redis_set


def get_swap_pools() -> List[SwapPool]:
    return redis_get('swap_pools',
                     lambda json_: [SwapPool.model_validate_json(x) for x in json_])


def set_swap_pools(pools: List[SwapPool]):
    redis_set('swap_pools',
              [p.model_dump_json() for p in pools],
              timedelta(hours=1))


def get_dex_aggregator_pool(sc_address: str, token_in: str, token_out: str) -> AbstractPool:
    key = f'pool_{sc_address}_{token_in}_{token_out}'

    return redis_get(key,
                     lambda serialized: pickle.loads(base64.b64decode(serialized)))


def set_dex_aggregator_pool(sc_address: str, token_in: str, token_out: str, pool: AbstractPool):
    key = f'pool_{sc_address}_{token_in}_{token_out}'

    redis_set(key,
              base64.b64encode(pickle.dumps(pool)),
              timedelta(seconds=60))


def get_tokens() -> Optional[List[Esdt]]:
    return redis_get('tokens',
                     lambda json_: [Esdt.model_validate(x) for x in json_])


def set_tokens(tokens: List[Esdt]):
    redis_set('tokens',
              tokens,
              timedelta(hours=6))

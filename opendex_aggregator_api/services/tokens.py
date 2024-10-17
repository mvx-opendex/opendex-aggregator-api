import logging
import random
from datetime import timedelta
from time import sleep
from typing import List, Optional

from opendex_aggregator_api.data.model import Esdt
from opendex_aggregator_api.services.externals import sync_sc_query
from opendex_aggregator_api.utils.convert import hex2str
from opendex_aggregator_api.utils.env import sc_address_system_tokens
from opendex_aggregator_api.utils.redis_utils import redis_get_or_set_cache

JEX_IDENTIFIER = 'JEX-9040ca'
USDC_IDENTIFIER = 'USDC-c76f1f'
WEGLD_IDENTIFIER = 'WEGLD-bd4d79'

_LOCAL_CACHE = {}


def token_from_identifier(token_identifier) -> Optional[Esdt]:
    if token_identifier in _LOCAL_CACHE:
        return _LOCAL_CACHE[token_identifier]
    else:
        return None


def get_or_fetch_token(identifier: str,
                       is_lp_token: bool = False,
                       exchange: Optional[str] = None) -> Esdt:
    token = token_from_identifier(identifier)

    if token is None:
        token = fetch_token(identifier,
                            is_lp_token,
                            exchange,
                            cooldown_fetch=timedelta(seconds=0.25))

    return token


def fetch_token(identifier: str,
                is_lp_token: bool,
                exchange: Optional[str],
                cooldown_fetch: timedelta) -> Esdt:

    def _do():
        logging.info(f'Fetching {identifier} token info from gateway')

        resp = sync_sc_query(sc_address=sc_address_system_tokens(),
                             function='getTokenProperties',
                             args=[identifier],
                             use_public_gw=True)

        decimals = hex2str(resp[5][24:])

        sleep(cooldown_fetch.total_seconds())

        return Esdt(decimals=decimals,
                    identifier=identifier,
                    name=identifier.split('-')[0],
                    is_lp_token=is_lp_token,
                    exchange=exchange)

    cache_key = f'esdt_{identifier}'
    cache_ttl = timedelta(hours=120 + random.randint(0, 72))
    return redis_get_or_set_cache(cache_key,
                                  cache_ttl,
                                  _do,
                                  lambda json_: Esdt.model_validate(json_))

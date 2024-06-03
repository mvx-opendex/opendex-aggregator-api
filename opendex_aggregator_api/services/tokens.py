import logging
from datetime import timedelta
import random
from typing import List, Optional

from opendex_aggregator_api.data.model import Esdt
from opendex_aggregator_api.services.externals import sync_sc_query
from opendex_aggregator_api.utils.convert import hex2str
from opendex_aggregator_api.utils.env import sc_address_system_tokens
from opendex_aggregator_api.utils.redis_utils import redis_get_or_set_cache

TOKENS: List[Esdt] = []

JEX_IDENTIFIER = 'JEX-9040ca'
USDC_IDENTIFIER = 'USDC-c76f1f'
WEGLD_IDENTIFIER = 'WEGLD-bd4d79'


def token_from_identifier(token_identifier) -> Optional[Esdt]:
    return next((x for x in TOKENS
                 if x.identifier == token_identifier), None)


def get_or_fetch_token(identifier: str) -> Esdt:
    token = token_from_identifier(identifier)

    if token is None:
        token = fetch_token(identifier)
        TOKENS.append(token)

    return token


def fetch_token(identifier: str) -> Esdt:

    def _do():
        logging.info(f'Fetching {identifier} token info from gateway')

        resp = sync_sc_query(sc_address=sc_address_system_tokens(),
                             function='getTokenProperties',
                             args=[identifier])

        decimals = hex2str(resp[5][24:])

        return Esdt(decimals=decimals,
                    identifier=identifier,
                    name=identifier.split('-')[0],
                    is_lp_token=None)

    cache_key = f'esdt_{identifier}'
    cache_ttl = timedelta(hours=120 + random.randint(0, 72))
    return redis_get_or_set_cache(cache_key,
                                  cache_ttl,
                                  _do,
                                  lambda json_: Esdt.model_validate(json_))

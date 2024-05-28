
import logging
from datetime import timedelta
from typing import List, Optional

from opendex_aggregator_api.data.model import Esdt
from opendex_aggregator_api.services.externals import call_mvx_api
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
        logging.info(f'Fetching token {identifier} from API')
        path = f"/tokens/{identifier}"

        resp = call_mvx_api(path)

        return Esdt(decimals=resp['decimals'],
                    identifier=resp['identifier'],
                    name=resp['ticker'].split('-')[0],
                    is_lp_token=None)

    cache_key = f'esdt_{identifier}'

    token = redis_get_or_set_cache(cache_key,
                                   timedelta(days=7),
                                   _do,
                                   lambda json_: Esdt.model_validate(json_))

    return token

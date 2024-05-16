
import base64
import logging
from typing import Any, List, Optional

import aiohttp
import requests
from multiversx_sdk_core.serializer import args_to_strings

from jex_dex_aggregator_api.utils.env import mvx_api_url


def call_mvx_api(path: str):
    logging.info(f'Calling MvX API: {path}')

    resp = requests.get(mvx_api_url()+path)
    if resp.status_code in [200, 204]:
        return resp.json()

    logging.error(f'Error [{resp.status_code}] calling MvX API')
    logging.error(f'path={path}')

    raise Exception(f'Error calling MvX API: HTTP error [{resp.status_code}]')


async def async_sc_query(http_client: aiohttp.ClientSession,
                         sc_address: str,
                         function: str,
                         args: List[Any] = []) -> Optional[List[str]]:

    prepared_args = args_to_strings(args)

    body = {
        "scAddress": sc_address,
        "funcName": function,
        "value": "0",
        "args": prepared_args
    }

    try:
        async with http_client.post('/vm-values/query', json=body) as resp:
            json_ = await resp.json()

            try:
                code = json_['code']

                if code == 'successful':
                    rdata = json_['data']['data']['returnData']
                    if rdata is None:
                        res = None
                    else:
                        res = [base64.b64decode(x).hex() for x in rdata]
                else:
                    res = None
            except:
                logging.error('Error during query')
                res = None

            return res
    except Exception as e:
        logging.exception('Error during query')
        logging.error(
            f'Error during query - parameters :: {sc_address} :: {function} :: {args}')
        return None

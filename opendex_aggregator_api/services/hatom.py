import asyncio
import logging
from typing import Optional, Union

import aiohttp

from opendex_aggregator_api.services.externals import async_sc_query
from opendex_aggregator_api.utils import env
from opendex_aggregator_api.utils.convert import hex2dec

PRECISION = 10**18


async def fetch_egld_and_usdc_prices() -> Union[Optional[float], Optional[float]]:
    logging.info('Fetching USD prices of EGLD and USD from Hatom price feed')

    sc_address = env.sc_address_hatom_price_feed()

    if not sc_address:
        return [None, None]

    async with aiohttp.ClientSession(env.mvx_gateway_url()) as http_client:
        tasks = [async_sc_query(http_client,
                                sc_address=sc_address,
                                function='latestPriceFeed',
                                args=[id, 'USD'])
                 for id in ['EGLD', 'USDC']]

        [egld_result, usdc_result] = await asyncio.gather(*tasks)

        egld_usd_price = hex2dec(
            egld_result[4]) / PRECISION if egld_result else None

        usdc_usd_price = hex2dec(
            usdc_result[4]) / PRECISION if usdc_result else None

        logging.info(f'EGLD price from Hatom: {egld_usd_price}')
        logging.info(f'USDC price from Hatom: {usdc_usd_price}')

        return [egld_usd_price, usdc_usd_price]

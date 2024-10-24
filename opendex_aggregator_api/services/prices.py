from typing import List, Optional, Set

import opendex_aggregator_api.services.hatom as hatom_svc
from opendex_aggregator_api.data.model import Esdt, ExchangeRate
from opendex_aggregator_api.services.tokens import (USDC_IDENTIFIER,
                                                    WEGLD_IDENTIFIER)


async def fill_tokens_usd_price(tokens: Set[Esdt],
                                rates: Set[ExchangeRate]) -> List[Esdt]:
    [wegld_usd_price, usdc_usd_price] = await hatom_svc.fetch_egld_and_usdc_prices()

    return [_fill_token_usd_price(t,
                                  rates,
                                  wegld_usd_price,
                                  usdc_usd_price)
            for t in tokens]


def _fill_token_usd_price(token: Esdt,
                          rates: List[ExchangeRate],
                          wegld_usd_price: Optional[float],
                          usdc_usd_price: Optional[float]) -> Esdt:
    if token.identifier == WEGLD_IDENTIFIER:
        token.usd_price = wegld_usd_price
    elif token.identifier == USDC_IDENTIFIER:
        token.usd_price = usdc_usd_price
    else:
        sorted_rates: List[ExchangeRate] = sorted((r for r in rates
                                                   if r.base_token_liquidity > 0
                                                   and r.base_token_id == token.identifier
                                                   and r.quote_token_id in [WEGLD_IDENTIFIER, USDC_IDENTIFIER]),
                                                  key=lambda x: x.base_token_liquidity,
                                                  reverse=True)

        for rate in sorted_rates:
            if rate.quote_token_id == WEGLD_IDENTIFIER and wegld_usd_price is not None:
                token.usd_price = wegld_usd_price * rate.rate

            if rate.quote_token_id == USDC_IDENTIFIER and usdc_usd_price is not None:
                token.usd_price = usdc_usd_price * rate.rate

    return token

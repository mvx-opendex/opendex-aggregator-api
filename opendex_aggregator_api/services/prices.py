from typing import List, Optional, Set

import opendex_aggregator_api.services.hatom as hatom_svc
from opendex_aggregator_api.data.model import Esdt, ExchangeRate, LpTokenComposition
from opendex_aggregator_api.services.tokens import (USDC_IDENTIFIER,
                                                    WEGLD_IDENTIFIER)


async def fill_tokens_usd_price(tokens: Set[Esdt],
                                rates: Set[ExchangeRate],
                                lp_tokens_compositions: List[LpTokenComposition]) -> List[Esdt]:
    [wegld_usd_price, usdc_usd_price] = await hatom_svc.fetch_egld_and_usdc_prices()

    tokens = [_fill_token_usd_price(t,
                                    rates,
                                    wegld_usd_price,
                                    usdc_usd_price)
              for t in tokens]

    tokens = [_fill_lp_token_usd_price(t,
                                       tokens,
                                       lp_tokens_compositions)
              for t in tokens]

    return tokens


def _fill_token_usd_price(token: Esdt,
                          rates: List[ExchangeRate],
                          wegld_usd_price: Optional[float],
                          usdc_usd_price: Optional[float]) -> Esdt:
    if token.identifier == WEGLD_IDENTIFIER:
        token.usd_price = wegld_usd_price
    elif token.identifier == USDC_IDENTIFIER:
        token.usd_price = usdc_usd_price
    elif token.is_lp_token:
        return token
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


def _fill_lp_token_usd_price(token: Esdt,
                             tokens: List[Esdt],
                             lp_tokens_compositions: List[LpTokenComposition]) -> Esdt:
    if not token.is_lp_token:
        return token

    comp = next((x for x in lp_tokens_compositions
                 if x.lp_token_id == token.identifier), None)

    if comp and comp.lp_token_supply > 0:

        underlying_tokens = [t for t in tokens
                             if t.identifier in comp.token_ids]

        if len(underlying_tokens) == len(comp.token_ids):
            total_usd_value = 0

            for id, reserve in zip(comp.token_ids, comp.token_reserves):
                underlying_token = next((x for x in underlying_tokens
                                         if x.identifier == id))

                if underlying_token.usd_price is None:
                    return token

                total_usd_value += reserve * underlying_token.usd_price / \
                    10**underlying_token.decimals

        token.usd_price = total_usd_value * 10**token.decimals / comp.lp_token_supply

    return token

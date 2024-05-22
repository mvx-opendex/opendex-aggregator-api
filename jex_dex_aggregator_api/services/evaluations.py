
import logging
from typing import List
from jex_dex_aggregator_api.data.constants import (
    SC_TYPE_JEXCHANGE_LP, SC_TYPE_JEXCHANGE_LP_DEPOSIT,
    SC_TYPE_JEXCHANGE_LP_WITHDRAW, SC_TYPE_JEXCHANGE_ORDERBOOK,
    SC_TYPE_JEXCHANGE_STABLEPOOL, SC_TYPE_JEXCHANGE_STABLEPOOL_DEPOSIT,
    SC_TYPE_JEXCHANGE_STABLEPOOL_WITHDRAW)
from jex_dex_aggregator_api.data.datastore import get_dex_aggregator_pool
from jex_dex_aggregator_api.pools.model import DynamicRoutingSwapEvaluation, SwapEvaluation, SwapRoute
from jex_dex_aggregator_api.services.tokens import (WEGLD_IDENTIFIER,
                                                    get_or_fetch_token)

FEE_MULTIPLIER = 0.05

NO_FEE_POOL_TYPES = [SC_TYPE_JEXCHANGE_ORDERBOOK,
                     SC_TYPE_JEXCHANGE_LP,
                     SC_TYPE_JEXCHANGE_LP_DEPOSIT,
                     SC_TYPE_JEXCHANGE_LP_WITHDRAW,
                     SC_TYPE_JEXCHANGE_STABLEPOOL,
                     SC_TYPE_JEXCHANGE_STABLEPOOL_DEPOSIT,
                     SC_TYPE_JEXCHANGE_STABLEPOOL_WITHDRAW]


def evaluate(route: SwapRoute,
             amount_in: int) -> SwapEvaluation:

    should_apply_fee = len(route.hops) > 1 and all(
        (h.pool.type not in NO_FEE_POOL_TYPES for h in route.hops))

    token = route.token_in
    amount = amount_in
    fee_amount = 0
    fee_token = None
    estimated_gas = 10_000_000
    theorical_amount = amount_in

    for hop in route.hops:
        if hop.token_in != token:
            raise ValueError(f'Invalid input token [{hop.token_in}]')

        pool = get_dex_aggregator_pool(hop.pool.sc_address,
                                       hop.token_in,
                                       hop.token_out)

        if pool is None:
            raise ValueError(
                f'Unknown pool [{hop.pool.sc_address}] [{hop.token_in}] [{hop.token_out}]')

        if should_apply_fee and hop.token_in == WEGLD_IDENTIFIER:
            fee_amount = int(amount * FEE_MULTIPLIER)
            fee_token = WEGLD_IDENTIFIER
            amount -= fee_amount
            theorical_amount -= fee_amount

        esdt_in = get_or_fetch_token(hop.token_in)
        esdt_out = get_or_fetch_token(hop.token_out)

        try:
            amount = pool.estimate_amount_out(esdt_in,
                                              amount,
                                              esdt_out)
        except ValueError as e:
            logging.info('Error during estimation -> 0')
            logging.debug(e)
            amount = 0
            break

        theorical_amount = pool.estimate_theorical_amount_out(esdt_in,
                                                              theorical_amount,
                                                              esdt_out)

        token = hop.token_out

        estimated_gas += pool.estimated_gas()

    if token != route.token_out:
        raise ValueError(
            f'Invalid output token after swaps [{token}] != [{route.token_out}]')

    if should_apply_fee and fee_amount is None:
        fee_amount = int(amount * FEE_MULTIPLIER)
        fee_token = token
        amount -= fee_amount

    return SwapEvaluation(amount_in=amount_in,
                          estimated_gas=estimated_gas,
                          fee_amount=fee_amount,
                          fee_token=fee_token,
                          net_amount_out=amount,
                          route=route,
                          theorical_amount_out=theorical_amount)


def find_best_dynamic_routing_algo1(single_route_evaluations: List[SwapEvaluation],
                                    amount_in: int) -> DynamicRoutingSwapEvaluation:
    if len(single_route_evaluations) < 2:
        return single_route_evaluations[0]

    first_eval = single_route_evaluations[0]

    first_route = first_eval.route

    second_eval = next((e for e in single_route_evaluations[1:]
                        if first_route.is_disjointed(e.route)), None)

    if second_eval is None:
        return first_eval

    second_route = second_eval.route

    amounts = [(amount_in * (100-x) // 100, amount_in * x // 100)
               for x in range(10, 100, 10)]

    best_evals = []
    best_amount_out = first_eval.net_amount_out

    for a1, a2 in amounts:
        e1 = evaluate(first_route, a1)
        e2 = evaluate(second_route, a2)

        amount_out = e1.net_amount_out + e2.net_amount_out

        if amount_out > best_amount_out:
            best_amount_out = amount_out
            best_evals = [e1, e2]

    return DynamicRoutingSwapEvaluation(amount_in=amount_in,
                                        estimated_gas=sum([e.estimated_gas
                                                           for e in best_evals]),
                                        evaluations=best_evals,
                                        net_amount_out=sum([e.net_amount_out
                                                            for e in best_evals]),
                                        theorical_amount_out=sum([e.theorical_amount_out
                                                                  for e in best_evals]),
                                        token_in=first_eval.route.token_in,
                                        token_out=first_eval.route.token_out)

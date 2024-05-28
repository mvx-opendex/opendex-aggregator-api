
import logging
from typing import List, Mapping, Optional, Tuple

import aiohttp

from opendex_aggregator_api.data.datastore import get_dex_aggregator_pool
from opendex_aggregator_api.pools.model import (DynamicRoutingSwapEvaluation,
                                                SwapEvaluation, SwapRoute)
from opendex_aggregator_api.pools.pools import AbstractPool
from opendex_aggregator_api.services.externals import async_sc_query
from opendex_aggregator_api.services.parsers.routing import \
    parse_evaluate_response
from opendex_aggregator_api.services.tokens import (WEGLD_IDENTIFIER,
                                                    get_or_fetch_token)
from opendex_aggregator_api.utils.env import (mvx_gateway_url,
                                              sc_address_aggregator)

FEE_MULTIPLIER = 0.0001  # 0.01%


def evaluate(route: SwapRoute,
             amount_in: int,
             pools_cache: Mapping[Tuple[str, str, str], AbstractPool],
             update_reserves: bool = False) -> SwapEvaluation:

    token = route.token_in
    amount = amount_in
    fee_amount = 0
    fee_token = None
    estimated_gas = 10_000_000
    theorical_amount = amount_in

    for hop in route.hops:
        if hop.token_in != token:
            raise ValueError(f'Invalid input token [{hop.token_in}]')

        pool_cache_key = (hop.pool.sc_address,
                          hop.token_in,
                          hop.token_out)
        pool = pools_cache.get(pool_cache_key, None)

        if pool is None:
            pool = get_dex_aggregator_pool(hop.pool.sc_address,
                                           hop.token_in,
                                           hop.token_out)

        if pool is None:
            raise ValueError(
                f'Unknown pool [{hop.pool.sc_address}] [{hop.token_in}] [{hop.token_out}]')

        pool = pool.deep_copy()
        pools_cache[pool_cache_key] = pool

        if hop.token_in == WEGLD_IDENTIFIER:
            fee_amount = int(amount * FEE_MULTIPLIER)
            fee_token = WEGLD_IDENTIFIER
            amount -= fee_amount
            theorical_amount -= fee_amount

        esdt_in = get_or_fetch_token(hop.token_in)
        esdt_out = get_or_fetch_token(hop.token_out)

        try:
            amount_out, admin_fee_in, admin_fee_out = pool.estimate_amount_out(esdt_in,
                                                                               amount,
                                                                               esdt_out)

            theorical_amount = pool.estimate_theorical_amount_out(esdt_in,
                                                                  theorical_amount,
                                                                  esdt_out)

            if update_reserves:
                pool.update_reserves(esdt_in,
                                     amount - admin_fee_in,
                                     esdt_out,
                                     amount_out + admin_fee_out)
            amount = amount_out
        except ValueError as e:
            logging.info('Error during estimation -> 0')
            logging.info(e)
            amount = 0

        token = hop.token_out

        estimated_gas += pool.estimated_gas()

    if token != route.token_out:
        raise ValueError(
            f'Invalid output token after swaps [{token}] != [{route.token_out}]')

    if fee_amount is None:
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


async def evaluate_online(amount_in: int,
                          route: SwapRoute,
                          http_client: aiohttp.ClientSession) -> Tuple[int, int, int, str]:
    route_payload = route.serialize()
    args = [amount_in, route_payload]

    sc_address = sc_address_aggregator()

    logging.info('QUERY: evaluate (evaluate_route)')
    try:
        result = await async_sc_query(http_client=http_client,
                                      sc_address=sc_address,
                                      function='evaluate',
                                      args=args)
    except:
        logging.exception('Error during evaluation')
        return (0, 0, 0, '')

    if result is not None and len(result) > 0:
        net_amount_out, fee, estimated_gas, fee_token = \
            parse_evaluate_response(result[0])

        return (net_amount_out, fee, estimated_gas, fee_token)

    return (0, 0, 0, '')


def find_best_dynamic_routing_algo1(single_route_evaluations: List[SwapEvaluation],
                                    amount_in: int) -> Optional[DynamicRoutingSwapEvaluation]:
    if len(single_route_evaluations) < 2:
        return None

    first_eval = single_route_evaluations[0]

    first_route = first_eval.route

    second_eval = next((e for e in single_route_evaluations[1:]
                        if first_route.is_disjointed(e.route)), None)

    if second_eval is None:
        return first_eval

    second_route = second_eval.route

    amounts = [(amount_in * (100-x) // 100, amount_in * x // 100)
               for x in range(10, 100, 10)]

    best_evals: List[SwapEvaluation] = []
    best_amount_out = first_eval.net_amount_out

    for a1, a2 in amounts:
        e1 = evaluate(first_route, a1)
        e2 = evaluate(second_route, a2)

        amount_out = e1.net_amount_out + e2.net_amount_out

        if amount_out > best_amount_out:
            best_amount_out = amount_out
            best_evals = [e1, e2]

    if len(best_evals) == 0:
        return None

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


def find_best_dynamic_routing_algo2(single_route_evaluations: List[SwapEvaluation],
                                    amount_in: int) -> Optional[DynamicRoutingSwapEvaluation]:
    if len(single_route_evaluations) < 2:
        return None

    first_eval = single_route_evaluations[0]

    first_route = first_eval.route

    candidates = [e for e in single_route_evaluations[1:]
                  if e.theorical_amount_out >= first_eval.net_amount_out
                  and e.route.is_disjointed(first_route)]

    if len(candidates) == 0:
        return None

    def _slippage(e: SwapEvaluation):
        return (e.net_amount_out - e.theorical_amount_out) / e.theorical_amount_out

    candidates = [c for c in candidates
                  if _slippage(c) > -0.1]

    candidates = sorted(candidates,
                        key=lambda x: x.theorical_amount_out,
                        reverse=True)

    candidates = [first_eval] + candidates[:1]

    slippage = [-1/_slippage(c)
                for c in candidates]

    total_slippage = sum(slippage)

    weights = [s / total_slippage
               for s in slippage]

    evals = [evaluate(c.route,
                      int(amount_in * w))
             for c, w in zip(candidates, weights)]

    return DynamicRoutingSwapEvaluation(amount_in=amount_in,
                                        estimated_gas=sum([e.estimated_gas
                                                           for e in evals]),
                                        evaluations=evals,
                                        net_amount_out=sum([e.net_amount_out
                                                            for e in evals]),
                                        theorical_amount_out=sum([e.theorical_amount_out
                                                                  for e in evals]),
                                        token_in=first_eval.route.token_in,
                                        token_out=first_eval.route.token_out)


async def find_best_dynamic_routing_algo3(routes: List[SwapRoute],
                                          amount_in: int) -> Optional[DynamicRoutingSwapEvaluation]:
    if len(routes) < 2:
        return None

    amounts = [amount_in // 10] * 9
    amounts = [amount_in - sum(amounts)] + amounts
    amounts = [a for a in amounts if a > 0]

    pools_cache: Mapping[Tuple[str, str, str], AbstractPool] = {}

    amount_per_route: Mapping[SwapRoute, int] = {}

    for amount in amounts:
        evals = [evaluate(r,
                          amount,
                          pools_cache) for r in routes]

        evals = sorted(evals,
                       key=lambda x: x.net_amount_out,
                       reverse=True)

        best_eval = next((e for e in evals
                          if  # first eval
                          len(amount_per_route) == 0
                          or  # known route
                          e.route in amount_per_route
                          or  # new route (disjointed from known routes)
                          all((e.route.is_disjointed(r)
                              for r in amount_per_route.keys()))
                          ))

        evaluate(best_eval.route,
                 amount,
                 pools_cache,
                 update_reserves=True)

        amount_of_route = amount_per_route.get(best_eval.route, 0)

        amount_of_route += amount

        amount_per_route[best_eval.route] = amount_of_route

    pools_cache.clear()

    print('-----------------------')
    print('Verifications')

    total_amount_out_verif_offline = 0
    total_amount_out_verif_online = 0

    evals: List[SwapEvaluation] = []

    async with aiohttp.ClientSession(mvx_gateway_url()) as http_client:
        for route, amount in amount_per_route.items():
            print('++')
            print(f'Route: {[h.pool.name for h in route.hops]}')
            print(f'Amount: {amount}')

            eval = evaluate(route, amount, {})

            print(f'Amount out (offline): {eval.net_amount_out}')
            print(f'Fee (offline): {eval.fee_amount} {eval.fee_token}')

            total_amount_out_verif_offline += eval.net_amount_out

            evals.append(eval)

            net_amount_out, fee, _, fee_token = await evaluate_online(amount,
                                                                      route,
                                                                      http_client)

            total_amount_out_verif_online += net_amount_out

            print(f'Amount out (online): {net_amount_out}')
            print(f'Fee (online): {fee} {fee_token}')

    print(
        f'Total amount out (verif) (offline): {total_amount_out_verif_offline}')
    print(
        f'Total amount out (verif) (online): {total_amount_out_verif_online}')

    print(
        f'Diff (offline vs online): {100 * abs(total_amount_out_verif_offline - total_amount_out_verif_online) / total_amount_out_verif_online}%')

    return DynamicRoutingSwapEvaluation(amount_in=amount_in,
                                        estimated_gas=sum((e.estimated_gas)
                                                          for e in evals),
                                        evaluations=evals,
                                        net_amount_out=sum((e.net_amount_out
                                                            for e in evals)),
                                        theorical_amount_out=sum((e.theorical_amount_out
                                                                  for e in evals)),
                                        token_in=evals[0].route.token_in,
                                        token_out=evals[0].route.token_out)


import logging
from time import time
from typing import List, Mapping, Optional, Tuple

import aiohttp

from opendex_aggregator_api.data.constants import SC_TYPE_JEXCHANGE_ORDERBOOK
from opendex_aggregator_api.data.datastore import get_dex_aggregator_pool
from opendex_aggregator_api.pools.model import (DynamicRoutingSwapEvaluation,
                                                SwapEvaluation, SwapRoute)
from opendex_aggregator_api.pools.pools import AbstractPool
from opendex_aggregator_api.services.externals import async_sc_query
from opendex_aggregator_api.services.parsers.routing import \
    parse_evaluate_response
from opendex_aggregator_api.services.tokens import get_or_fetch_token
from opendex_aggregator_api.utils.env import sc_address_aggregator

FEE_MULTIPLIER = 50  # 0.05%
MAX_FEE = 100_000


async def evaluate_fixed_input(route: SwapRoute,
                               amount_in: int,
                               pools_cache: Mapping[Tuple[str, str, str], AbstractPool],
                               http_client: aiohttp.ClientSession) -> Optional[SwapEvaluation]:

    if can_evaluate_offline(route):
        return evaluate_fixed_input_offline(route,
                                            amount_in,
                                            pools_cache)
    else:
        return await evaluate_fixed_input_online(amount_in,
                                                 route,
                                                 http_client)


async def evaluate_fixed_output(route: SwapRoute,
                                net_amount_out: int,
                                pools_cache: Mapping[Tuple[str, str, str], AbstractPool],
                                http_client: aiohttp.ClientSession) -> Optional[SwapEvaluation]:

    if can_evaluate_offline(route):
        return evaluate_fixed_output_offline(route,
                                             net_amount_out,
                                             pools_cache)
    else:
        raise ValueError('Cannot evaluate fixed output (online)')


def evaluate_fixed_input_offline(route: SwapRoute,
                                 amount_in: int,
                                 pools_cache: Mapping[Tuple[str, str, str], AbstractPool],
                                 update_reserves: bool = False) -> Optional[SwapEvaluation]:
    token = route.token_in
    amount = amount_in
    fee_amount = 0
    fee_token = None
    estimated_gas = 10_000_000
    theorical_amount = amount_in

    for hop in route.hops:
        try:
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

            if hop.token_in.startswith('WEGLD-'):
                fee_amount = amount * FEE_MULTIPLIER // MAX_FEE
                fee_token = hop.token_in
                amount -= fee_amount
                theorical_amount -= fee_amount

            esdt_in = get_or_fetch_token(hop.token_in)
            esdt_out = get_or_fetch_token(hop.token_out)

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
            logging.info('Error during estimation for this route -> abort')
            return None

        token = hop.token_out

        if pool:
            estimated_gas += pool.estimated_gas()

    if token != route.token_out:
        raise ValueError(
            f'Invalid output token after swaps [{token}] != [{route.token_out}]')

    if fee_amount == 0:
        fee_amount = amount * FEE_MULTIPLIER // MAX_FEE
        fee_token = token
        amount -= fee_amount

    return SwapEvaluation(amount_in=amount_in,
                          estimated_gas=estimated_gas,
                          fee_amount=fee_amount,
                          fee_token=fee_token,
                          net_amount_out=amount,
                          route=route,
                          theorical_amount_out=theorical_amount)


def evaluate_fixed_output_offline(route: SwapRoute,
                                  net_amount_out: int,
                                  pools_cache: Mapping[Tuple[str, str, str], AbstractPool],
                                  update_reserves: bool = False) -> Optional[SwapEvaluation]:
    token = route.token_out
    amount = net_amount_out
    fee_amount = 0
    fee_token = None
    estimated_gas = 10_000_000
    theorical_amount = net_amount_out

    for hop in reversed(route.hops):
        if hop.token_out != token:
            raise ValueError(f'Invalid output token [{hop.token_out}]')

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

        if hop.token_out.startswith('WEGLD-'):
            fee_amount = amount * FEE_MULTIPLIER // MAX_FEE
            fee_token = hop.token_out
            amount -= fee_amount
            theorical_amount -= fee_amount

        esdt_in = get_or_fetch_token(hop.token_in)
        esdt_out = get_or_fetch_token(hop.token_out)

        try:
            amount_in, admin_fee_in, admin_fee_out = pool.estimate_amount_in(esdt_out,
                                                                             amount,
                                                                             esdt_in)

            # TODO
            # theorical_amount = pool.estimate_theorical_amount_in(esdt_in,
            #                                                       theorical_amount,
            #                                                       esdt_out)

            if update_reserves:
                pool.update_reserves(esdt_in,
                                     amount_in - admin_fee_in,
                                     esdt_out,
                                     amount + admin_fee_out)

            amount = amount_in
        except ValueError as e:
            logging.info('Error during estimation for this route -> abort')
            # logging.exception(e)
            return None

        token = hop.token_in

        estimated_gas += pool.estimated_gas()

    if token != route.token_in:
        raise ValueError(
            f'Invalid output token after swaps [{token}] != [{route.token_in}]')

    if fee_amount == 0:
        fee_amount = amount * FEE_MULTIPLIER // MAX_FEE
        fee_token = token
        amount -= fee_amount

    return SwapEvaluation(amount_in=amount,
                          estimated_gas=estimated_gas,
                          fee_amount=fee_amount,
                          fee_token=fee_token,
                          net_amount_out=net_amount_out,
                          route=route,
                          theorical_amount_out=theorical_amount)


async def evaluate_fixed_input_online(amount_in: int,
                                      route: SwapRoute,
                                      http_client: aiohttp.ClientSession) -> Optional[SwapEvaluation]:
    route_payload = route.serialize()
    args = [amount_in, route_payload]

    sc_address = sc_address_aggregator()

    logging.info('QUERY: evaluate (evaluate_route)')
    try:
        result = await async_sc_query(http_client=http_client,
                                      sc_address=sc_address,
                                      function='evaluateRoute',
                                      args=args)
    except:
        logging.exception('Error during evaluation')
        return None

    if result is not None and len(result) > 0:
        net_amount_out, fee, fee_token = \
            parse_evaluate_response(result[0])

        [h.pool.sc_type_as_code() for h in route.hops]

        return SwapEvaluation(amount_in=amount_in,
                              estimated_gas=route.estimated_gas(),
                              fee_amount=fee,
                              fee_token=fee_token,
                              net_amount_out=net_amount_out,
                              route=route,
                              theorical_amount_out=0)

    return None


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
        e1 = evaluate_fixed_input_offline(first_route, a1)
        e2 = evaluate_fixed_input_offline(second_route, a2)

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

    evals = [evaluate_fixed_input_offline(c.route,
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
                                          amount_in: int,
                                          max_routes: int) -> Optional[DynamicRoutingSwapEvaluation]:
    start = time()

    offline_routes = [r
                      for r in routes
                      if can_evaluate_offline(r)]

    if len(offline_routes) < 2:
        return None

    nb_sub_amounts = 20

    amounts = [amount_in // nb_sub_amounts] * (nb_sub_amounts-1)
    amounts = [amount_in - sum(amounts)] + amounts
    amounts = [a for a in amounts if a > 0]

    pools_cache: Mapping[Tuple[str, str, str], AbstractPool] = {}

    amount_per_route: Mapping[SwapRoute, int] = {}

    for amount in amounts:
        if len(amount_per_route) >= max_routes:
            route_candidates = amount_per_route.keys()
        else:
            route_candidates = offline_routes

        evals = [evaluate_fixed_input_offline(r,
                                              amount,
                                              pools_cache) for r in route_candidates]

        evals = [e for e in evals if e is not None]

        evals = sorted(evals,
                       key=lambda x: x.net_amount_out,
                       reverse=True)

        best_eval = next((e for e in evals
                          if e
                          and  # first eval
                          len(amount_per_route) == 0
                          or  # known route
                          e.route in amount_per_route
                          or  # new route (disjointed from known routes)
                          all((e.route.is_disjointed(r)
                              for r in amount_per_route.keys()))
                          ))

        evaluate_fixed_input_offline(best_eval.route,
                                     amount,
                                     pools_cache,
                                     update_reserves=True)

        amount_of_route = amount_per_route.get(best_eval.route, 0)

        amount_of_route += amount

        amount_per_route[best_eval.route] = amount_of_route

    pools_cache.clear()

    # print('-----------------------')
    # print('Verifications')

    total_amount_out_verif_offline = 0
    # total_amount_out_verif_online = 0

    evals: List[SwapEvaluation] = []

    # async with aiohttp.ClientSession(mvx_gateway_url()) as http_client:
    for route, amount in amount_per_route.items():
        #         print('++')
        #         print(f'Route: {[h.pool.name for h in route.hops]}')
        #         print(f'Amount: {amount}')

        eval = evaluate_fixed_input_offline(route, amount, {})

    #         print(f'Amount out (offline): {eval.net_amount_out}')
    #         print(f'Fee (offline): {eval.fee_amount} {eval.fee_token}')

        total_amount_out_verif_offline += eval.net_amount_out

        evals.append(eval)

    #         start_online_eval = time()
    #         online_eval = await evaluate_fixed_input_online(amount,
    #                                                         route,
    #                                                         http_client)
    #         end_online_eval = time()
    #         logging.info(
    #             f'algo3: online eval computed in {end_online_eval-start_online_eval} seconds')

    #         total_amount_out_verif_online += online_eval.net_amount_out

    #         print(f'Amount out (online): {online_eval.net_amount_out}')
    #         print(
    #             f'Fee (online): {online_eval.fee_amount} {online_eval.fee_token}')

    # print(
    #     f'Total amount out (verif) (offline): {total_amount_out_verif_offline}')
    # print(
    #     f'Total amount out (verif) (online): {total_amount_out_verif_online}')

    # print(
    #     f'Diff (offline vs online): {100 * abs(total_amount_out_verif_offline - total_amount_out_verif_online) / total_amount_out_verif_online}%')

    end = time()

    logging.info(f'algo3: computed in {end-start} seconds')

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


def can_evaluate_offline(route: SwapRoute):
    return all((h.pool.type not in [SC_TYPE_JEXCHANGE_ORDERBOOK]
                for h in route.hops))

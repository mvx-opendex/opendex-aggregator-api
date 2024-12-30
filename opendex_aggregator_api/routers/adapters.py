from opendex_aggregator_api.data.model import Esdt
from opendex_aggregator_api.pools.model import (DynamicRoutingSwapEvaluation,
                                                SwapEvaluation, SwapHop,
                                                SwapPool, SwapRoute)
from opendex_aggregator_api.routers.api_models import (
    DynamicRouteSwapEvaluationOut, StaticRouteSwapEvaluationOut, SwapHopOut,
    SwapPoolOut, SwapRouteOut)
from opendex_aggregator_api.services import gas as gas_svc
from opendex_aggregator_api.services.tokens import get_or_fetch_token


def adap_dyn_eval(e: DynamicRoutingSwapEvaluation,
                  token_in: Esdt,
                  token_out: Esdt) -> DynamicRouteSwapEvaluationOut:

    human_amount_in = e.amount_in / 10**token_in.decimals

    net_human_amount_out = e.net_amount_out / 10**token_out.decimals

    if token_out.usd_price:
        net_usd_amount_out = e.net_amount_out * \
            token_out.usd_price / 10**token_out.decimals
    else:
        net_usd_amount_out = None

    rate = human_amount_in / net_human_amount_out

    rate2 = net_human_amount_out / human_amount_in

    amounts_and_routes_payload = e.build_amounts_and_routes_payload()

    estimated_tx_fee_egld = gas_svc.calculate_tx_fee_egld(data=amounts_and_routes_payload,
                                                          estimated_gas=e.estimated_gas)

    return DynamicRouteSwapEvaluationOut(amount_in=str(e.amount_in),
                                         human_amount_in=human_amount_in,
                                         estimated_gas=str(e.estimated_gas),
                                         estimated_tx_fee_egld=str(
                                             estimated_tx_fee_egld),
                                         net_amount_out=str(e.net_amount_out),
                                         net_human_amount_out=net_human_amount_out,
                                         net_usd_amount_out=net_usd_amount_out,
                                         evals=[adapt_static_eval(x, token_in, token_out)
                                                for x in e.evaluations],
                                         rate=rate,
                                         rate2=rate2,
                                         amounts_and_routes_payload=amounts_and_routes_payload)


def adapt_static_eval(e: SwapEvaluation,
                      token_in: Esdt,
                      token_out: Esdt) -> StaticRouteSwapEvaluationOut:

    net_human_amount_out = e.net_amount_out / 10**token_out.decimals

    if token_out.usd_price:
        net_usd_amount_out = e.net_amount_out * \
            token_out.usd_price / 10**token_out.decimals
    else:
        net_usd_amount_out = None

    theorical_human_amount_out = e.theorical_amount_out / 10**token_out.decimals

    human_amount_in = e.amount_in / 10**token_in.decimals
    rate = human_amount_in / net_human_amount_out if net_human_amount_out else 0
    rate2 = net_human_amount_out / human_amount_in

    if theorical_human_amount_out > 0:
        slippage_percent = 100 * (net_human_amount_out -
                                  theorical_human_amount_out) / theorical_human_amount_out
    else:
        slippage_percent = 0

    amounts_and_routes_payload = e.build_amounts_and_routes_payload()

    estimated_tx_fee_egld = gas_svc.calculate_tx_fee_egld(data=amounts_and_routes_payload,
                                                          estimated_gas=e.estimated_gas)

    return StaticRouteSwapEvaluationOut(amount_in=str(e.amount_in),
                                        human_amount_in=human_amount_in,
                                        estimated_gas=str(e.estimated_gas),
                                        estimated_tx_fee_egld=str(
                                            estimated_tx_fee_egld),
                                        fee_amount=str(e.fee_amount),
                                        fee_token=e.fee_token,
                                        net_amount_out=str(e.net_amount_out),
                                        net_usd_amount_out=net_usd_amount_out,
                                        route=e.route,
                                        route_payload=e.route.serialize().hex(),
                                        net_human_amount_out=net_human_amount_out,
                                        rate=rate,
                                        rate2=rate2,
                                        slippage_percent=slippage_percent,
                                        theorical_amount_out=str(
                                            e.theorical_amount_out),
                                        theorical_human_amount_out=theorical_human_amount_out,
                                        amounts_and_routes_payload=amounts_and_routes_payload)


def adapt_pool(p: SwapPool) -> SwapPoolOut:
    return SwapPoolOut(name=p.name,
                       sc_address=p.sc_address,
                       type=p.type)


def adapt_hop(h: SwapHop) -> SwapHopOut:
    return SwapHopOut(pool=adapt_pool(h.pool),
                      token_in=h.token_in,
                      token_out=h.token_out)


def adapt_route(r: SwapRoute) -> SwapRouteOut:
    return SwapRouteOut(hops=[adapt_hop(h) for h in r.hops],
                        route_payload=r.serialize().hex(),
                        token_in=r.token_in,
                        token_out=r.token_out)

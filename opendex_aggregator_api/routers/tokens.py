
from typing import List

from fastapi import APIRouter

from opendex_aggregator_api.data import datastore
from opendex_aggregator_api.data.model import Esdt
from opendex_aggregator_api.routers.api_models import TokenOut

router = APIRouter()


@router.get("/tokens")
async def get_tokens() -> List[TokenOut]:

    return [_adapt_token(x)
            for x in datastore.get_tokens() or []]


def _adapt_token(x: Esdt) -> TokenOut:
    return TokenOut(decimals=x.decimals,
                    identifier=x.identifier,
                    ticker=x.ticker,
                    name=x.name,
                    is_lp_token=x.is_lp_token,
                    exchange=x.exchange,
                    usd_price=x.usd_price)

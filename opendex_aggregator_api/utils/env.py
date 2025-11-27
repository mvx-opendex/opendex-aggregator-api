import os
from typing import List


def mvx_gateway_url():
    return os.environ['GATEWAY_URL']


def mvx_index_url():
    return os.environ.get('MVX_INDEX_URL', '')


def mvx_public_gateway_url():
    return os.environ['PUBLIC_GATEWAY_URL']


def router_pools_dir():
    return os.environ.get('ROUTER_POOLS_DIR', '')


def sc_address_aggregator():
    return os.environ['SC_ADDRESS_AGGREGATOR']


def sc_address_jex_lp_deployer():
    return os.environ.get('SC_ADDRESS_JEX_LP_DEPLOYER', '')


def sc_address_hatom_staking_segld():
    return os.environ.get('SC_ADDRESS_HATOM_STAKING_SEGLD', '')


def sc_address_hatom_staking_tao():
    return os.environ.get('SC_ADDRESS_HATOM_STAKING_TAO', '')


def sc_address_onedex_swap():
    return os.environ.get('SC_ADDRESS_ONEDEX_SWAP', '')


def sc_addresses_opendex_deployers() -> List[str]:
    value = os.environ.get('SC_ADDRESSES_OPENDEX_DEPLOYERS', '')

    addresses = []

    if value:
        addresses.extend(value.split(','))

    return addresses


def sc_address_system_tokens():
    return os.environ.get('SC_ADDRESS_SYSTEM_TOKENS', '')


def sc_address_hatom_price_feed():
    return os.environ.get('SC_ADDRESS_HATOM_PRICE_FEED', '')


def sc_address_xoxno_liquid_staking_egld():
    return os.environ.get('SC_ADDRESS_XOXNO_LIQUID_STAKING_EGLD', '')


def sc_address_xoxno_liquid_staking_xoxno():
    return os.environ.get('SC_ADDRESS_XOXNO_LIQUID_STAKING_XOXNO', '')

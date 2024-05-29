import os


def mvx_gateway_url():
    return os.environ['GATEWAY_URL']


def sc_address_aggregator():
    return os.environ['SC_ADDRESS_AGGREGATOR']


def sc_address_jex_lp_deployer():
    return os.environ.get('SC_ADDRESS_JEX_LP_DEPLOYER', None)


def sc_address_hatom_staking():
    return os.environ.get('SC_ADDRESS_HATOM_STAKING', None)


def sc_address_onedex_swap():
    return os.environ.get('SC_ADDRESS_ONEDEX_SWAP', None)


def sc_address_system_tokens():
    return os.environ.get('SC_ADDRESS_SYSTEM_TOKENS', None)


def sc_address_vestadex_router():
    return os.environ.get('SC_ADDRESS_VESTADEX_ROUTER', None)


def sc_address_vestax_staking():
    return os.environ.get('SC_ADDRESS_VESTAX_STAKING', None)

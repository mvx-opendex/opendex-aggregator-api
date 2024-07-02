
def calculate_tx_fee_egld(data: str,
                          estimated_gas: int) -> str:

    erd_min_gas_price = 1000000000
    erd_gas_price_modifier = 0.01
    erd_gas_per_data_byte = 1500
    erd_min_gas_limit = 50_000

    data_gas = erd_min_gas_limit + (len(data) * erd_gas_per_data_byte)

    sc_gas = estimated_gas - data_gas

    gas_egld = int(data_gas * erd_min_gas_price) + \
        int(sc_gas * erd_min_gas_price * erd_gas_price_modifier)

    return gas_egld

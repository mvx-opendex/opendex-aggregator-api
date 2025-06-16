# opendex-aggregator-api

DEX aggregator API

## Features

### Dynamic routing

Swap on several pools to minimize slippage

### Automatic on-chain pools detection

All pools are automatically fetched on-chain using public MvX API or your own gateway.

## Compatibility

OpenDex aggregator API is compatible with:

- JEXchange
- xExchange
- OneDex
- AshSwap
- VestaDex (removed in June 2025)
- Hatom (money markets & liquid staking)
- Xoxno (liquid staking)
- Exrond

## Run

```
# init env (1st time only)
./script_mainnet.sh  --init

# Start daemon
NB_WORKERS=3  ./script_mainnet.sh  --start
```

## Integration Guide

### API call to fetch swap evaluations

#### Fixed input

```
GET /evaluate?token_in={token_in}&token_out={token_out}&amount_in={amount}
```

Example:

```
GET /evaluate?token_in=WEGLD-bd4d79&token_out=JEX-9040ca&amount_in=1_000000000000000000
```

#### Fixed output

```
GET /evaluate?token_in={token_in}&token_out={token_out}&amount_out={amount}
```

Example:

```
GET /evaluate?token_in=WEGLD-bd4d79&token_out=JEX-9040ca&amount_out=10000_000000000000000000
```

### API evaluation response

Example of payload response:

```
{
    "static": {
        "amount_in": "1000000000000000000",
        "estimated_gas": "30000000",
        "estimated_tx_fee_egld": "573735000000000",
        "fee_amount": "500000000000000",
        "fee_token": "WEGLD-bd4d79",
        "human_amount_in": 1.0,
        "net_amount_out": "12737555740990711438717",
        "net_human_amount_out": 12737.55574099071,
        "net_usd_amount_out": 21.58139603977241,
        "route": {
            "id_": 2137985246130407305,
            "hops": [
                {
                    "pool": {
                        "name": "JEX: JEX/WEGLD",
                        "sc_address": "erd1qqqqqqqqqqqqqpgq7u4y0qle773mcelvnkapjv36pn2whzy36avs2qccja",
                        "tokens_in": [
                            "JEX-9040ca",
                            "WEGLD-bd4d79"
                        ],
                        "tokens_out": [
                            "JEX-9040ca",
                            "WEGLD-bd4d79"
                        ],
                        "type": "jexchange_lp"
                    },
                    "token_in": "WEGLD-bd4d79",
                    "token_out": "JEX-9040ca"
                }
            ],
            "token_in": "WEGLD-bd4d79",
            "token_out": "JEX-9040ca"
        },
        "route_payload": "0000000c5745474c442d6264346437390000000100000000000000000500f72a4783f9f7a3bc67ec9dba19323a0cd4eb8891d759060000000a4a45582d393034306361",
        "rate": 7.85079979498658e-05,
        "rate2": 12737.55574099071,
        "slippage_percent": -0.14321618190714241,
        "theorical_amount_out": "12755824145302401148393",
        "theorical_human_amount_out": 12755.824145302402,
        "amounts_and_routes_payload": "0de0b6b3a7640000@0000000c5745474c442d6264346437390000000100000000000000000500f72a4783f9f7a3bc67ec9dba19323a0cd4eb8891d759060000000a4a45582d393034306361"
    },
    ...
}
```

### Forge transaction

This section describes how to forge a transaction to the DEX aggregator smart contract and execute a swap.

- SC address:

  - mainnet: `erd1qqqqqqqqqqqqqpgq360nakqgsp5zkmguptucpjy6n4n3du7e5snsd2swzq`
  - devnet: `erd1qqqqqqqqqqqqqpgqqjyq5g07fsh7a5wsvc4fugu8n2v9vcer6avsr4s62v`

- Endpoint:

  - without referral: `aggregate`
  - with referrer: `aggregateWithRef`

- Value:

  - if intput token is EGLD: swap amount
  - else: `0`

- Token transfer:

  - if input token is EGLD: no token transfer
  - else: `ESDTTransfer` with token IN and amount IN

- Arguments:

  - (only if referral) `referrer`: referral address
  - `token_out`: `EGLD` or output token ID,
  - `min_amount_out`: minimum amount to receive. Use `net_amount_out` from API response and apply slippage tolerance.
  - `amounts_and_routes`: simply copy/paste `amounts_and_routes_payload` from API response

- Gas Limit:
  - Use `estimated_gas` from API response. Add `10_000_000` if input token or output token is `EGLD` to cover gas for wrapping/unwrapping.

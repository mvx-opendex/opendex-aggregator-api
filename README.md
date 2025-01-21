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
- VestaDex
- Hatom (money markets & liquid staking)
- Xoxno (liquid staking)
- Exrond

##

```
# init env (1st time only)
./script_mainnet.sh  --init

# Start daemon
NB_WORKERS=3  ./script_mainnet.sh  --start
```

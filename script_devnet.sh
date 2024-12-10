#!/bin/sh

if [ -d .venv ]
then
  . .venv/bin/activate
else
    echo 'Python venv not found'
    exit 1
fi

export GATEWAY_URL=https://devnet-gateway.multiversx.com
export PUBLIC_GATEWAY_URL=https://devnet-gateway.multiversx.com
export REDIS_HOST=localhost
export ROUTER_POOLS_DIR=
export SC_ADDRESS_AGGREGATOR=erd1qqqqqqqqqqqqqpgqqjyq5g07fsh7a5wsvc4fugu8n2v9vcer6avsr4s62v
export SC_ADDRESS_HATOM_STAKING=
export SC_ADDRESS_JEX_LP_DEPLOYER=
export SC_ADDRESS_ONEDEX_SWAP=
export SC_ADDRESS_SYSTEM_TOKENS=erd1qqqqqqqqqqqqqqqpqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqzllls8a5w6u
export SC_ADDRESS_VESTADEX_ROUTER=
export SC_ADDRESS_VESTAX_STAKING=
export SC_ADDRESSES_OPENDEX_DEPLOYERS=erd1qqqqqqqqqqqqqpgq25vpgegz4c9yx3aae6cdd24uzgrdkksw6avsqmj8r8

if [ -z "${NB_WORKERS}" ]; then export NB_WORKERS=2; fi

echo "Nb workers: $NB_WORKERS"

do_kill() {
    ps aux | grep gunicorn | grep opendex-aggregator-api | awk '{print $2}' | xargs kill -9
}

do_start() {
    rm -f pid

    gunicorn -k uvicorn.workers.UvicornWorker opendex_aggregator_api.main:app \
        --workers ${NB_WORKERS} \
        --bind 0.0.0.0:3002 \
        --log-level error \
        --log-file log_devnet \
        --access-logfile log_devnet \
        --capture-output \
        --daemon --pid pid
}

if [ $# -eq 1 ]
then
    if [ $1 = "--start" ]
    then
        do_start
    elif [ $1 = "--stop" ]
    then
        do_kill
    elif [ $1 = "--reload" ]
    then
        echo "Reloading process $(cat pid)"
        kill -HUP $(cat pid)
    elif [ $1 = "--restart" ]
    then
        do_kill
        sleep 5
        do_start
    elif [ $1 = "--dev" ]
    then
        GATEWAY_URL=https://devnet-api.multiversx.com \
            uvicorn opendex_aggregator_api.main:app --host 0.0.0.0 --port 3002 --log-level debug --reload
    elif [ $1 = "--info" ] || [ $1 = "--status" ]
    then
        ps -p $(cat pid)
    else
        echo "Invalid argument $1"
        exit 1
    fi
else
    echo "Usage: $0 {--start|--reload|--restart|--info|--status|--stop}"
fi

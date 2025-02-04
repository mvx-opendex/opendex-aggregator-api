#!/bin/sh

VENV_DIR=.venv

export GATEWAY_URL=http://jex-observer-squad:8079
export PUBLIC_GATEWAY_URL=https://gateway.multiversx.com
export REDIS_HOST=localhost
export ROUTER_POOLS_DIR=${HOME}/jex-router-pools/pools
export SC_ADDRESS_AGGREGATOR=erd1qqqqqqqqqqqqqpgq360nakqgsp5zkmguptucpjy6n4n3du7e5snsd2swzq
export SC_ADDRESS_HATOM_PRICE_FEED=erd1qqqqqqqqqqqqqpgqh3e67630mm7t6awvgdrh78ws9hfh85tz78sssecur8
export SC_ADDRESS_HATOM_STAKING=erd1qqqqqqqqqqqqqpgq4gzfcw7kmkjy8zsf04ce6dl0auhtzjx078sslvrf4e
export SC_ADDRESS_JEX_LP_DEPLOYER=erd1qqqqqqqqqqqqqpgqpz4skj4q0kwndpp0a5n52328xchee6rs6avsqfytay
export SC_ADDRESS_ONEDEX_SWAP=erd1qqqqqqqqqqqqqpgqqz6vp9y50ep867vnr296mqf3dduh6guvmvlsu3sujc
export SC_ADDRESS_SYSTEM_TOKENS=erd1qqqqqqqqqqqqqqqpqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqzllls8a5w6u
export SC_ADDRESS_VESTADEX_ROUTER=erd1qqqqqqqqqqqqqpgq8vem4kq208phuhny9gfy9qza47np63gq0a0s7edevj
export SC_ADDRESS_VESTAX_STAKING=erd1qqqqqqqqqqqqqpgqawus4zu5w2frmhh9rscjqnu9x6msfjya2d2sfw7tsn
export SC_ADDRESS_XOXNO_LIQUID_STAKING=erd1qqqqqqqqqqqqqpgq6uzdzy54wnesfnlaycxwymrn9texlnmyah0ssrfvk6
export SC_ADDRESSES_OPENDEX_DEPLOYERS=

if [ $# -eq 1 ]
then
    if [ $1 = "--init" ]
    then
        if [ ! -d ${VENV_DIR} ]
        then
            python3.10 -m venv ${VENV_DIR}
            . ${VENV_DIR}/bin/activate
            pip install -r opendex_aggregator_api/requirements.txt
        fi
        exit 0
    fi
fi

if [ -d ${VENV_DIR} ]
then
  . ${VENV_DIR}/bin/activate
else
    echo 'Python venv not found'
    echo "Launch:"
    echo "$0 --init"
    exit 1
fi

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
        --log-file log_mainnet \
        --access-logfile log_mainnet \
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
        GATEWAY_URL=http://gateway.mvx.fr:8079 \
            uvicorn opendex_aggregator_api.main:app --host 0.0.0.0 --port 3002 --log-level debug --reload
    elif [ $1 = "--info" ] || [ $1 = "--status" ]
    then
        ps -p $(cat pid)
    else
        echo "Invalid argument $1"
        exit 1
    fi
else
    echo "Usage: $0 {--init|--start|--reload|--restart|--info|--status|--stop}"
fi

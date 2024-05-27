
import requests


token_in = input('Token IN: ')
amount_in = input('Amount IN: ')
token_out = input('Token OUT: ')

resp = requests.get(
    f'https://aggregator-internal.ashswap.io/aggregate?from={token_in}&to={token_out}&amount={amount_in}')
ashswap_out = resp.json()['returnAmountWithDecimal']

print(f'AshSwap: {ashswap_out}')

resp = requests.get(
    f'https://api.jexchange.io/routing/evaluations/v2?token_in={token_in}&token_out={token_out}&amount_in={amount_in}')
jex_out = resp.json()[0]['net_amount_out']

print(f'JEXchange: {jex_out}')

resp = requests.get(
    f'http://localhost:3001/evaluate?token_in={token_in}&token_out={token_out}&amount_in={amount_in}')
eval = resp.json().get('dynamic', resp.json().get('static', {}))
agg_out = eval.get('net_amount_out', 0)

print(f'JEXchange (new): {agg_out}')

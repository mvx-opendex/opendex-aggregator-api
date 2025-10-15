from typing import List

from elasticsearch import Elasticsearch

from opendex_aggregator_api.utils.env import mvx_index_url


def fetch_paused_tokens() -> List[str]:
    es = Elasticsearch(mvx_index_url())

    query = {
        'query': {
            'bool': {
                'must': [
                    {'term': {'type': 'FungibleESDT'}},
                    {'term': {'paused': True}}
                ]
            }
        },
        '_source': ['token'],
        'size': 10_000
    }

    response = es.search(index='tokens', body=query)

    return [hit['_source']['token'] for hit in response['hits']['hits']]

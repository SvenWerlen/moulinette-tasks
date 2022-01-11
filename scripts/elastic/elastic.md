# Elastic Search Implementation

## Create a new deployment

* Navigate to elastic.co
* Create new deployment (with smallest configuration, cost is $0,0217/h)
* Wait until finished

## Get credentials (API)

* Navigate to Enteprise Search
* Skip setup
* Go to "Credentials"
* Copy API Endpoint and private-key to elasticIndexAssets.py
* Copy API Endpoint and search-key to moulinette-tiles/modules/moulinette-search.js

## Index assets

* Execute `update.sh` (from /script folder) to retrieve all assets from server and generate availabe*.json files
* Execute `source ../../environment.sh && python3 elasticCreateIndices.py` to convert assets to data ready to be indexed. Max number can be configured.
* Execute `source ../../environment.sh && python3 elasticIndexAssets.py` (takes about 10 minutes)

## Foundry VTT - Open new search


## Development

* Search : https://www.elastic.co/guide/en/app-search/current/search.html
* Python : https://www.elastic.co/guide/en/enterprise-search-clients/python/current/app-search-api.html
* Javascript :
- https://www.elastic.co/guide/en/elasticsearch/client/javascript-api/current/index.html
- https://github.com/elastic/app-search-javascript

##
## This script updates the schema by adding new fields
##
import os
import time
import json
import requests
from elastic_enterprise_search import AppSearch

ENGINE_NAME = "moulinette"  # Elastic Engine Name
SERVER = os.environ["MOULINETTE_API"]
UPDATE = True

resp = requests.get("%s/static/categories.json" % (SERVER))
data = resp.json()


app_search = AppSearch(
    os.environ["ELASTIC_ENDPOINT"],
    http_auth=os.environ["ELASTIC_PRIVATE"],
)

schema = {}
for d in data:
  key = "cat" + d["id"].lower()
  schema[key] = "text"
  print('  "mtte.filter%s": "",' % key)
  for v in d["values"]:
    print('  "mtte.filterval%s%s": "",' % (d["id"].lower(), v))

if UPDATE:
  resp = app_search.put_schema(
      engine_name=ENGINE_NAME,
      schema=schema
  )

  print(resp)

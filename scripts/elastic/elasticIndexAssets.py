##
## This script re-indexes all documents on Elastic
## - Engine will be regenerated
##
import os
import time
import json
from elastic_enterprise_search import AppSearch

ASSETS_MAX   = 100           # Maximum number of documents per API call
ASSETS_PAUSE = 20000         # Pause 5 seconds after a bunch of documents to not crash the server
ENGINE_NAME  = "moulinette"  # Elastic Engine Name
INDEX_FILE   = "/tmp/available-assets.json"

if not 'ELASTIC_ENDPOINT' in os.environ:
  print("Please set the environment variables!")
  exit(1)

if not os.path.exists(INDEX_FILE):
  print("Please generate the document indices!")
  exit(1)

app_search = AppSearch(
    os.environ["ELASTIC_ENDPOINT"],
    http_auth=os.environ["ELASTIC_PRIVATE"],
)

# Create engine
exists = False
engines = app_search.list_engines()
for e in engines["results"]:
  if e["name"] == "moulinette":
    exists = True

if exists:
  print("Engine '%s' already exists. Deleting..." % ENGINE_NAME)
  app_search.delete_engine(engine_name=ENGINE_NAME)
  time.sleep(2)

print("Creating engine '%s'..." % ENGINE_NAME)
app_search.create_engine(
    engine_name=ENGINE_NAME,
    language="en",
)

print("Importing all assets by %s increment" % ASSETS_MAX)
secs = time.time()
with open(INDEX_FILE) as f:
  data = json.load(f)
  # split array into chunks of max entries
  count = 0
  sublist = [data[i:i+ASSETS_MAX] for i in range(0, len(data), ASSETS_MAX)]
  for docs in sublist:
    app_search.index_documents(
      engine_name=ENGINE_NAME,
      documents=docs
    )
    count += ASSETS_MAX
    if count % ASSETS_PAUSE == 0:
      print("%s documents indexed. Pausing for 5 seconds." % count)
      time.sleep(5)

  print("Indexing completed after %.1f seconds (%d docs indexed)" % (time.time() - secs, len(data)))

print("Updating schema...")
secs = time.time()
resp = app_search.put_schema(
    engine_name=ENGINE_NAME,
    schema={
        "perm": "number",
        "packid": "number",
        "animated": "boolean"
    }
)
print("Schema updated after %.1f seconds" % (time.time() - secs))
print("Completed!")

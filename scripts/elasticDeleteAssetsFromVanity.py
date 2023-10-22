##
## This script deletes all indices for a creator
## (see : moulinette/procedures/rename-vanity.md)
##
import os
import logging
from elastic_enterprise_search import AppSearch

CREATOR_TO_DELETE = "MikWewa Maps"

#################

logger = logging.getLogger(__name__)
ELASTIC_ENGINE = "moulinette"
PAGE_SIZE      = 1000
ASSETS_MAX     = 100

# logging information
logging.basicConfig(
    format="[%(levelname)s] %(message)s (%(filename)s, %(funcName)s(), line %(lineno)d)",
    level=logging.WARN,
)
logger = logging.getLogger("moulinette_utils")
logger.setLevel(logging.INFO)


app_search = AppSearch(
  os.environ["ELASTIC_ENDPOINT"],
  http_auth=os.environ["ELASTIC_PRIVATE"],
)

deleted = 0

logger.info("Deleting existing documents...")
currentPage = 1
while True:
  resp = app_search.search(
    engine_name=ELASTIC_ENGINE,
    body={
      "query": "",
      "filters" : {
        "publisher": CREATOR_TO_DELETE
      },
      "page": { "size": PAGE_SIZE, "current": currentPage }
    }
  )

  toDelete = []
  for doc in resp["results"]:
    toDelete.append(doc['id']['raw'])
    #print(doc['base']['raw'])
  
  sublist = [toDelete[i:i+ASSETS_MAX] for i in range(0, len(toDelete), ASSETS_MAX)]
  for docs in sublist:
    app_search.delete_documents( engine_name=ELASTIC_ENGINE, document_ids=docs )

  logger.info("%s documents deleted!" % len(resp["results"]))
  deleted += len(resp["results"])
  currentPage += 1
  if currentPage > resp["meta"]["page"]["total_pages"]:
    break

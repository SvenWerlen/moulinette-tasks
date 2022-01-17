import os
import json
import logging
import pymysql
from elastic_enterprise_search import AppSearch

logger = logging.getLogger(__name__)

SERVER         = os.environ["MOULINETTE_API"]
SESSION_ID     = "moulinette-readonly-all"
ELASTIC_ENGINE = "moulinette"
PAGE_SIZE      = 1000
ASSETS_MAX     = 100

# access DB
db = pymysql.connect(host="localhost", user=os.environ['DB_USER'], password=os.environ['DB_PASS'], database=os.environ['DB_DB'])
cursor = db.cursor()

# logging information
logging.basicConfig(
    format="[%(levelname)s] %(message)s (%(filename)s, %(funcName)s(), line %(lineno)d)",
    level=logging.WARN,
)
logger = logging.getLogger("moulinette_utils")
logger.setLevel(logging.INFO)

###
### Elastic Tasks - Reindex documents from that pack
### - removes all documents
### - insert new documents
###
### Returns the number of documents deleted and indexed
###
def processUpdateIndices(container, packFile):

  pack = os.path.splitext(packFile)[0]

  app_search = AppSearch(
    os.environ["ELASTIC_ENDPOINT"],
    http_auth=os.environ["ELASTIC_PRIVATE"],
  )

  deleted = 0
  indexed = 0

  logger.info("Deleting existing documents...")
  currentPage = 1
  while True:
    resp = app_search.search(
      engine_name=ELASTIC_ENGINE,
      body={
        "query": "",
        "filters" : {
          "base": "%s/%s" % (container, pack)
        },
        "page": { "size": PAGE_SIZE, "current": currentPage }
      }
    )

    toDelete = []
    for doc in resp["results"]:
      toDelete.append(doc['id']['raw'])
    sublist = [toDelete[i:i+ASSETS_MAX] for i in range(0, len(toDelete), ASSETS_MAX)]
    for docs in sublist:
      app_search.delete_documents( engine_name=ELASTIC_ENGINE, document_ids=docs )

    logger.info("%s documents deleted!" % len(resp["results"]))
    deleted += len(resp["results"])
    currentPage += 1
    if currentPage > resp["meta"]["page"]["total_pages"]:
      break

  logger.info("Adding new documents...")

  # find matching pack
  docs = []
  cursor.execute("SELECT id, assets, publisher, name, baseUrl, vanity FROM packs WHERE packFile = %s", (packFile) )
  results = cursor.fetchall()
  result = None

  # check that container matches
  for r in results:
    if container == r[5].replace("_","").lower():
      result = r

  if not result:
    logger.warning("No packFile %s on container %s" % (packFile, container))
  else:
    # check permissions
    cursor.execute("SELECT tierId FROM packTiers WHERE packId = %s", (result[0]) )
    resultPerms = cursor.fetchall()
    perms = []
    for p in resultPerms:
      perms.append(p[0])

    if len(perms) > 0:
      # index all documents
      assets = json.loads(result[1])
      for a in assets:
        if isinstance(a, dict):
          path = a["path"]
          category = "scene"
          # ignore prefab & sounds & others
          if a["type"] != "scene":
            continue
        else:
          path = a
          category = "image"
          # ignore sounds or other non-image format
          if not a.endswith(".webp") and not a.endswith(".webm"):
            continue

        path = a["path"] if isinstance(a, dict) else a
        pathClean = os.path.splitext(path)[0]
        doc = {
          'publisher': result[2],
          'packid': result[0],
          'pack': result[3],
          'category': category,
          'animated': path.endswith(".webm"),
          'name': pathClean.replace("-", " ").replace("_", " ").title(),
          'base': result[4][47:], # remove https://mttecloudstorage.blob.core.windows.net/
          'path': pathClean,
          'perm': perms
        }

        # add categories
        cursor.execute("SELECT categoryKey, categoryVal FROM categories WHERE packId = %s AND asset = %s", (result[0], path))
        categs = cursor.fetchall()
        for c in categs:
          doc['cat%s' % c[0].lower()] = c[1]

        # add index to be processed
        docs.append(doc)

  sublist = [docs[i:i+ASSETS_MAX] for i in range(0, len(docs), ASSETS_MAX)]
  for d in sublist:
    app_search.index_documents( engine_name=ELASTIC_ENGINE, documents=d )

  logger.info("%s documents indexed!" % len(docs))
  indexed = len(docs)

  return { 'deleted': deleted, 'indexed': indexed }

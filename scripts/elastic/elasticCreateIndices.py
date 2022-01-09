##
## This script prepares the elastic data to be indexed
## - Files available.json and available-scenes.json are reused
## - Set MAX if you want to limit the number of assets to be indexed
##
import re
import os
import json
import requests
import pymysql

## MAXIMUM documents to be indexed
MAX = 0
assets = []

STATIC_FOLDER = os.environ["STATIC_FOLDER"]

if not 'DB_USER' in os.environ:
  print("Please set the environment variables!")
  exit(1)

db = pymysql.connect(host="localhost", user=os.environ['DB_USER'], password=os.environ['DB_PASS'], database=os.environ['DB_DB'])
cursor = db.cursor()


# utility function to return the permissions of a given pack
def getPermissions(packId):
  cursor.execute("SELECT tierId FROM packTiers WHERE packId = %s", pack['id'])
  tiers = cursor.fetchall()
  list = []
  for t in tiers:
    list.append(int(t[0]))

  return list


cursor.execute("SELECT packId, asset, categoryKey, categoryVal FROM categories")
results = cursor.fetchall()

values = {}
for r in results:
  packId = r[0]
  asset  = r[1]
  catKey = r[2]
  catVal = r[3]

  key = "%s#%s" % (packId, asset)
  if not key in values:
    values[key] = {}
  values[key][catKey] = catVal

with open(os.path.join(STATIC_FOLDER, 'availableNew.json')) as f:
  data = json.load(f)

  for pub, packs in data.items():
    for pack in packs:

      for a in pack['assets']:
        if MAX <= 0 or len(assets) < MAX:
          match = re.search('^([^/]+/[^/]+)/(.+).web[pm]$', a)
          if not match:
            print("Something went wrong with", a)
            exit(1)

          index = {
            'publisher': pub,
            'packid': pack['id'],
            'pack': pack['name'],
            'category': 'image',
            'animated': a.endswith(".webm"),
            'name': os.path.basename(a).replace("_thumb.webp", "").replace("-", " ").replace("_", " ").title(),
            'base': match.group(1),
            'path': match.group(2),
            'perm': getPermissions(pack['id'])
          }

          key = "%s#%s.webp" % (pack['id'], match.group(2))
          if key in values:
            for catKey in values[key]:
              index["cat" + catKey.lower()] = values[key][catKey]

          assets.append(index)


with open(os.path.join(STATIC_FOLDER, 'available-scenes.json')) as f:
  data = json.load(f)

  for pub, packs in data.items():
    for pack in packs:

      for a in pack['assets']:
        if MAX <= 0 or len(assets) < MAX:
          match = re.search('^([^/]+/[^/]+)/(.+)_thumb.webp$', a)
          if not match:
            print("Something went wrong with", a)
            exit(1)

          assets.append({
            'publisher': pub,
            'packid': pack['id'],
            'pack': pack['name'],
            'category': 'scene',
            'animated': a.endswith(".webm"),
            'name': os.path.basename(a).replace("_thumb.webp", "").replace("-", " ").replace("_", " ").title(),
            'base': match.group(1),
            'path': match.group(2),
            'perm': getPermissions(pack['id'])
          })

with open('/tmp/available-assets.json', "w") as f:
  json.dump(assets, f)

##
## This script:
## - downloads the list of all available assets
## - checks for each asset if thumb is available
## - if not, downloads the thumb and generates the watermarked version of it
##

import os
import json
import requests
from urllib.parse import unquote

from azure.storage.blob import BlobServiceClient

TMP_FILE          = "/tmp/assets.json"
TMP_THUMB         = "/tmp/moulinette-thumb.webp"
TMP_THUMB2        = "/tmp/moulinette-thumb2.webp"
THUMB_FOLDER      = os.environ['PREVIEW_FOLDER']

SERVER            = os.environ["MOULINETTE_API"]
SESSION_ID        = "moulinette-readonly-all"

STATIC_FOLDER     = os.environ["STATIC_FOLDER"]
STATIC_AVAIL      = "available.json"
STATIC_AVAIL_SC   = "available-scenes.json"
STATIC_AVAIL_NEW    = "availableNew.json"
STATIC_AVAIL_SC_NEW = "availableNew-scenes.json"

BLOB_ACCOUNT_NAME = os.environ['AZURE_STORAGE_ACCOUNT']    # Azure Blob storage account name
BLOB_ACCOUNT_KEY  = os.environ['AZURE_STORAGE_ACCESS_KEY'] # Azure Blob storage account key

WATERMARK         = "../watermark.png"
WATERMARK_MAP     = "../watermark-map.png"

FILTER            = "" # leave blank to not filter


blobService = BlobServiceClient(account_url="https://%s.blob.core.windows.net/" % BLOB_ACCOUNT_NAME, credential=BLOB_ACCOUNT_KEY)

##
## Downloads a file from container/blob and saves it into path
##
def downloadFile(path, container, blob):
  blob = unquote(blob)
  client = blobService.get_blob_client(container, blob, snapshot=None)
  with open(path, "wb") as file:
    if client.exists():
      download_stream = client.download_blob()
      file.write(download_stream.readall())
      return True
  return False



#if not os.path.isfile(TMP_FILE):
resp = requests.get("%s/assets/%s" % (SERVER, SESSION_ID))
data = resp.json()

with open(TMP_FILE, "w") as outfile:
  json.dump(data, outfile)

# Opening JSON file
with open(TMP_FILE, 'r') as infile:
  data = json.load(infile)
  

pubs = {}
pubsNew = {}
pubsMaps = {}
pubsMapsNew = {}

for c in data:
  pub = []
  pubNew = []
  pubMaps = []
  pubMapsNew = []

  for p in c["packs"]:
    path = p["path"].split("mttecloudstorage.blob.core.windows.net/").pop()
    if len(FILTER) > 0 and not path.startswith(FILTER):
      continue
    #if path.startswith("moulinette"):
    #  continue
    
    container = path.split("/")[0]
    packName = path.split("/")[1]
    pack = { 'id': p['id'], 'name': p['name'], 'assets': [] }
    packNew = { 'id': p['id'], 'name': p['name'], 'assets': [] }
    packMaps = { 'id': p['id'], 'name': p['name'], 'assets': [] }
    packMapsNew = { 'id': p['id'], 'name': p['name'], 'assets': [] }
    dir = "%s/%s" % (THUMB_FOLDER, path)

    for a in p["assets"]:
      if not "img" in a:
        print(a)
        continue

      assetPath = a["img"] if isinstance(a, dict) else a
      thumb = os.path.splitext(assetPath)[0] + "_thumb.webp"

      fIndex = thumb.rfind("/")
      thumbPath = os.path.join(dir, thumb)

      if not os.path.isdir(os.path.dirname(thumbPath)):
        os.makedirs(os.path.dirname(thumbPath))

      # maps
      if isinstance(a, dict):
        if a["type"] == "scene":
          if not os.path.isfile(thumbPath):
            blob = os.path.join(packName, thumb)
            if downloadFile(TMP_THUMB, container, blob):
              os.system('convert -thumbnail 400x400 -background none -gravity center "%s" -extent 400x400 "%s"' % (TMP_THUMB, TMP_THUMB2))
              os.system('composite "%s" "%s" -gravity Center "%s"' % (WATERMARK_MAP, TMP_THUMB2, thumbPath))
              print("[M] %s/%s" % (container, blob))
            else:
              print("[MISSING] %s/%s" % (container, blob))
              continue
          packMaps['assets'].append("%s/%s" % (path, thumb))
          packMapsNew['assets'].append("%s/%s" % (path, assetPath))

      # regular assets
      else:
        if a.endswith(".webp") or a.endswith(".webm"):
          if not os.path.isfile(thumbPath):
            blob = os.path.join(packName, thumb)
            if downloadFile(TMP_THUMB, container, blob):
              os.system('convert -thumbnail 100x100 -background none -gravity center "%s" -extent 100x100 "%s"' % (TMP_THUMB, TMP_THUMB2))
              os.system('composite "%s" "%s" -gravity Center "%s"' % (WATERMARK, TMP_THUMB2, thumbPath))
              print("[A] %s/%s" % (container, blob))
            else:
              print("[MISSING] %s/%s" % (container, blob))
              continue
          pack['assets'].append("%s/%s" % (path, thumb))
          packNew['assets'].append("%s/%s" % (path, assetPath))

    if len(pack['assets']) > 0:
      pub.append(pack)
      pubNew.append(packNew)
    if len(packMaps['assets']) > 0:
      pubMaps.append(packMaps)
      pubMapsNew.append(packMapsNew)

  if len(pub) > 0:
    pubs[c["publisher"]] = pub
    pubsNew[c["publisher"]] = pubNew
  if len(pubMaps) > 0:
    pubsMaps[c["publisher"]] = pubMaps
    pubsMapsNew[c["publisher"]] = pubMapsNew

with open(os.path.join(STATIC_FOLDER, STATIC_AVAIL), "w") as outfile:
  json.dump(pubs, outfile)
with open(os.path.join(STATIC_FOLDER, STATIC_AVAIL_SC), "w") as outfile:
  json.dump(pubsMaps, outfile)
with open(os.path.join(STATIC_FOLDER, STATIC_AVAIL_NEW), "w") as outfile:
  json.dump(pubsNew, outfile)
with open(os.path.join(STATIC_FOLDER, STATIC_AVAIL_SC_NEW), "w") as outfile:
  json.dump(pubsMapsNew, outfile)

os.system("chmod -R 775 '%s'" % THUMB_FOLDER)

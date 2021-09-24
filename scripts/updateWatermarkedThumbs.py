##
## This script:
## - downloads the list of all available assets
## - checks for each asset if thumb is available
## - if not, downloads the thumb and generates the watermarked version of it
##

import os
import json
import requests

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

BLOB_ACCOUNT_NAME = os.environ['BLOB_NAME'] # Azure Blob storage account name
BLOB_ACCOUNT_KEY  = os.environ['BLOB_KEY']  # Azure Blob storage account key


blobService = BlobServiceClient(account_url="https://%s.blob.core.windows.net/" % BLOB_ACCOUNT_NAME, credential=BLOB_ACCOUNT_KEY)

##
## Downloads a file from container/blob and saves it into path
##
def downloadFile(path, container, blob):
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
pubsMaps = {}

for c in data:

  for p in c["packs"]:
    path = p["path"].split("mttecloudstorage.blob.core.windows.net/").pop()
    if path.startswith("moulinette"):
      continue
    
    container = path.split("/")[0]
    packName = path.split("/")[1]
    pack = { 'id': p['id'], 'name': p['name'], 'assets': [] }
    packMaps = { 'id': p['id'], 'name': p['name'], 'assets': [] }

    dir = "%s/%s" % (THUMB_FOLDER, path)
    if not os.path.isdir(dir):
      os.makedirs(dir)

    for a in p["assets"]:

      thumb = (os.path.splitext(a["img"])[0] if isinstance(a, dict) else os.path.splitext(a)[0]) + "_thumb.webp"
      fIndex = thumb.rfind("/")
      thumbPath = os.path.join(dir, thumb)

      # maps
      if isinstance(a, dict):
        if a["type"] == "scene":
          if not os.path.isfile(thumbPath):
            blob = os.path.join(packName, thumb)
            if downloadFile(TMP_THUMB, container, blob):
              os.system('convert "%s" -resize 400x400^ "%s"' % (TMP_THUMB, TMP_THUMB2))
              os.system('composite ../watermark-map.png "%s" -gravity North "%s"' % (TMP_THUMB2, thumbPath))
              print("[M] %s/%s" % (container, blob))
              packMaps['assets'].append("%s/%s" % (path, thumb))
            else:
              print("[MISSING] %s/%s" % (container, blob))

      # regular assets
      else:
        if a.endswith(".webp"):
          if not os.path.isfile(thumbPath):
            blob = os.path.join(packName, thumb)
            if downloadFile(TMP_THUMB, container, blob):
              os.system('convert "%s" -resize 100x100^ "%s"' % (TMP_THUMB, TMP_THUMB2))
              os.system('composite ../watermark.png "%s" -gravity North "%s"' % (TMP_THUMB2, thumbPath))
              print("[A] %s/%s" % (container, blob))
              pack['assets'].append("%s/%s" % (path, thumb))
            else:
              print("[MISSING] %s/%s" % (container, blob))

    if len(pack['assets']) > 0:
      pub.append(pack)
    if len(packMaps['assets']) > 0:
      pubMaps.append(packMaps)

with open(os.path.join(STATIC_FOLDER, STATIC_AVAIL), "w") as outfile:
  json.dump(pubs, outfile)
with open(os.path.join(STATIC_FOLDER, STATIC_AVAIL_SC), "w") as outfile:
  json.dump(pubsMaps, outfile)

os.system("chmod -R 755 '%s'" % THUMB_FOLDER)

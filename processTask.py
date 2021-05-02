import os
import sys
import requests
import json
import zipfile
from time import time

# Get environment variables
MOULINETTE_API = os.getenv('MOULINETTE_API')
MOULINETTE_SECRET_KEY = os.getenv('MOULINETTE_SECRET')
AZURE_MOUNT = os.getenv('AZURE_STORAGE_MOUNT')
TASK_ID = os.getenv('TASK_ID')
TMP = "/tmp/"

# Check environment variables
if not MOULINETTE_API or not MOULINETTE_SECRET_KEY:
  sys.exit("Missing environment variables")

# Get authorization code
response = requests.post(url = MOULINETTE_API + "/login", data = json.dumps({"secret" : MOULINETTE_SECRET_KEY}), headers = {"Content-Type": "application/json"})

if response.status_code != 201:
  sys.exit("Authorization failed! " + response.text)

data = response.json()
token = data["access_token"]

# Get tasks
response = requests.get(url = MOULINETTE_API + "/task/" + TASK_ID, headers = {"Content-Type": "application/json", "Authorization": "Bearer " + token})

if response.status_code != 200:
  sys.exit("Get tasks failed! " + response.text)

task = response.json()
id = task["id"]

# TASK Extract
if task["type"] == "extract":
  blob = task["data"]["blob"]
  filepath = os.path.join(AZURE_MOUNT, blob)
  if os.path.isfile(filepath):
    dir = os.path.splitext(os.path.basename(filepath))[0]
    dirpath = os.path.join(AZURE_MOUNT, dir)
    tmppath = os.path.join(TMP, dir)
    if os.path.isdir(dirpath):
      print("Dir %s already exists" % dirpath)
    else:
      # prepare
      if os.path.isdir(tmppath):
        os.system("rm -rf '%s'" % tmppath)
      os.mkdir(tmppath)
      
      # extract archive
      secs = time()
      os.system("unzip -q %s -d %s" % (filepath, tmppath))
      print("Unzipped in %.1f seconds" % (time() - secs))
      
      # change permissions (just in case)
      os.system("chmod -R 755 %s" % tmppath)
      
      # convert images to webp
      secs = time()
      os.system("find '%s' -type f \( -iname \*.jpg -o -iname \*.png -o -iname \*.jpeg \) -exec cwebp -quiet '{}' -o '{}.webp' \;" % tmppath)
      print("Conversion to webp in %.1f seconds" % (time() - secs))
      
      # delete original files, rename webp files and remove all non-images
      secs = time()
      os.system("find '%s' -type f \( -iname \*.jpg -o -iname \*.png -o -iname \*.gif -o -iname \*.jpeg \) -exec rm '{}' \;" % tmppath)
      os.system("find '%s' -type f -not -iname *.webp -exec rm '{}' \;" % tmppath)
      os.system("find '%s' -type f -iname *.webp -exec python3 rename.py '{}' \;" % tmppath)
      print("Cleanup in %.1f seconds" % (time() - secs))
      
      # move files to cloud
      secs = time()
      os.system("mv '%s' '%s'" % (tmppath, dirpath))
      print("Copied to storage in %.1f seconds" % (time() - secs))
      
  else:
    print("Blob %s doesn't exist !" % blob)
    


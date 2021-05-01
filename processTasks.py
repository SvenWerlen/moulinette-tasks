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
response = requests.get(url = MOULINETTE_API + "/tasks", headers = {"Content-Type": "application/json", "Authorization": "Bearer " + token})

if response.status_code != 200:
  sys.exit("Get tasks failed! " + response.text)

tasks = response.json()

for t in tasks:
  id = t["id"]
  
  # TASK Extract
  if t["type"] == "extract":
    blob = t["data"]["blob"]
    filepath = os.path.join(AZURE_MOUNT, blob)
    if os.path.isfile(filepath):
      dir = os.path.splitext(os.path.basename(filepath))[0]
      dirpath = os.path.join(AZURE_MOUNT, dir)
      if os.path.isdir(dirpath):
        print("Dir %s already exists" % dirpath)
      else:
        os.mkdir(dirpath)
        
        # extract archive
        secs = time()
        os.system("unzip -q %s -d %s" % (filepath, dirpath))
        print("Unzipped in %.1f seconds" % (time() - secs))
        
        # change permissions (just in case)
        os.system("chmod -R a+rw %s" % dirpath)
        
        # convert images to webp
        secs = time()
        os.system("find '%s' -type f \( -iname \*.jpg -o -iname \*.png -o -iname \*.gif -o -iname \*.jpeg \) -exec convert '{}' '{}.webp' \;" % dirpath)
        print("Conversion to webp in %.1f seconds" % (time() - secs))
        
        # delete original files, rename webp files and remove all non-images
        secs = time()
        os.system("find '%s' -type f \( -iname \*.jpg -o -iname \*.png -o -iname \*.gif -o -iname \*.jpeg \) -exec rm '{}' \;" % dirpath)
        os.system("find '%s' -type d -exec rename 's/\.(png|gif|jpg|jpeg)\.webp/\.webp/g' '{}/*.webp' \;" % dirpath)
        os.system("find '%s' -type f -not -iname *.webp -exec rm '{}' \;" % dirpath)
        print("Cleanup in %.1f seconds" % (time() - secs))
    else:
      print("Blob %s doesn't exist !" % blob)
    

import os
import sys
import requests
import json
import zipfile
import shutil
from time import time

# Get environment variables (production usage)
MOULINETTE_API = os.getenv('MOULINETTE_API')
MOULINETTE_SECRET_KEY = os.getenv('MOULINETTE_SECRET')
AZURE_MOUNT = os.getenv('AZURE_STORAGE_MOUNT')
TASK_ID = os.getenv('TASK_ID')
TMP = "/tmp/"

# Get environment variables (local/debugging usages)
TASK_TYPE = os.getenv('LOCAL_TYPE')
TASK_FILE = os.getenv('LOCAL_FILE')



# Check environment variables
if AZURE_MOUNT and MOULINETTE_API and MOULINETTE_SECRET_KEY and TASK_ID:

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

elif AZURE_MOUNT and TASK_TYPE and TASK_FILE:
  task = { "type": TASK_TYPE, "data": { "blob": TASK_FILE } }
  
else:
  print(AZURE_MOUNT, TASK_TYPE, TASK_FILE)
  sys.exit("Missing environment variables")


# TASK Extract
if task["type"] == "extract":
  blob = task["data"]["blob"]
  filepath = os.path.join(AZURE_MOUNT, blob)
  if os.path.isfile(filepath):
    dir = os.path.splitext(os.path.basename(filepath))[0]
    dirpath = os.path.join(AZURE_MOUNT, dir)
    tmppath = os.path.join(TMP, "mtte")
    
    # clear existing blobs (if any)
    if os.path.isdir(dirpath):
      os.system("rm -rf '%s'" % dirpath)
    
    # prepare
    if os.path.isdir(tmppath):
      os.system("rm -rf '%s'" % tmppath)
    os.mkdir(tmppath)
    
    # extract archive
    secs = time()
    os.system("./sunzip.sh %s %s" % (filepath, tmppath))
    
    print("Unzipped in %.1f seconds" % (time() - secs))
    
    # change permissions (just in case)
    os.system("chmod -R 755 %s" % tmppath)
    
    # convert images to webp
    secs = time()
    os.system("find '%s' -type f \( -iname \*.jpg -o -iname \*.png -o -iname \*.jpeg \) -execdir mogrify -format webp -quality 60 {} \;" % tmppath)
    print("Conversion to webp in %.1f seconds" % (time() - secs))
    
    # load configuration if exists
    cfg = None
    if os.path.isfile(os.path.join(tmppath, dir, "config.json")):
      with open(os.path.join(tmppath, dir, "config.json"), "r") as f:
        cfg = json.load(f)
    else:
      print("No configuration file found!")
    
    # POST PROCESSING
    thumbsToDelete = []
    for root, dirs, files in os.walk(tmppath):
      for file in files:
        
        ###
        ### VIDEO PROCESSING
        ### - look for exising thumbnail
        ###
        if file.endswith(".webm"):
          thumb = os.path.join(root, os.path.splitext(file)[0] + ".webp")
          # thumbnail already exists
          if os.path.isfile(thumb):
            continue
          
          # look for a matching webp file
          found = None
          for f in os.listdir(root):
            if not f.endswith(".webp"):
              continue
            # filename is included (ex: myvideo-200x200.webm and myvideo.webp)
            if file.startswith(os.path.splitext(f)[0]):
              found = os.path.join(root, f)
              break
            # filename is included when removing the last _... part (ex: myvideo-200x200.webm and myvideo_thumb.webp)
            underscore = f.rfind('_')
            if underscore > 0 and file.startswith(f[0:underscore]):
              found = os.path.join(root, f)
              break
          
          if found:
            shutil.copyfile(found, thumb)
            if not found in thumbsToDelete:
              thumbsToDelete.append(found)
          #else:
            print("Thumbnail for video not found: %s" % thumb)
            # try to generate a new thumbnail from the video
            #os.system("ffmpeg -v -8 -ss 2 -i %s -frames:v 1 %s" % (os.path.join(root, file), thumb))
    
        ###
        ### MAPS PROCESSING (JSON)
        ### - look for matching image (or delete)
        ### - generate thumbnail image
        ### - compress json file
        ###
        ### PREFABS PROCESSING (JSON)
        ### - look for all dependencies and replace with => #DEP#<path>
        ### - compress json file
        ###
        if file.endswith(".json"):
          with open(os.path.join(root, file), "r") as f:
            content = f.read().replace('\n', '')
            data = json.loads(content)
            if "type" in data and data["type"] == "npc":
              if not cfg or not "depPath" in cfg:
                print("Missing dependency path configuration!")
                os.remove(os.path.join(root, file))
              content = content.replace("\"%s/" % cfg["depPath"], "\"#DEP#")
              data = json.loads(content)
              with open(os.path.join(root, file), "w") as fw:
                fw.write(json.dumps(data, separators=(',', ':')))
                
            elif "navigation" in data:
              image = os.path.join(root, os.path.splitext(file)[0] + ".webp")
              # check if image available
              if os.path.isfile(image):
                baseFolder = root[len(tmppath)+1:]
                data["img"] = "#DEP#%s/%s" % (baseFolder, os.path.splitext(file)[0] + ".webp")
                
                # generate thumbnail
                os.system("convert '%s' -thumbnail 400x400^ -gravity center -extent 400x400 '%s'" % (image, os.path.splitext(image)[0] + "_thumb.webp"))
            
                data['tokens'] = []
                data['sounds'] = []
                if "thumb" in data:
                  del data['thumb']
                if "_priorThumbPath" in data:
                  del data['_priorThumbPath']
                
                with open(os.path.join(root, file), "w") as fw:
                  fw.write(json.dumps(data, separators=(',', ':')))
              else:
                os.remove(os.path.join(root, file))
    
    # CLEANUP
    
    # remove all thumbnails (to avoid them to appear in Foundry)
    for t in thumbsToDelete:
      os.remove(t)
    
    # delete original files, rename webp files and remove all non-supported files
    secs = time()
    os.system("find '%s' -type f \( -iname \*.jpg -o -iname \*.png -o -iname \*.gif -o -iname \*.jpeg \) -exec rm '{}' \;" % tmppath)
    os.system("find '%s' -type f -not -iname \*.webp -not -iname \*.webm -not -iname \*.ogg -not -iname \*.json -exec rm '{}' \;" % tmppath)
    print("Cleanup in %.1f seconds" % (time() - secs))
    
    # move files to cloud
    secs = time()
    os.system("mv '%s'/* '%s'" % (tmppath, dirpath))
    print("Copied to storage in %.1f seconds" % (time() - secs))
    
    # cleanup
    if os.path.isdir(tmppath):
      os.system("rm -rf '%s'" % tmppath)
      
  else:
    print("Blob %s doesn't exist !" % blob)
    

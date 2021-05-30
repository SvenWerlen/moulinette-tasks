import os
import sys
import re
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
log = ""
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
    if filepath.endswith(".zip"):
      os.system("./sunzip.sh '%s' '%s'" % (filepath, tmppath))
    elif filepath.endswith(".dungeondraft_pack"):
      os.system("$GOPATH/bin/dungeondraft-unpack '%s' '%s'" % (filepath, tmppath))
    else:
      sys.exit("Invalid file %s" % filepath)
    
    print("Unzipped in %.1f seconds" % (time() - secs))
    log += "Unzipped in %.1f seconds\n" % (time() - secs)
    
    # change permissions (just in case)
    os.system("chmod -R 755 '%s'" % tmppath)
    
    ###
    ### PRE PROCESSING #1
    ### - extract information from any existing module
    ###
    fvttModulePath = os.path.join(tmppath, dir, "module.json")
    configPath = os.path.join(tmppath, dir, "config.json")
    if os.path.isfile(fvttModulePath) and not os.path.isfile(configPath):
      with open(fvttModulePath, 'r') as f:
        data = json.load(f)
        if "name" in data:
          print("Foundry VTT module.json file found with name '%s'" % data["name"])
          log += "Foundry VTT module.json file found with name '%s'\n" % data["name"]
    
          config = {
            "depPath" : "modules/%s" % data["name"]
          }
          with open(configPath, 'w') as out:
            json.dump(config, out)
    
    ###
    ### PRE PROCESSING #2
    ### - extracts all entries from compendiums (if type supported)
    ###
    for root, dirs, files in os.walk(tmppath):
      for file in files:
        if file.endswith(".db"):
          with open(os.path.join(root,file), 'r') as f:
            for line in f:
              data = json.loads(line)
              if "name" in data:
                filename = re.sub('[^0-9a-zA-Z]+', '-', data["name"]).lower()
                folder = None
                # actors => prefab
                if "type" in data and data["type"] == "npc":
                  folder = os.path.join(tmppath, dir, "json", "prefabs")
                # navigation => scene
                elif "navigation" in data:
                  folder = os.path.join(tmppath, dir, "json", "maps")
                
                if folder:
                  os.system("mkdir -p '%s'" % folder)
                  with open(os.path.join(folder, filename + ".json"), 'w') as out:
                    json.dump(data, out)
    
    ###
    ### IMAGE CONVERSION
    ### - converts all images to webp format
    ### - generates thumbnails
    ###
    secs = time()
    os.system("find '%s' -type f \( -iname \*.jpg -o -iname \*.png -o -iname \*.jpeg \) -execdir mogrify -format webp -quality 60 {} \;" % tmppath)
    print("Conversion to webp in %.1f seconds" % (time() - secs))
    log += "Conversion to webp in %.1f seconds\n" % (time() - secs)
    
    # load configuration if exists
    cfg = None
    if os.path.isfile(configPath):
      with open(configPath, "r") as f:
        cfg = json.load(f)
    else:
      print("No configuration file found!")
      log += "No configuration file found!\n"
    
    
    ###
    ### GENERATE MAPS FROM IMAGE or VIDEO
    ###
    if cfg and "maps" in cfg:
      for root, dirs, files in os.walk(os.path.join(tmppath, dir, cfg["maps"])):
        for file in files:
          if file.endswith(".webm") or file.endswith(".mp4") or file.endswith(".webp"):
            map = os.path.join(root, os.path.splitext(file)[0] + ".json")
            name = (os.path.splitext(os.path.basename(filepath))[0]).replace("-"," ")
            name = ' '.join(elem.capitalize() for elem in name.split())
            data = {
              "name": name,
              "navigation": False
            }
            with open(os.path.join(root, map), "w") as fw:
              fw.write(json.dumps(data, separators=(',', ':')))
    
    # POST PROCESSING
    thumbsToDelete = []
    for root, dirs, files in os.walk(tmppath):
      for file in files:
        
        ###
        ### VIDEO PROCESSING
        ### - look for exising thumbnail
        ###
        if file.endswith(".webm") or file.endswith(".mp4"):
          print("- Webm/mp4 %s ... " % file)
          log += "- Webm/mp4 %s ...\n" % file
          
          thumb = os.path.join(root, os.path.splitext(file)[0] + ".webp")
          # thumbnail already exists
          if os.path.isfile(thumb):
            continue
          
          # look for a matching webp file
          found = None
          for f in os.listdir(root):
            if not f.endswith(".webp"):
              continue
          
          if found:
            shutil.copyfile(found, thumb)
            if not found in thumbsToDelete:
              thumbsToDelete.append(found)
          #else:
          #  print("- No thumbnail found for %s ... " % file)
          #  log += "- No thumbnail found for %s ...\n" % file
          else:
            print("- Generating thumbnail for video: %s" % file)
            # try to generate a new thumbnail from the video
            videoPath = os.path.join(root, file)
            thumbFilename = os.path.join(root, os.path.splitext(file)[0])
            os.system('./thumbnailFromVideo.sh "%s" "%s"' % (videoPath, thumbFilename))
            #os.system("ffmpeg -ss 1 -c:v libvpx-vp9 -i %s -frames:v 1 %s" % (os.path.join(root, file), thumb))
          
    
    for root, dirs, files in os.walk(tmppath):
      for file in files:
        
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
            
            # if depPath defined => replace all paths with #DEP#
            if cfg and "depPath" in cfg:
              content = content.replace("\"%s/" % cfg["depPath"], "\"#DEP#")
              if "external" in cfg:
                for idx, dep in enumerate(cfg["external"]):
                  content = content.replace("\"%s/" % dep["src"], "\"#DEP%d#" % idx)

              with open(os.path.join(root, file), "w") as fw:
                fw.write(content)
            
            data = json.loads(content)            
            
            if "type" in data and data["type"] == "npc":
              # nothing more to do
              print("- Prefab %s ... " % file)
              log += "- Prefab %s ...\n" % file
              
            elif "navigation" in data:
              # look for default location for scene image (same folder, same name) OR look for "img" in JSON
              image = os.path.join(root, os.path.splitext(file)[0] + ".webp")
              if not os.path.isfile(image):
                if "img" in data and len(data["img"]) > 0:
                  rootFolder = root[0:root.find('/', len(tmppath)+2)]
                  image = os.path.join(rootFolder, data["img"].replace("#DEP#", ""))
                else:
                  print("- Map %s with invalid img path. Skipped" % file)
                  log += "- Map %s with invalid img path. Skipped\n" % file
                  os.remove(os.path.join(root, file))
                  continue
                
              if os.path.isfile(image):
                print("- Scene %s ... " % file)
                log += "- Scene %s ...\n" % file
              
                rootFolder = root[0:root.find('/', len(tmppath)+2)]
                imgPath = image[len(rootFolder)+1:]
                
                # support for video (webm/mp4) as image file (webp image also exists)
                if os.path.isfile(os.path.join(root, os.path.splitext(file)[0] + ".mp4")):
                  imgPath = os.path.splitext(imgPath)[0] + ".mp4"
                elif os.path.isfile(os.path.join(root, os.path.splitext(file)[0] + ".webm")):
                  imgPath = os.path.splitext(imgPath)[0] + ".webm"
                
                data["img"] = "#DEP#%s" % imgPath
                
                # generate thumbnail
                os.system("convert '%s' -thumbnail 400x400^ -gravity center -extent 400x400 '%s'" % (image, os.path.splitext(image)[0] + "_thumb.webp"))
            
                if "thumb" in data:
                  del data['thumb']
                if "_priorThumbPath" in data:
                  del data['_priorThumbPath']
                
                with open(os.path.join(root, file), "w") as fw:
                  fw.write(json.dumps(data, separators=(',', ':')))
                
              else:
                print("- Map %s without image. Skipped" % file)
                log += "- Map %s without image. Skipped\n" % file
                os.remove(os.path.join(root, file))
    
    ###
    ### Generate thumbnails if not exist
    ###    
    secs = time()
    for root, dirs, files in os.walk(tmppath):
      for file in files:
        if file.endswith(".webp") and not "_thumb" in file:
          thumbPath = os.path.join(root, os.path.splitext(file)[0] + "_thumb.webp")
          if not os.path.isfile(thumbPath):
            imagePath = os.path.join(root, file)
            os.system('convert "%s" -resize 100x100 "%s"' % (imagePath, thumbPath))
            print("- Thumbnail generated for %s" % file)
            log += "- Thumbnail generated for %s\n" % file
    print("Thumbnails generated in %.1f seconds" % (time() - secs))
    log += "Thumbnails generated in %.1f seconds\n" % (time() - secs)
    
    ###
    ### CLEANUP
    ###
    
    # remove all thumbnails (to avoid them to appear in Foundry)
    for t in thumbsToDelete:
      os.remove(t)
    
    # delete original files, rename webp files and remove all non-supported files
    secs = time()
    os.system("find '%s' -type f \( -iname \*.jpg -o -iname \*.png -o -iname \*.gif -o -iname \*.jpeg \) -exec rm '{}' \;" % tmppath)
    os.system("find '%s' -type f -not -iname \*.webp -not -iname \*.webm -not -iname \*.mp4 -not -iname \*.ogg -not -iname \*.json -exec rm '{}' \;" % tmppath)
    print("Cleanup in %.1f seconds" % (time() - secs))
    log += "Cleanup in %.1f seconds\n" % (time() - secs)

    ###
    ### LOG
    ###
    log += "\n\nDependencies:\n"
    
    folder = None
    # find unique folder in tmp
    for d in os.listdir(tmppath):
      if os.path.isdir(os.path.join(tmppath, d)):
        folder = d
        break
    
    if folder:
      logPath = os.path.join(tmppath, folder, "info.log")
      with open(logPath, 'w') as out:
        out.write(log)
      os.system("grep 'modules/[^/\"]*/[^\"]*' %s -ohr | sort | uniq >> '%s'" % (tmppath, logPath))
    
    # move files to cloud
    secs = time()
    os.system("mv '%s'/* '%s'" % (tmppath, dirpath))
    print("Copied to storage in %.1f seconds" % (time() - secs))
    
    # cleanup
    if os.path.isdir(tmppath):
      os.system("rm -rf '%s'" % tmppath)
      
  else:
    print("Blob %s doesn't exist !" % blob)
    

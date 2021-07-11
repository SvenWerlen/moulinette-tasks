import os
import sys
import re
import requests
import json
import zipfile
import shutil
from time import time
from urllib.parse import unquote

# Get required variable environment
OUTPUT_FOLDER = os.getenv('OUTPUT_FOLDER')
TMP = "/tmp/"

if not OUTPUT_FOLDER or not os.path.isfile(os.path.join(OUTPUT_FOLDER, "task.json")):
  sys.exit("[ProcessTask] %s is not a valid directory or task.json not found" % OUTPUT_FOLDER)

task = {}
with open(os.path.join(OUTPUT_FOLDER, "task.json")) as f:
  task = json.load(f)


# TASK Extract
log = ""
if task["type"] == "extract":
  blob = task["data"]["blob"]
  filepath = os.path.join(OUTPUT_FOLDER, blob)
  if os.path.isfile(filepath):
    dir = os.path.splitext(os.path.basename(filepath))[0]
    dirpath = os.path.join(OUTPUT_FOLDER, dir)
    tmppath = os.path.join(TMP, "mtte")    
    print("[ProcessTask] Processing '%s'" % blob)
        
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
    
    print("[ProcessTask] Unzipped in %.1f seconds" % (time() - secs))
    log += "Unzipped in %.1f seconds\n" % (time() - secs)
    
    # change permissions (just in case)
    os.system("chmod -R 755 '%s'" % tmppath)
    
    ###
    ### PRE CLEANUP
    ### - remove all __MACOSX folders
    ###
    os.system("find '%s' -name '__MACOSX' -exec rm -rf {} \;" % tmppath)
    
    ###
    ### PRE PROCESSING #1
    ### - extract information from any existing module
    ###
    fvttModulePath = os.path.join(tmppath, dir, "module.json")
    configPath = os.path.join(tmppath, dir, "json", "config.json")
    if not os.path.isfile(configPath):
      configPath = os.path.join(tmppath, dir, "config.json")
    
    if os.path.isfile(fvttModulePath) and not os.path.isfile(configPath):
      with open(fvttModulePath, 'r') as f:
        data = json.load(f)
        if "name" in data:
          print("[ProcessTask] Foundry VTT module.json file found with name '%s'" % data["name"])
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
    ### PRE PROCESSING #3 (special for Baileywiki)
    ### - assuming that all images in json/ folder are thumbnails, rename them accordingly
    ###
    for root, dirs, files in os.walk(os.path.join(TMP, "mtte", dir, "json")):
      for file in files:
        if file.endswith(".webp"):
          source = os.path.join(root, file)
          target = os.path.join(root, os.path.splitext(file)[0] + "_thumb.webp")
          os.rename(source, target)
    
    ###
    ### IMAGE CONVERSION
    ### - converts all images to webp format
    ### - generates thumbnails
    ###
    secs = time()
    os.system("find '%s' -type f \( -iname \*.jpg -o -iname \*.png -o -iname \*.jpeg \) -execdir mogrify -format webp -quality 60 {} \;" % tmppath)
    print("[ProcessTask] Conversion to webp in %.1f seconds" % (time() - secs))
    log += "Conversion to webp in %.1f seconds\n" % (time() - secs)
    
    # load configuration if exists
    cfg = None
    if os.path.isfile(configPath):
      with open(configPath, "r") as f:
        cfg = json.load(f)
    else:
      print("[ProcessTask] No configuration file found!")
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
          print("[ProcessTask] - Webm/mp4 %s ... " % file)
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
            print("[ProcessTask] - Generating thumbnail for video: %s" % file)
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
        ### - generate thumbnail image (if not provided)
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
              
              # make sure that all assets are in webm format
              content = re.sub(r'"(#DEP[^"]*).(?:png|jpg)"', '"\g<1>.webp"', content)

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
                if "img" in data and data["img"] and len(data["img"]) > 0:
                  idx = root.find('/', len(tmppath)+2)
                  rootFolder = root[0:idx] if idx >= 0 else root
                  imagePath = unquote(os.path.join(rootFolder, data["img"].replace("#DEP#", "")))
                  # copy background image file near json file (required to match with thumbnail)
                  if re.match("#DEP\d#", data["img"]):
                    print("[ProcessTask] Thumbnail is not possible from external pack: %s" % data["img"])
                    image = imagePath
                  else:
                    shutil.copyfile(imagePath, image)
                else:
                  print("[ProcessTask] - Map %s with missing img path. Skipped" % file)
                  log += "- Map %s with missing img path. Skipped\n" % file
                  os.remove(os.path.join(root, file))
                  continue
                
              # if image path depends on another pack => don't generate thumbnail (assume it was done)
              imgExternal = re.match("#DEP\d#", data["img"]) if "img" in data and data["img"] else None
              if imgExternal or os.path.isfile(image):
                print("[ProcessTask] - Scene %s ... " % file)
                log += "- Scene %s ...\n" % file
              
                idx = root.find('/', len(tmppath)+2)
                rootFolder = root[0:idx] if idx >= 0 else root
                imgPath = image[len(rootFolder)+1:]
                
                # support for video (webm/mp4) as image file (webp image also exists)
                if os.path.isfile(os.path.join(root, os.path.splitext(file)[0] + ".mp4")):
                  imgPath = os.path.splitext(imgPath)[0] + ".mp4"
                elif os.path.isfile(os.path.join(root, os.path.splitext(file)[0] + ".webm")):
                  imgPath = os.path.splitext(imgPath)[0] + ".webm"
                
                if not imgExternal:
                  data["img"] = "#DEP#%s" % imgPath

                  # generate thumbnail
                  thumbPath = os.path.splitext(image)[0] + "_thumb.webp"
                  if not os.path.isfile(thumbPath):
                    os.system('convert "%s" -thumbnail 400x400^ -gravity center -extent 400x400 "%s"' % (image, thumbPath))
            
                if "thumb" in data:
                  del data['thumb']
                if "_priorThumbPath" in data:
                  del data['_priorThumbPath']
                
                with open(os.path.join(root, file), "w") as fw:
                  fw.write(json.dumps(data, separators=(',', ':')))
                
              else:
                print("[ProcessTask] - Map %s without image (%s). Skipped" % (file, image))
                log += "- Map %s without image (%s). Skipped\n" % (file, image)
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
            if os.path.isfile(thumbPath):
              print("[ProcessTask] - Thumbnail generated for %s" % file)
              log += "- Thumbnail generated for %s\n" % file
            else:
              print("[ProcessTask] - Thumbnail NOT GENERATED as expected for %s" % file)
              log += "- Thumbnail NOT GENERATED as expected for %s\n" % file

    print("[ProcessTask] Thumbnails generated in %.1f seconds" % (time() - secs))
    log += "Thumbnails generated in %.1f seconds\n" % (time() - secs)
    
    ###
    ### CLEANUP
    ###
    
    # remove all thumbnails (to avoid them to appear in Foundry)
    for t in thumbsToDelete:
      os.remove(t)
    
    # delete original files, rename webp files and remove all non-supported files
    secs = time()
    os.system("find '%s' -type f -not -iname \*.svg -not -iname \*.webp -not -iname \*.webm -not -iname \*.mp4 -not -iname \*.ogg -not -iname \*.mp3 -not -iname \*.wav -not -iname \*.json -exec rm '{}' \;" % tmppath)
    print("[ProcessTask] Cleanup in %.1f seconds" % (time() - secs))
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

    
    # clear existing blobs (if any)
    secs = time()
    if os.path.isdir(dirpath):
      os.system("rm -rf '%s'" % dirpath)
    print("[ProcessTask] Existing blobs deleted in %.1f seconds" % (time() - secs))
    
    # move files to target
    secs = time()
    os.system("mv '%s'/* '%s'" % (tmppath, dirpath))
    print("[ProcessTask] Copied to output folder in %.1f seconds" % (time() - secs))
    
    # cleanup
    if os.path.isdir(tmppath):
      os.system("rm -rf '%s'" % tmppath)
      
  else:
    sys.exit("[ProcessTask] Blob %s doesn't exist !" % blob)
    

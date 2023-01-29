import os
import sys
import re
import requests
import logging
import json
import zipfile
import shutil
import subprocess
import audioread
from tinytag import TinyTag
from time import time
from urllib.parse import unquote
from processTasksScenePacker import *
from processTasksElastic import *

logger = logging.getLogger(__name__)

# Get required variable environment
OUTPUT_FOLDER = os.getenv('OUTPUT_FOLDER')
PREVIEW_FOLDER = os.getenv('PREVIEW_FOLDER')
TASKS_FILE   = "moulinette-tasks.json"
TASKS_STATUS = "moulinette-tasks-status.json"
TMP = "/tmp/"
DEBUG = False

# Check if debug mode enabled
if len(sys.argv) > 1:
  DEBUG = sys.argv[1] == "true"

# Check output folder
if not OUTPUT_FOLDER or not os.path.isdir(OUTPUT_FOLDER):
  sys.exit("[ProcessTasks] %s is not a valid directory" % OUTPUT_FOLDER)

# Check tasks (input)
if not os.path.isfile(os.path.join(TMP, TASKS_FILE)):
  sys.exit("[ProcessTasks] no %s file found" % TASKS_FILE)

tasks = []
with open(os.path.join(TMP, TASKS_FILE)) as f:
  tasks = json.load(f)


## utility function to get the size of a folder
def getSize(path):
  total_size = 0
  for dirpath, dirnames, filenames in os.walk(path):
    for f in filenames:
      fp = os.path.join(dirpath, f)
      # skip if it is symbolic link
      if not os.path.islink(fp):
        total_size += os.path.getsize(fp)

  return total_size

# Only process 1 task at a time
if len(tasks) > 0:
  task = tasks[0]
  
  print("[ProcessTasks] Processing task %s" % task["id"])
  
  
  log = ""
  
  ############################################################################################################################
  ################################## TASK ELASTIC ############################################################################
  ############################################################################################################################
  if task["type"] == "updateIndex":
    try:
      stats = processUpdateIndices(task['container'], task['packFile'])

      if DEBUG:
        print("Stopping before COMPLETION")
        exit(1)

      task["status"] = "done"
      task["details"] = "%s docs deleted, %s docs indexed" % (stats['deleted'], stats['indexed'])

    except Exception as e:
      logger.error("Error index update")
      logger.error(e)
      task["status"] = "failed"

  ############################################################################################################################
  ################################## TASK BYOA ###############################################################################
  ############################################################################################################################
  elif task["type"] == "byoa":
    blob = task["packFile"]
    container = task["container"]
    filepath = os.path.join(OUTPUT_FOLDER, container, blob)
    try:
      if os.path.isfile(filepath):
        dir = os.path.splitext(os.path.basename(filepath))[0]
        dirpath = os.path.join(OUTPUT_FOLDER, container, dir)
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
        ### - remove all files larger than 20 MB
        ###
        os.system("find '%s' -name '__MACOSX' -exec rm -rf {} \;" % tmppath)
        os.system("find '%s' -type f -name '.*' -exec rm -f {} \;" % tmppath)
        os.system("find '%s' -type f \( -iname \*.jpg -o -iname \*.png -o -iname \*.jpeg \) -size +20M -exec rm -f {} \;" % tmppath)

        ###
        ### IMAGE CONVERSION
        ### - converts all images to webp format
        ### - generates thumbnails
        ###
        secs = time()
        os.system("find '%s' -type f \( -iname \*.jpg -o -iname \*.png -o -iname \*.jpeg \) -execdir mogrify -format webp -quality 60 {} \;" % tmppath)
        print("[ProcessTask] Conversion to webp in %.1f seconds" % (time() - secs))
        log += "Conversion to webp in %.1f seconds\n" % (time() - secs)

        ###
        ### PRE PROCESSING
        ### - simple maps (when "maps.mtte" file is added to pack)
        ###
        cfg = None
        if os.path.isfile(os.path.join(tmppath, dir, "maps.mtte")):
          for root, dirs, files in os.walk(os.path.join(tmppath, dir)):
            for file in files:
              if file.endswith(".webm") or file.endswith(".mp4") or file.endswith(".webp"):
                print("[ProcessTask] - Map generation for %s ... " % file)
                log += "- Map generation for %s ...\n" % file

                map = os.path.join(root, os.path.splitext(file)[0] + ".json")
                name = (os.path.splitext(os.path.basename(filepath))[0]).replace("-"," ")
                name = ' '.join(elem.capitalize() for elem in name.split())
                data = {
                  "name": name,
                  "navigation": False,
                  "img": "#DEP#" + os.path.splitext(file)[0] + ".webp"
                }
                # generate thumbnail
                imgPath = os.path.join(root, file)
                thumbPath = os.path.join(root, os.path.splitext(file)[0] + "_thumb.webp")
                os.system('convert "%s" -resize 400x400^ -gravity center -extent 400x400 "%s"' % (imgPath, thumbPath))

                with open(os.path.join(root, map), "w") as fw:
                  fw.write(json.dumps(data, separators=(',', ':')))

        # POST PROCESSING #1
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

        # POST PROCESSING #2
        for root, dirs, files in os.walk(tmppath):
          for file in files:

            ###
            ### MAPS PROCESSING (JSON)
            ### - look for matching image (or delete)
            ###
            if file.endswith(".json"):
              with open(os.path.join(root, file), "r") as f:
                content = f.read().replace('\n', '')

                # make sure that all assets are in webp format
                content = re.sub(r'"(#DEP[^"]*).(?:png|jpg|gif|jpeg)"', '"\g<1>.webp"', content)

                data = json.loads(content)
                backgroundImage = None
                # UP TO V9
                if "img" in data:
                  backgroundImage = data["img"]
                # FROM V10
                elif "background" in data and "src" in data["background"]:
                  backgroundImage = data["background"]["src"]

                if "navigation" in data:
                  # look for default location for scene image (same folder, same name)
                  image = os.path.join(root, os.path.splitext(file)[0] + ".webp")
                  thumb = os.path.join(root, os.path.splitext(file)[0] + "_thumb.webp")
                  if not os.path.isfile(image):
                    # for WebM files, get extracted frame
                    srcImage = backgroundImage.replace("#DEP#", os.path.join(tmppath, dir) + "/") if backgroundImage else ""
                    srcImage = os.path.splitext(srcImage)[0] + ".webp"
                    if os.path.isfile(srcImage):
                      shutil.copyfile(srcImage, image)
                    else:
                      print("[ProcessTask] - Map %s with missing thumbnail. Skipped" % file)
                      log += "- Map %s with missing thumbnail. Skipped\n" % file

                      if not DEBUG:
                        os.remove(os.path.join(root, file))

                      continue

                  if not os.path.isfile(thumb):
                    shutil.copyfile(image, thumb) # avoid thumbnail being generated

                # compress JSON
                with open(os.path.join(root, file), "w") as fw:
                  fw.write(json.dumps(data, separators=(',', ':')))


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

        if DEBUG:
          print("Stopping before CLEANUP")
          exit(1)

        ###
        ### CLEANUP
        ###

        # remove all thumbnails (to avoid them to appear in Foundry)
        for t in thumbsToDelete:
          os.remove(t)

        # delete original files, rename webp files and remove all non-supported files
        secs = time()
        os.system("find '%s' -type f -not -iname \*.json -not -iname \*.svg -not -iname \*.webp -not -iname \*.webm -not -iname \*.mp4 -not -iname \*.ogg -not -iname \*.mp3 -exec rm '{}' \;" % tmppath)
        print("[ProcessTask] Cleanup in %.1f seconds" % (time() - secs))
        log += "Cleanup in %.1f seconds\n" % (time() - secs)

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

        # update task status
        task["newSize"] = getSize(dirpath)
        task["status"] = "done"

      else:
        raise Exception("[ProcessTask] PackFile %s doesn't exist ! Skipping..." % blob)

    # Exception handling
    except Exception as e:
      print("[ProcessTask] Exception during processing")
      print(e)
      task["status"] = "failed"
      
  ############################################################################################################################
  ################################## TASK Extract ############################################################################
  ############################################################################################################################
  if task["type"] == "extract":
    blob = task["packFile"]
    container = task["container"]
    filepath = os.path.join(OUTPUT_FOLDER, container, blob)
    try:
      if os.path.isfile(filepath):
        dir = os.path.splitext(os.path.basename(filepath))[0]
        dirpath = os.path.join(OUTPUT_FOLDER, container, dir)
        tmppath = os.path.join(TMP, "mtte")
        print("[ProcessTask] Processing '%s'" % blob)

        # prepare (clean any existing file)
        if os.path.isdir(tmppath):
          subprocess.run(["rm", "-rf", tmppath])
        os.mkdir(tmppath)
        #if os.path.isdir(os.path.join(PREVIEW_FOLDER, container)):
        #  subprocess.run(["rm", "-rf", os.path.join(PREVIEW_FOLDER, container)])
        #os.mkdir(os.path.join(PREVIEW_FOLDER, container))

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
        ### - remove all files larger than 20 MB
        ###
        os.system("find '%s' -name '__MACOSX' -exec rm -rf {} \;" % tmppath)
        os.system("find '%s' -type f -name '.*' -exec rm -f {} \;" % tmppath)
        os.system("find '%s' -type f \( -iname \*.jpg -o -iname \*.png -o -iname \*.jpeg \) -size +20M -exec rm -rf {} \;" % tmppath)

        ###
        ### SCENE PACKER
        ###
        task["packer"] = False
        if os.path.isfile( os.path.join(tmppath, dir, "scene-packer.info") ):
          print("[ProcessTask] Scene Packer identified.")
          task["packer"] = True
          processScenePacker(tmppath, dir, container)

          if DEBUG:
            print("Stopping before CLEANUP")
            exit(1)

        ###
        ### REGULAR PACK
        ###
        else:

          packs = []

          ###
          ### PRE PROCESSING #1.a
          ### - extract information from any existing module
          ###
          fvttModulePath = os.path.join(tmppath, dir, "module.json")
          configPath = os.path.join(tmppath, dir, "json", "config.json")
          if not os.path.isfile(configPath):
            configPath = os.path.join(tmppath, dir, "config.json")

          if os.path.isfile(fvttModulePath) and not os.path.isfile(configPath):
            with open(fvttModulePath, 'r') as f:
              data = json.load(f)
              if "name" in data or "id" in data:
                # V10 (id), V9 (name)
                moduleID = data["id"] if "id" in data else data["name"]

                print("[ProcessTask] Foundry VTT module.json file found with name '%s'" % moduleID)
                log += "Foundry VTT module.json file found with name '%s'\n" % moduleID

                config = {
                  "depPath" : "modules/%s" % moduleID
                }
                with open(configPath, 'w') as out:
                  json.dump(config, out)

                # extract compendiums info
                if "packs" in data:
                  packs = data["packs"]

          ###
          ### PRE PROCESSING #1.b
          ### - extract information from any existing module
          ###
          fvttWorldPath = os.path.join(tmppath, dir, "world.json")

          if os.path.isfile(fvttWorldPath) and not os.path.isfile(configPath):
            with open(fvttWorldPath, 'r') as f:
              data = json.load(f)
              if "name" in data or "id" in data:
                # V10 (id), V9 (name)
                moduleID = data["id"] if "id" in data else data["name"]

                print("[ProcessTask] Foundry VTT world.json file found with name '%s'" % moduleID)
                log += "Foundry VTT world.json file found with name '%s'\n" % moduleID

                config = {
                  "depPath" : "worlds/%s" % moduleID
                }
                with open(configPath, 'w') as out:
                  json.dump(config, out)

                # extract compendiums info
                if "packs" in data:
                  packs = data["packs"]

          ###
          ### PRE PROCESSING #2
          ### - extracts all entries from compendiums (if type supported)
          ###
          for root, dirs, files in os.walk(tmppath):
            for file in files:
              if file.endswith(".db"):

                # find matching compendium
                type = None
                for p in packs:
                  if os.path.join(root,file).endswith(p["path"]) and "type" in p:
                    type = p["type"]

                with open(os.path.join(root,file), 'r') as f:
                  for line in f:
                    data = json.loads(line)
                    if "name" in data:
                      filename = re.sub('[^0-9a-zA-Z]+', '-', data["name"]).lower()
                      folder = None

                      # special case (dummy scene)
                      if data["name"] == "#[CF_tempEntity]":
                        print("Skipping scene with name %s" % data["name"])
                        continue;

                      # support for Adventures
                      # - explode elements in individual files
                      if type == "Adventure":
                        hasContent = False
                        advPath = re.sub('[^0-9a-zA-Z]+', '-', data["name"]).lower()
                        if "scenes" in data and len(data["scenes"]) > 0:
                          folder = os.path.join(tmppath, dir, "json", "adventures", advPath, "scenes")
                          os.system("mkdir -p '%s'" % folder)
                          # extract scenes
                          for sc in data["scenes"]:
                            filename = re.sub('[^0-9a-zA-Z]+', '-', sc["name"]).lower()
                            with open(os.path.join(folder, filename + ".json"), 'w') as out:
                              json.dump(sc, out)
                          hasContent = True
                        if "actors" in data and len(data["actors"]) > 0:
                          folder = os.path.join(tmppath, dir, "json", "adventures", advPath, "actors")
                          os.system("mkdir -p '%s'" % folder)
                          # extract actors
                          for sc in data["actors"]:
                            filename = re.sub('[^0-9a-zA-Z]+', '-', sc["name"]).lower()
                            with open(os.path.join(folder, filename + ".json"), 'w') as out:
                              json.dump(sc, out)
                          hasContent = True

                        # store adventure information
                        adventure = { "name": data["name"], "img": data["img"], "caption": data["caption"], "description": data["description"], "stats": data["_stats"] }
                        with open(os.path.join(tmppath, dir, "json", "adventures", advPath, "adventure.json"), 'w') as out:
                          json.dump(adventure, out)
                        continue

                      # actors => prefab
                      elif "type" in data and data["type"] == "npc":
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
          ### - assuming that all images in json/ folder are thumbnails, generate thumbnail and keep origin accordingly
          ###
          for root, dirs, files in os.walk(os.path.join(TMP, "mtte", dir, "json")):
            for file in files:
              if file.endswith(".webp") and not "_thumb" in file:
                source = os.path.join(root, file)
                # generate thumbnail
                target = os.path.join(root, os.path.splitext(file)[0] + "_thumb.webp")
                os.system('convert "%s" -resize 400x400^ -gravity center -extent 400x400 "%s"' % (source, target))
                # generate original source
                target = os.path.join(root, os.path.splitext(file)[0] + "_thumb_orig.webp")
                os.rename(source, target)

          # load configuration if exists
          cfg = None
          if os.path.isfile(configPath):
            with open(configPath, "r") as f:
              cfg = json.load(f)
          else:
            print("[ProcessTask] No configuration file found!")
            log += "No configuration file found!\n"

          ###
          ### PRE PROCESSING #4 (maps based on specific extension : introduced for PogsProps)
          ###
          if cfg and "maps" in cfg and cfg["maps"].find("*") == 0:
            for root, dirs, files in os.walk(os.path.join(tmppath, dir)):
              for file in files:
                if file.endswith(cfg["maps"][1:]):
                  map = os.path.join(root, os.path.splitext(file)[0] + ".json")
                  name = (os.path.splitext(os.path.basename(filepath))[0]).replace("-"," ")
                  name = ' '.join(elem.capitalize() for elem in name.split())
                  data = {
                    "name": name,
                    "navigation": False
                  }
                  with open(os.path.join(root, map), "w") as fw:
                    fw.write(json.dumps(data, separators=(',', ':')))

          ###
          ### IMAGE CONVERSION
          ### - converts all images to webp format
          ### - generates thumbnails
          ###
          secs = time()
          os.system("find '%s' -type f \( -iname \*.jpg -o -iname \*.png -o -iname \*.jpeg \) -execdir mogrify -format webp -quality 60 {} \;" % tmppath)
          print("[ProcessTask] Conversion to webp in %.1f seconds" % (time() - secs))
          log += "Conversion to webp in %.1f seconds\n" % (time() - secs)

          ###
          ### AUDIO CONVERSION
          ### - converts all .aac audio to .ogg format
          ###
          secs = time()
          for root, dirs, files in os.walk(tmppath):
            for file in files:
              if(file.lower().endswith(".aac")):
                aacFile = os.path.join(root, file)
                oggFile = os.path.splitext(aacFile)[0] + ".ogg"
                print("Processing " + aacFile)
                os.system("ffmpeg -loglevel quiet -stats -n -i \"%s\" \"%s\"" % (aacFile, oggFile))

          print("[ProcessTask] Conversion from aac to ogg in %.1f seconds" % (time() - secs))
          log += "Conversion from aac to ogg in %.1f seconds\n" % (time() - secs)

          ###
          ### GENERATE MAPS FROM IMAGE or VIDEO
          ###
          if cfg and "maps" in cfg and cfg["maps"].find("*") < 0:
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
                  # replace all %20 or similar (URL decode). Hopefully, this will not break anything else :-)
                  content = unquote(f.read().replace('\n', ''))

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
                  backgroundImage = None
                  # UP TO V9
                  if "img" in data:
                    backgroundImage = data["img"]
                  # FROM V10
                  elif "background" in data and "src" in data["background"]:
                    backgroundImage = data["background"]["src"]

                  if "type" in data and data["type"] == "npc":
                    # nothing more to do
                    print("- Prefab %s ... " % file)
                    log += "- Prefab %s ...\n" % file

                  elif "navigation" in data:
                    # look for default location for scene image (same folder, same name) OR look for "img" in JSON
                    image = os.path.join(root, os.path.splitext(file)[0] + ".webp")
                    if not os.path.isfile(image):
                      if backgroundImage and len(backgroundImage) > 0:
                        idx = root.find('/', len(tmppath)+2)
                        rootFolder = root[0:idx] if idx >= 0 else root
                        imagePath = unquote(os.path.join(rootFolder, backgroundImage.replace("#DEP#", "")))
                        # copy background image file near json file (required to match with thumbnail)
                        if re.match("#DEP\d#", backgroundImage):
                          print("[ProcessTask] Thumbnail is not possible from external pack: %s" % backgroundImage)
                          image = imagePath
                        elif os.path.isfile(imagePath):
                          srcExt = os.path.splitext(imagePath)[1]
                          # special case for animated maps. Also copy the webm/mp4 file (WHY??? => disabling)
                          if srcExt in [".webm", ".mp4"]:
                            #shutil.copyfile(imagePath, os.path.join(root, os.path.splitext(file)[0] + srcExt))
                            shutil.copyfile(os.path.splitext(imagePath)[0] + ".webp", image)
                          else:
                            shutil.copyfile(imagePath, image)
                        else:
                          print("[ProcessTask] - No match and image %s doesn't exist" % imagePath)
                          log += "[ProcessTask] - No match and image %s doesn't exist" % imagePath

                      else:
                        print("[ProcessTask] - Map %s with missing img path. Using empty image" % file)
                        log += "- Map %s with missing img path. Using empty image\n" % file
                        shutil.copyfile("noimage.webp", image)
                        continue

                    # if image path depends on another pack => don't generate thumbnail (assume it was done)
                    imgExternal = re.match("#DEP\d#", backgroundImage) if backgroundImage else None
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
                        # replace img path (except for WebM (video))
                        if not backgroundImage or not backgroundImage.endswith("webm"):
                          # V10
                          if "background" in data and "src" in data["background"]:
                            data["background"]["src"] = "#DEP#%s" % imgPath
                          # V9
                          else:
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
          ### Extract audio information
          ###
          audioInfo = {}
          packBasePath = os.path.join(tmppath, dir)
          for root, dirs, files in os.walk(tmppath):
            for file in files:
              if file.endswith(".ogg") or file.endswith(".mp3"):
                audioFile = os.path.join(root, file)
                relPath = os.path.join(root, file)[len(packBasePath)+1:]

                title = None
                duration = 0
                try:
                  tag = TinyTag.get(audioFile)
                  title = tag.title if tag.title else None
                  duration = round(tag.duration) if tag.duration else 0
                except Exception as e:
                  print("Couldn't extract tag", e)

                if not duration:
                  with audioread.audio_open(audioFile) as f:
                    duration = f.duration

                audioInfo[relPath] = { "duration": duration }
                if title and len(title) > 0:
                  audioInfo[relPath]['title'] = title

                if file.lower().find("loop") > 0:
                  audioInfo[relPath]['loop'] = True

                # Generate audio preview
                if duration > 45:
                  base, _ = os.path.splitext(relPath)
                  previewPath = os.path.join(PREVIEW_FOLDER, container, dir, base + "_preview.ogg")
                  if not os.path.isdir(os.path.dirname(previewPath)):
                    os.makedirs(os.path.dirname(previewPath))
                  command = ["ffmpeg", "-y", "-ss", "30", "-t", "15", "-i", audioFile, previewPath]
                  subprocess.run(command)
                  audioInfo[relPath]['preview'] = True

          if len(audioInfo.keys()) > 0:
            with open(os.path.join(packBasePath, "audioInfo.json"), "w") as out:
              json.dump(audioInfo, out)

          if DEBUG:
            print("Stopping before CLEANUP")
            exit(1)

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
          ### Generate watermarked versions
          ###
          secs = time()
          for root, dirs, files in os.walk(tmppath):
            for file in files:
              if file.endswith(".webp") and not "_thumb" in file:
                baseDir = os.path.join(TMP, "mtte")
                basePath = os.path.join(root, file)[len(baseDir)+1:]
                basePath = os.path.splitext(basePath)[0]
                wmPath = os.path.join(PREVIEW_FOLDER, container, basePath + "_thumb.webp")
                if not os.path.isdir(os.path.dirname(wmPath)):
                  os.makedirs(os.path.dirname(wmPath))
                os.system('convert -thumbnail 100x100 -background none -gravity center "%s" -extent 100x100 /tmp/img.webp' % (os.path.join(root,file)))
                os.system('composite watermark.png /tmp/img.webp -gravity Center "%s"' % (wmPath))

          # maps
          for root, dirs, files in os.walk(tmppath):
            for file in files:
              if file.endswith(".json"):
                imgPath = os.path.splitext(file)[0] + ".webp"
                if os.path.isfile( os.path.join(root, imgPath) ):
                  baseDir = os.path.join(TMP, "mtte")
                  basePath = os.path.join(root, imgPath)[len(baseDir)+1:]
                  basePath = os.path.splitext(basePath)[0]
                  wmPath = os.path.join(PREVIEW_FOLDER, container, basePath + "_thumb.webp")
                  if not os.path.isdir(os.path.dirname(wmPath)):
                    os.makedirs(os.path.dirname(wmPath))
                  os.system('convert -thumbnail 400x400 -background none -gravity center "%s" -extent 400x400 /tmp/img.webp' % (os.path.join(root,imgPath)))
                  os.system('composite watermark-map.png /tmp/img.webp -gravity Center "%s"' % (wmPath))

          # chg permissions
          os.system('chmod 775 -R %s' % (os.path.join(PREVIEW_FOLDER, container)))

          print("[ProcessTask] Watermarked images generated in %.1f seconds" % (time() - secs))
          log += "Watermarked images generated in %.1f seconds\n" % (time() - secs)

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

        ### -------------------------------------------

        # clear existing blobs (if any)
        secs = time()
        if os.path.isdir(dirpath):
          os.system("rm -rf '%s'" % dirpath)

        # move files to target
        secs = time()
        os.system("mv '%s'/* '%s'" % (tmppath, dirpath))
        print("[ProcessTask] Copied to output folder in %.1f seconds" % (time() - secs))

        # cleanup
        if os.path.isdir(tmppath):
          os.system("rm -rf '%s'" % tmppath)

        # update task status
        task["status"] = "done"

      else:
        raise Exception("[ProcessTask] Blob %s doesn't exist ! Skipping..." % blob)

    # Exception handling
    except Exception as e:
      print("[ProcessTask] Exception during processing")
      print(e)
      task["status"] = "failed"

# write statuses
with open(os.path.join(TMP, TASKS_STATUS), "w") as outfile:
  json.dump(tasks, outfile) 

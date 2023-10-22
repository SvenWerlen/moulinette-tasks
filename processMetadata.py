##
## This file generates metadata files for some predefined creators
##
import os
import sys
import re
import json
import logging

# Get required variable environment
TASKS_FILE    = "moulinette-tasks.json"
OUTPUT_FOLDER = os.getenv('OUTPUT_FOLDER') # Output folder (where to download the pack)
TMP = "/tmp/"
DEBUG = False

# Check if debug mode enabled
if len(sys.argv) > 1:
  DEBUG = sys.argv[1] == "true"

# logging information
logging.basicConfig(
    format="[%(levelname)s] %(message)s (%(filename)s, %(funcName)s(), line %(lineno)d)",
    level=logging.WARN,
)
logger = logging.getLogger("moulinette_utils")
logger.setLevel(logging.INFO)

# Check tasks (input)
if not os.path.isfile(os.path.join(TMP, TASKS_FILE)):
  sys.exit("[ProcessMeta] no %s file found" % TASKS_FILE)

tasks = []
with open(os.path.join(TMP, TASKS_FILE)) as f:
  tasks = json.load(f)

if len(tasks) > 0:
  task = tasks[0]
  blob = task["packFile"]
  container = task["container"]
  packName = os.path.splitext(blob)[0]
  targetFolder = os.path.join(OUTPUT_FOLDER, container, packName)
  if DEBUG:
    targetFolder = os.path.join(TMP, "mtte", packName)

  ## Support for Michael Ghelfi
  ## Up to 2 folders => category
  if container == "michaelghelfi":
    logger.info("[ProcessMeta] Generating metadata for Michael Ghelfi")
  
    allSounds = { 'Music': [] }

    metadataPath = os.path.join(targetFolder, "metadata.json")
    if os.path.exists(metadataPath):
      logger.warn(f"[ProcessMeta] Metadata file already exists in pack {blob}")
    else:
      try:
        audios = {}
        with open(os.path.join(targetFolder, "audioInfo.json")) as f:
          audios = json.load(f)

        for path in audios.keys():
          categs = []
          folders = path.split("/")
          if len(folders) > 2:
            categs.append(folders[0].lower())
          if len(folders) > 3:
            categs.append(folders[1].lower())
          # hot fix : Any should be "basic"
          if "any" in categs:
            categs.remove("any")
            categs.push("basic")
          
          allSounds['Music'].append({
            'path': path,
            'categ': categs
          })
        
        logger.info(f"Storing metadata for {len(audios)} entries ...")
        out_file = open(metadataPath, "w")
        json.dump(allSounds, out_file)

      except Exception as e:
        logger.error("[ProcessMeta] Exception raised during processing")
        logger.error(e)
        pass
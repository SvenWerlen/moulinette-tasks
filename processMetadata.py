##
## This file generates metadata files for some predefined creators
##
import os
import sys
import re
import json
import logging

# Get required variable environment
TASKS_FILE   = "moulinette-tasks.json"
TMP = "/tmp/"

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

  ## Support for Michael Ghelfi
  ## Up to 2 folders => category
  if container == "michaelghelfi":
    logger.info("[ProcessMeta] Generating metadata for Michael Ghelfi")
  
    allSounds = { 'Music': [] }

    dir = os.path.splitext(os.path.basename(blob))[0]
    metadataPath = os.path.join(TMP, "mtte", dir, "metadata.json")
    if os.path.exists(metadataPath):
      logger.warn(f"[ProcessMeta] Metadata file already exists in pack {blob}")
    else:
      try:
        audios = {}
        with open(os.path.join(TMP, "mtte", dir, "audioInfo.json")) as f:
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
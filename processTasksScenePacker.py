### ######################################################################
### ######################################################################
### ######################################################################
###
###                         SCENE PACKER INTEGRATION
###
### Trigger: file /scene-packer.info
### Input files:
###  - /data/actors/info.json : list of all included actors
###  - /data/scenes/info.json : list of all included scenes
###
### File structure:
###  - /data/assets/... : all dependent assets
###  - /data/scenes/thumbs : thumbnails of each scene
###
### Data structure:
###  - Actors: id, name, img, hasTokenAttacherData
###  - Scenes: id, name, hasDrawings, hasLights, hasNotes, hasSounds, hasTokens, hasWalls, thumb
###
### Process:
###  - Generates mtte.json
###  - Generates all thumbnails inside /mtte/
###
### Moulinette Cloud
###  - On Azure:
###      - mtte.json
###      - all thumbs (_thumb.web)
###  - On S3:
###      - ZIP file on Space "moulinette"
###      - All but thumbs on Space "mtteblobs"
###
###
### ######################################################################
### ######################################################################
### ######################################################################

import os
import logging

from libs.jsonUtils import fileToJson, jsonToFile
from libs.mediaUtils import convertImage, generateThumnail

logger = logging.getLogger(__name__)

###
### Scene packer process
### - prepare JSON (scene-packer.json)
### - convert scenes thumbnails
###
def processScenePacker(tmppath, dir):

  fileScenes = os.path.join(tmppath, dir, "data", "scenes", "info.json")
  fileActors = os.path.join(tmppath, dir, "data", "actors", "info.json")
  fileMtte = os.path.join(tmppath, dir, "mtte.json")

  # look for main JSON (there must only be 1 single JSON in the root folder)
  baseInfo = None
  for f in os.listdir(os.path.join(tmppath, dir)):
    if f.endswith(".json"):
      baseInfo = fileToJson(os.path.join(tmppath, dir, f))
  if not baseInfo:
    return logger.warning("No main JSON found in pack!")

  baseInfo["scenes"] = []
  baseInfo["actors"] = []

  # create moulinette-specific folder
  os.mkdir(os.path.join(tmppath, dir, "mtte"))

  # STEP 1 : retrieve all scenes
  scenes = fileToJson(fileScenes)
  if not scenes:
    logger.warning("No scenes found (%s)!" % fileScenes)
  else:
    logger.info("Scenes found (%s)!" % fileScenes)
    # check that thumbnails exist and convert them into WEBP format
    for sc in scenes:
      srcThumb = os.path.join(tmppath, dir, "data", sc["thumb"])
      thumbFilename = os.path.basename(sc["id"])

      destPath = os.path.join(tmppath, dir, "mtte", os.path.splitext(thumbFilename)[0] + "_thumb.webp")
      convertImage(srcThumb, destPath)

      # add scene to main info
      del(sc["thumb"])
      baseInfo["scenes"].append(sc)

  # STEP 2 : retrieve all actors/prefabs
  actors = fileToJson(fileActors)
  if not actors:
    logger.warning("No actors found (%s)!" % fileActors)
  else:
    logger.info("Actors found (%s)!" % fileScenes)
    # check that thumbnails exist and convert them into WEBP format
    for a in actors:
      srcImg = os.path.join(tmppath, dir, "data", "assets", a["img"])
      imgFilename = os.path.basename(a["id"])

      destPath = os.path.join(tmppath, dir, "mtte", os.path.splitext(imgFilename)[0] + "_thumb.webp")
      generateThumnail(srcImg, destPath)

      # add scene to main info
      baseInfo["actors"].append(a)

  # generate a new JSON for moulinette purpose
  jsonToFile(fileMtte, baseInfo)


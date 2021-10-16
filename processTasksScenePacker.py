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
  fileMtte = os.path.join(tmppath, dir, "mtte.json")

  # look for main JSON (there must only be 1 single JSON)
  baseInfo = None
  for f in os.listdir(os.path.join(tmppath, dir)):
    if f.endswith(".json"):
      baseInfo = fileToJson(os.path.join(tmppath, dir, f))
  if not baseInfo:
    return logger.warning("No main JSON found in pack!")
  baseInfo["scenes"] = []

  # retrieve all scenes
  scenes = fileToJson(fileScenes)
  if not scenes:
    return logger.warning("No or invalid info file (%s)!" % fileScenes)

  # create moulinette-specific folder
  os.mkdir(os.path.join(tmppath, dir, "mtte"))

  # check that thumbnails exist and convert them into WEBP format
  for sc in scenes:
    srcThumb = os.path.join(tmppath, dir, "data", sc["thumb"])
    thumbFilename = os.path.basename(sc["thumb"])

    destPath = os.path.join(tmppath, dir, "mtte", os.path.splitext(thumbFilename)[0] + "_thumb.webp")
    convertImage(srcThumb, destPath)

    # add scene to main info
    del(sc["thumb"])
    baseInfo["scenes"].append(sc)

  # generate a new JSON for moulinette purpose
  jsonToFile(fileMtte, baseInfo)


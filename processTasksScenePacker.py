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
import json
import logging

from libs.jsonUtils import fileToJson, jsonToFile, dbToJson
from libs.mediaUtils import convertImage, generateThumnail, generateWatermark
from urllib.parse import unquote

logger = logging.getLogger(__name__)

# logging information
logging.basicConfig(
    format="[%(levelname)s] %(message)s (%(filename)s, %(funcName)s(), line %(lineno)d)",
    level=logging.WARN,
)
logger = logging.getLogger("moulinette_utils")
logger.setLevel(logging.INFO)

PREVIEW_FOLDER = os.getenv('PREVIEW_FOLDER')

###
### Scene packer process
### - prepare JSON (scene-packer.json)
### - convert scenes thumbnails
###
def processScenePacker(tmppath, dir, container):

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
    # load scenes
    scenesDB = dbToJson(os.path.join(tmppath, dir, "data", "Scene.json"))

    # check that thumbnails exist and convert them into WEBP format
    for sc in scenes:

      if not sc["thumb"]:
        logger.warning("Skipping scene because thumb is None %s" % sc)
        continue;

      srcThumb = os.path.join(tmppath, dir, "data", sc["thumb"])
      thumbFilename = os.path.basename(sc["id"])

      # thumbnail path
      destPath = os.path.join(tmppath, dir, "mtte", os.path.splitext(thumbFilename)[0] + "_thumb.webp")

      # use background as scene preview
      if sc["id"] in scenesDB and ("img" in scenesDB[sc["id"]] or "background" in scenesDB[sc["id"]]):
        scene = scenesDB[sc["id"]]
        backgroundUrl = scene["background"]["src"] if "background" in scene else scene["img"]
        scenePath = unquote(backgroundUrl) if backgroundUrl else None # unquote in case URL are encoded
        # BeneosBattlemaps : try to search a matching tile
        if not scenePath and "tiles" in scene:
          for t in scenesDB[sc["id"]]["tiles"]:
            if "texture" in t and "src" in t["texture"] and t["texture"]["src"] and t["texture"]["src"].startswith("beneos_battlemaps_assets") and t["texture"]["src"].endswith(".webm"):
              scenePath = t["texture"]["src"]

        if scenePath:
          backgroundPath = os.path.join(tmppath, dir, "data", "assets", scenePath)  
          if os.path.isfile(backgroundPath):
            logger.info("Generating thumbnail for scene: %s (%s)" % (scene["name"], sc["id"]))
            generateThumnail(backgroundPath, destPath, 400, False)
      
      # fallback #2
      if not os.path.isfile(destPath):
        logger.warn(f'Converting fallback thumbnail for scene: {sc["id"]}')
        convertImage(srcThumb, destPath)

      # generate watermarked versions
      wmPath = os.path.join(PREVIEW_FOLDER, container, dir, os.path.basename(destPath))
      if not os.path.isdir(os.path.dirname(wmPath)):
        os.makedirs(os.path.dirname(wmPath))
      generateWatermark(destPath, wmPath, "watermark-map.png", 400)

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
      logger.info("Generating thumbnail for actor: %s" % (imgFilename))
      generateThumnail(srcImg, destPath, 200)

      # generate watermarked versions
      wmPath = os.path.join(PREVIEW_FOLDER, container, dir, os.path.basename(destPath))
      if not os.path.isdir(os.path.dirname(wmPath)):
        os.makedirs(os.path.dirname(wmPath))
      generateWatermark(destPath, wmPath, "watermark.png", 100)

      # add scene to main info
      baseInfo["actors"].append(a)

  # STEP 3 : if adventure => retrieve cover
  if "category" in baseInfo and baseInfo["category"] in ["one-shot", "short-adventure", "long-adventure", "short-campaign", "long-campaign"]:
    # cover must be in /data/cover/ and have filename <cover>.[ext]
    covers = os.listdir(os.path.join(tmppath, dir, "data", "cover"))
    if len(covers) != 1:
      raise Exception("Missing cover!")

    # generate watermarked versions
    coverPath = os.path.join(tmppath, dir, "data", "cover", covers[0])
    thumbPath = os.path.join(PREVIEW_FOLDER, container, dir, "cover_thumb.webp")
    if not os.path.isdir(os.path.dirname(thumbPath)):
      os.makedirs(os.path.dirname(thumbPath))
    generateThumnail(coverPath, thumbPath, 400, True)

  # generate a new JSON for moulinette purpose
  jsonToFile(fileMtte, baseInfo)


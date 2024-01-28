### ######################################################################
### ######################################################################
### ######################################################################
###
###                         SCAN GIT
###
###  
### insert packs(vanity, packFile, packFileSize, packTotalSize, packAssetsCount, baseUrl, token) values('moulinette', 'SvenWerlen-moulinette-obsidian-demo.git', 0,0,0, 'https://github.com/SvenWerlen/moulinette-obsidian-demo.git', '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')
###
### ######################################################################
### ######################################################################
### ######################################################################

import os
import re
import json
import logging
import git
import yaml

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

GIT_FOLDER = "/tmp/mtte-repo/"

# Simple utility function which sets metadata in object if exists (with maximum size)
def setMetadata(obj, meta, key, maxlength):
  if key in meta:
    obj[key] = meta[key][0:maxlength]

###
### Scene packer process
### - prepare JSON (scene-packer.json)
### - convert scenes thumbnails
###
def processScanGIT(repo):

  os.system("rm -rf '%s'" % GIT_FOLDER)
  try:
    git.Repo.clone_from(repo, GIT_FOLDER)
  except Exception as e:
    logger.error(f"Cannot clone GIT repo : {repo}")
    logger.error(e)
    return False

  assets = []
  yamlPattern = re.compile(r"---(?:\n|\r\n?)(.+?)(?:\n|\r\n?)---", re.MULTILINE | re.DOTALL)

  for root, dirs, files in os.walk(GIT_FOLDER):
    for file in files:
      if file.endswith(".md"):
        filepath = os.path.join(root, file)
        with open(filepath) as f:
          data = f.read()
          # by default, asset is a simple type (only the path)
          asset = filepath.replace(GIT_FOLDER,"")

          # look for metadata
          match = yamlPattern.match(data)
          if match:
            try:
              metadata = yaml.load(match.group(1), Loader=yaml.SafeLoader)
              asset = { 'path': asset, 'type': 'md', 'meta': {} }
              setMetadata(asset['meta'], metadata, "type", 20)
              setMetadata(asset['meta'], metadata, "subtype", 20)
              setMetadata(asset['meta'], metadata, "biome", 20)
              setMetadata(asset['meta'], metadata, "description", 50)
              
            except (yaml.YAMLError, exc):
              pass

          assets.append(asset)

  # write statuses
  with open(os.path.join(GIT_FOLDER, "mtte-assets.json"), "w") as outfile:
    json.dump(assets, outfile) 
  
  return True
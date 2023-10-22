import os
import re
import json
import logging
import requests
import urllib.request

START = 301
OUTPUT = "/home/sven/Téléchargements"
URL = "https://tabletopaudio.com/tta_data"
DEF_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.74 Safari/537.36 Edg/79.0.309.43"

# logging information
logging.basicConfig(
    format="[%(levelname)s] %(message)s (%(filename)s, %(funcName)s(), line %(lineno)d)",
    level=logging.WARN,
)
logger = logging.getLogger("moulinette_utils")
logger.setLevel(logging.INFO)

# configure urllib
opener = urllib.request.build_opener()
opener.addheaders = [('User-agent', DEF_USER_AGENT)]
urllib.request.install_opener(opener)

logger.info("Reading list TTA website ...")
headers = {'User-Agent': DEF_USER_AGENT}
response = requests.get(URL, headers=headers)
if response.status_code != 200:
  logger.error("Couldn't download the metadata!")
  exit(1)

allSounds = { 'Music': [] }
data = json.loads(response.text)
data["tracks"].sort(key=lambda track: track['key'])

for sound in data["tracks"]:
  
  # hotfixes
  if sound["link"] == "https://sounds.tabletopaudio.com/326_Distilled_Tropical.mp3":
    sound["link"] = "https://sounds.tabletopaudio.com/327_Distilled_Tropical.mp3"
  if sound["link"] == "https://sounds.tabletopaudio.com/284_Oasis-City.mp3":
    sound["link"] = "https://sounds.tabletopaudio.com/284_Oasis_City.mp3"
  if sound["link"] == "https://sounds.tabletopaudio.com/272_Starforged_Sojourn.mp3":
    sound["link"] = "https://sounds.tabletopaudio.com/272_Starforged_Vault.mp3"
  if sound["link"] == "https://sounds.tabletopaudio.com/265_Shrine_of_Taols.mp3":
    sound["link"] = "https://sounds.tabletopaudio.com/265_Shrine_of_Talos.mp3"
  if sound["link"] == "https://sounds.tabletopaudio.com/146_Frozen_Ice_Castle.mp3":
    sound["link"] = "https://sounds.tabletopaudio.com/146_Floating_Ice_Castle.mp3"

  if sound['key'] < START:
    continue

  batchNr = (sound['key']-1) // 100
  batchName = "music-%03d-%03d" % (batchNr*100 + 1, (batchNr+1)*100)

  # create folder structure
  targetFolder = os.path.join(OUTPUT, batchName, "Music")
  os.makedirs(targetFolder, exist_ok=True)

  filename = sound["link"].split("/").pop()
  targetFile = os.path.join(targetFolder, filename)
  if not os.path.exists(targetFile):
    logger.info(f"Downloading {filename}...")
    urllib.request.urlretrieve(sound["link"], filename)
    os.rename(filename, targetFile)

  # fix track genre
  categ = []
  for genre in sound['track_genre']:
    genres = genre.split(",")
    for g in genres:
      categ.append(g.strip())

  soundEntry = {
    'path': os.path.join("Music", filename),
    'name': sound['track_title'],
    'categ': categ,
    'tags': sound['tags']
  }
  allSounds['Music'].append(soundEntry)

  if sound['key'] % 100 == 0 or sound == data["tracks"][-1]:
    logger.info("Preparing metadata ...")
    out_file = open(os.path.join(OUTPUT, batchName, "metadata.json"), "w")
    json.dump(allSounds, out_file)
    allSounds['Music'] = []
  
logger.info("Done.")

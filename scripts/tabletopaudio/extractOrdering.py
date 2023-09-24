import os
import re
import json
import json5
import logging
from fuzzywuzzy import fuzz

MASTERLIST = "/home/sven/Téléchargements/test/Custom SoundPad - Tabletop Audio_files/custom_sp_master_freq_min.js"
PATH = "/home/sven/Téléchargements/custom_sp.html"
PACK = "/home/sven/Téléchargements/tabletopaudio-pad/"
OUTPUT = "/home/sven/Téléchargements/tabletopaudio-pad/metadata.json"
FOLDERMAP = {
  'alien_starship': "Alien Starship",
  'ancient_greece': "Ancient Greece",
  'atlantis': "Atlantis",
  'castle_raven': "Castle Raven",
  'combat': "Combat",
  'combat_future': "Combat Future",
  'combat_siege': "Combat Siege",
  'cthulhu': "Cthulhu",
  'darkforest': "Dark Forest",
  'deep_six': "Deep Six",
  'desert_planet': "Desert Planet",
  'dm_tools': "DM Tools",
  'dungeon': "Dungeon",
  'film_noir': "Film Noir",
  'future': "Future City",
  'hell_planet': "Hell Planet",
  'house': "House on the Hill",
  'ice_planet': "Ice Planet",
  'jungle_planet': "Jungle Planet",
  'monster_pack1': "Monster Pack",
  'oldetowne': "Olde Towne",
  'sail': "Age of Sail",
  'secret_agent': "Secret Agent",
  'starship': "Starship",
  'steampunk': "Steampunk",
  'tavern': "Tavern",
  'true_west': "True West",
  'vampire': "Vampire",
  'vikings': "Vikings",
  'wasteland': "Wasteland",
  'weirder_things': "Weirder Things",
  'wuxia': "Wuxia",
}

CATEGMAP = {
  'ev': "Event",
  'bg': "B/G",
  'tn': "Tone",
  'mu': "Music"
}

# logging information
logging.basicConfig(
    format="[%(levelname)s] %(message)s (%(filename)s, %(funcName)s(), line %(lineno)d)",
    level=logging.WARN,
)
logger = logging.getLogger("moulinette_utils")
logger.setLevel(logging.INFO)


# dict to quickly search a sound (by ID and by soundfile)
soundsById = {}
soundsByFile = {}

##
## Utility method which cleans a filename (for matching purposes)
## 
def clean(filename):
  return filename.lower().replace("music_", "").replace("_loop", "").replace(".mp3", "").replace(".ogg", "").replace("_", " ")

##
## Utility method which tries to match a sound by filename and folder
##
def matchSound(folder, filename):
  # retrieve matching folder
  folderMatch = None
  for k, v in FOLDERMAP.items():
    if v == folder:
      folderMatch = k
      break
  
  if not folderMatch:
    logger.error(f'No folder matching {folder} ({filename})!')
    exit(1)
  
  cleanMatch = clean(filename)
  
  # try to find all filename matches
  best = None
  bestDist = len(cleanMatch)
  
  matchFolder = True
  while(True):
    for id, sound in soundsById.items():
      if matchFolder and sound["sp"] != folderMatch:
        continue

      # check full match
      dist1 = fuzz.token_set_ratio(cleanMatch, clean(sound["soundFile"]))
      dist2 = fuzz.token_set_ratio(cleanMatch, sound["name"].lower())
      dist = max(dist1, dist2)
      #print(dist1, cleanMatch, sound["soundFile"])
      #print(dist2, cleanMatch, sound["name"])
      if not best or bestDist < dist:
        best = sound
        bestDist = dist
    
    # not good enough match? => try again in all folders
    if matchFolder and bestDist < 80:
      matchFolder = False
      continue
    break

  return [best, bestDist]


##
## Read the masterlist from Tabletop Audio website (custom SoundPad)
## It provides usefull information about the sounds. Example :
## {'id': '1', 'chk': 1, 'vol': '.35', 'name': 'Low Wind', 'sp': 'dungeon', 'path': 'dungeonPath', 'soundFile': 'dungeon_bg1.ogg', 'iconFile': 'wind_icon2.png', 'freq': 0}
##
logger.info("Reading masterlist ...")

if os.path.exists(MASTERLIST):
  f = open(MASTERLIST,"r")
  html = f.readlines()
  search = re.search("var masterList=([^;]+)", str(html), re.IGNORECASE)
  if search:
    #print(search.group(1))
    match = search.group(1).replace('iconPath+"', '"').replace(':chk,',':1,')
    match = re.sub('path:([^,]+),', 'path:"\\1",', match)
    list = json5.loads(match)
    for el in list:
      if not 'id' in el:
        continue
      
      # check for duplicates!
      if el['id'] in soundsById:
        logger.error(f'Duplicated sound with id {el["id"]}')
        logger.error(el)
        exit(1)
      soundFile = f'{el["path"]}:{el["soundFile"]}'
      if soundFile in soundsByFile:
        logger.error(f'Duplicated sound with file {soundFile}')
        logger.error(el)
        exit(1)

      # remove x2, x3, ... from name
      el['name'] = re.sub(' x?[0-9]', "", el['name'])

      soundsById[el['id']] = el
      soundsByFile[el['soundFile']] = el

logger.info(f'{len(soundsById)} sounds found!')

##
## Read all available sounds from Tabletop Audio (prepared by Tim)
## Those are the files which are available in Moulinette
##
allSounds = {}
logger.info("Fetching all sounds ...")
for root, subfolders, files in os.walk(PACK):
  for file in files:
    if file.endswith(".ogg") or file.endswith(".mp3"):
      filePath = str(os.path.join(root, file))
      subFolder = os.path.dirname(filePath)[len(PACK):]
      if not subFolder in allSounds:
        allSounds[subFolder] = []
      allSounds[subFolder].append({ "path" : file })


##
## Read all the soundpads from Tabletop Audio
## Provides the ordering of the sounds on the page and the category
##
logger.info("Reading soundpads ...")
index = 0
if os.path.exists(PATH):
  f = open(PATH,"r")
  html = f.readlines()
  
  matches = re.findall('<span class="(.{2})-sound sound-select[^"]*" data-sp="([^"]*)" data-sound="(\d+)" [^>]*>([^<]*)</span>', str(html), re.IGNORECASE)
  for match in matches:
    category = match[0]
    soundpad = match[1]
    id       = match[2]
    title    = match[3]

    # add information about category
    sound = soundsById[id]
    sound["category"] = category

    if int(id) != index+1:
      #print("ERROR", id, index)
      continue
    index += 1

    # retrieve ID in masterlist
    if not id in soundsById:
      logger.error(f'{id} not found')
      continue
    
    # check if sound exists
    if not sound["sp"] in FOLDERMAP:
      logger.error(f"Folder map doesn't exist for {sound['sp']}")
      exit(1)
  
##
## Add category, index, name and volume to all sound files
##
logger.info("Preparing metadata ...")
for folder, sounds in allSounds.items():
  for sound in sounds:
    match = matchSound(folder, sound['path'])
    #if match[1] < 90:
    #  print(f"{folder}/{sound['path']} ==> {match[0]['name']} ({match[0]['soundFile']} - {match[1]})")    
    
    name = match[0]['name']
    
    # check if filename ends with digit => #1 #2 #3...
    varMatch = re.match("^.*([0-9])\.(ogg|mp3)$", sound['path'])
    if varMatch:
      name += f' #{varMatch.group(1)}'
    
    sound['name'] = name
    sound['nameAlt'] = clean(sound['path']).title()
    sound['categ'] = [CATEGMAP[match[0]['category']]]
    sound['order'] = int(match[0]['id'])
    sound['path'] = os.path.join(folder, sound['path'])

out_file = open(OUTPUT, "w")
json.dump(allSounds, out_file)
logger.info("Done.")
##
## This script:
##

import os
import re
import json
import requests

PATH = "/home/sven/projets/dnd-test/"

titlePattern = re.compile("^#([^#].*)$")
assets = []

for root, dirs, files in os.walk(PATH):
  for file in files:
    if file.endswith(".md"):
      filepath = os.path.join(root, file)
      with open(filepath) as f:
        content = f.readlines()
        titles = list(filter(lambda l: titlePattern.match(l), content))
        if(len(titles) == 0):
            print("Invalid file", filepath)
            continue
      
        title_search = titlePattern.search(titles[0])
        if title_search:
          title = title_search.group(1).strip()
          assets.append(filepath.replace(PATH,""))

print(assets)

import os
import sys
import re
import requests
import json
import zipfile
import shutil
from time import time

if len(sys.argv) < 3:
  print("Usage: %s <db file> <out folder>" % sys.argv[0])
  exit(1)

FILE = sys.argv[1]
OUT = sys.argv[2]

print("Opening %s" % FILE)
with open(FILE, 'r') as f:
  for line in f:
    data = json.loads(line)
    if "name" in data:
      print(data["name"])
      filename = re.sub('[^0-9a-zA-Z]+', '-', data["name"]).lower()
      with open(os.path.join(OUT, filename + ".json"), 'w') as out:
        json.dump(data, out)
      

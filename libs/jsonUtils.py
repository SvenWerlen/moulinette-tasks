import os
import json

##
## Python utilities for manipulating JSON
##


##
## Parses a JSON file and return it as object
## Returns None if file doesn't exist
##
def fileToJson(filepath):
  data = None
  if os.path.isfile(filepath):
    with open(filepath, 'r') as f:
      data = json.load(f)
  return data

##
## Writes JSON data to specified file
##
def jsonToFile(filepath, data):
  with open(filepath, "w") as f:
    f.write(json.dumps(data, separators=(',', ':')))


##
## Read a FoundryVTT DB file and retur a dict
##
def dbToJson(filepath):
  data = {}
  if os.path.isfile(filepath):
    with open(filepath, 'r') as f:
      lines = f.readlines()
      for line in lines:
        try:
          jData = json.loads(line)
          for sc in jData:
            if "id" in sc:
              data[sc["id"]] = sc
            if "_id" in sc:
              data[sc["_id"]] = sc
        except:
          pass
  return data

## #################################################
## This scripts retrieves all tasks from Moulinette Cloud
## It generates a JSON file in /tmp, ready to be processed by progressTasks
##
## Author: Sven Werlen
## #################################################

import os
import sys
import requests
import json
import zipfile
from time import time

# Get environment variables
MOULINETTE_API        = os.getenv('MOULINETTE_API')     # Moulinette API endpoint
MOULINETTE_SECRET_KEY = os.getenv('MOULINETTE_SECRET')  # Mouilnette secret key for API endpoint

# Constants
TMP = "/tmp/"

# Check environment variables
if not MOULINETTE_API or not MOULINETTE_SECRET_KEY:
  sys.exit("[ProcessTasks] Missing environment variables")

# Get authorization code
response = requests.post(url = MOULINETTE_API + "/login", data = json.dumps({"secret" : MOULINETTE_SECRET_KEY}), headers = {"Content-Type": "application/json"})

if response.status_code != 201:
  sys.exit("[ProcessTasks] Authorization failed! " + response.text)

data = response.json()
token = data["access_token"]

# Mark task as completed
response = requests.get(url = MOULINETTE_API + "/tasks" , headers = {"Content-Type": "application/json", "Authorization": "Bearer " + token})
if response.status_code != 200:
  sys.exit("[ProcessTasks] Retrieval of tasks failed. " + response.text)

with open(os.path.join(TMP, "moulinette-tasks.json"), "w") as outfile:
  json.dump(response.json(), outfile)


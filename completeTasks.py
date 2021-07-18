import os
import sys
import requests
import json
import zipfile
from time import time

# Get environment variables
MOULINETTE_API        = os.getenv('MOULINETTE_API')     # Moulinette API endpoint
MOULINETTE_SECRET_KEY = os.getenv('MOULINETTE_SECRET')  # Mouilnette secret key for API endpoint
TASK_ID               = os.getenv('TASK_ID')            # Task ID to process (production)

# Constants
TASKS_STATUS = "moulinette-tasks-status.json"
TMP = "/tmp/"

# Check environment variables
if not MOULINETTE_API or not MOULINETTE_SECRET_KEY:
  sys.exit("[CompleteTasks] Missing environment variables")

# Check tasks (output)
if not os.path.isfile(os.path.join(TMP, TASKS_STATUS)):
  sys.exit("[CompleteTasks] no %s file found" % TASKS_STATUS)

# Get authorization code
response = requests.post(url = MOULINETTE_API + "/login", data = json.dumps({"secret" : MOULINETTE_SECRET_KEY}), headers = {"Content-Type": "application/json"})

if response.status_code != 201:
  sys.exit("[CompleteTasks] Authorization failed! " + response.text)

data = response.json()
token = data["access_token"]

tasks = []
with open(os.path.join(TMP, TASKS_STATUS)) as f:
  tasks = json.load(f)

for task in tasks:
  print("[CompleteTasks] Delete task #%d" % (task["id"]))
  
  response = requests.delete(url = MOULINETTE_API + "/task/%s" % task["id"], headers = {"Content-Type": "application/json", "Authorization": "Bearer " + token})
  if response.status_code != 200:
    sys.exit("[CompleteTasks] Task deletion failed. " + response.text)



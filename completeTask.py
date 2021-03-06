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


# Check environment variables
if not MOULINETTE_API or not MOULINETTE_SECRET_KEY:
  sys.exit("[CompleteTask] Missing environment variables")

# Get authorization code
response = requests.post(url = MOULINETTE_API + "/login", data = json.dumps({"secret" : MOULINETTE_SECRET_KEY}), headers = {"Content-Type": "application/json"})

if response.status_code != 201:
  sys.exit("[CompleteTask] Authorization failed! " + response.text)

data = response.json()
token = data["access_token"]

# Mark task as completed
response = requests.delete(url = MOULINETTE_API + "/task/%s" % TASK_ID, headers = {"Content-Type": "application/json", "Authorization": "Bearer " + token})
if response.status_code != 200:
  sys.exit("[CompleteTask] Task deleting failed. " + response.text)

print("[CompleteTask] Task completed!")

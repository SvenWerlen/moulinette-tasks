###
### This scripts gets the task to process and downloads the pack
###
import os
import sys
import json
import shutil
import requests
from azurelib import downloadBlob
from azure.storage.blob import BlobServiceClient, AccountSasPermissions, ResourceTypes, generate_account_sas, generate_container_sas

# Get required environment variables
MOULINETTE_API           = os.getenv('MOULINETTE_API')            # Moulinette API endpoint
MOULINETTE_SECRET_KEY    = os.getenv('MOULINETTE_SECRET')         # Mouilnette secret key for API endpoint
OUTPUT_FOLDER            = os.getenv('OUTPUT_FOLDER')             # Output folder (where to download the pack)

AZURE_STORAGE_ACCOUNT    = os.getenv('AZURE_STORAGE_ACCOUNT')     # Azure storage account
AZURE_STORAGE_ACCESS_KEY = os.getenv('AZURE_STORAGE_ACCESS_KEY')  # Azure storage access key
TASK_FILE                = os.getenv('LOCAL_FILE')                # Local file (development only)
TASK_TYPE                = os.getenv('LOCAL_TYPE')                # Task type (development only)
TASK_ID                  = os.getenv('TASK_ID')                   # Task ID to process (production)


# Expected task information
# Example: { "type": "extract", "data": { "blob": "test.zip" } }
task = {}

if not OUTPUT_FOLDER or not os.path.isdir(OUTPUT_FOLDER):
  sys.exit("[DownloadPack] %s is not a valid directory" % OUTPUT_FOLDER)

if TASK_FILE and not os.path.isfile(TASK_FILE):
  sys.exit("[DownloadPack] %s is not a valid file" % TASK_FILE)

########################################################################
# Use case for PRODUCTION (restrieves information from task on server)
########################################################################
if MOULINETTE_API and MOULINETTE_SECRET_KEY and TASK_ID:
  # Get authorization code
  response = requests.post(url = MOULINETTE_API + "/login", data = json.dumps({"secret" : MOULINETTE_SECRET_KEY}), headers = {"Content-Type": "application/json"})

  if response.status_code != 201:
    sys.exit("[DownloadPack] Authorization failed! " + response.text)

  data = response.json()
  token = data["access_token"]

  # Get tasks
  response = requests.get(url = MOULINETTE_API + "/task/" + TASK_ID, headers = {"Content-Type": "application/json", "Authorization": "Bearer " + token})

  if response.status_code != 200:
    sys.exit("[DownloadPack] Get tasks failed! " + response.text)

  task = response.json()
  client = BlobServiceClient(account_url="https://%s.blob.core.windows.net/" % AZURE_STORAGE_ACCOUNT, credential=AZURE_STORAGE_ACCESS_KEY)
  downloadBlob(client, task["data"]["container"], task["data"]["blob"], OUTPUT_FOLDER)

########################################################################
# Use case for DEVELOPMENT (restrieves information from LOCAL_FILE and TASK_TYPE environment variables)
########################################################################
elif TASK_TYPE and TASK_FILE:
  shutil.copy(TASK_FILE, OUTPUT_FOLDER)
  task = { "type": TASK_TYPE, "data": { "blob": os.path.basename(TASK_FILE) } }
  
else:
  sys.exit("[DownloadPack] Missing environment variables")


########################################################################
# Write json for later usage
########################################################################

with open(os.path.join(OUTPUT_FOLDER, "task.json"), 'w') as file:
  json.dump(task, file)

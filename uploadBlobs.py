###
### This scripts gets the task to process and downloads the pack
###
import os
import sys
import json
import shutil
import requests
from azurelib import deletePack, uploadPackFolder
from azure.storage.blob import BlobServiceClient, AccountSasPermissions, ResourceTypes, generate_account_sas, generate_container_sas

# Get required environment variables
OUTPUT_FOLDER            = os.getenv('OUTPUT_FOLDER')             # Output folder (where to download the pack)
AZURE_STORAGE_ACCOUNT    = os.getenv('AZURE_STORAGE_ACCOUNT')     # Azure storage account
AZURE_STORAGE_ACCESS_KEY = os.getenv('AZURE_STORAGE_ACCESS_KEY')  # Azure storage access key

# Constants
TASKS_STATUS = "moulinette-tasks-status.json"
TMP = "/tmp/"

# Check environment variables
if not AZURE_STORAGE_ACCOUNT or not AZURE_STORAGE_ACCESS_KEY:
  sys.exit("[UploadBlobs] environment variables missing")

# Check output folder
if not OUTPUT_FOLDER or not os.path.isdir(OUTPUT_FOLDER):
  sys.exit("[UploadBlobs] %s is not a valid directory" % OUTPUT_FOLDER)

# Check tasks (input)
if not os.path.isfile(os.path.join(TMP, TASKS_STATUS)):
  sys.exit("[UploadBlobs] no %s file found" % TASKS_STATUS)

# Expected task information
# Example: { "type": "extract", "data": { "blob": "test.zip" } }
tasks = []
with open(os.path.join(TMP, TASKS_STATUS)) as f:
  tasks = json.load(f)

for task in tasks:
  print("[UploadBlobs] Updating blobs for %s from task #%d" % (task["packFile"], task["id"]))

  client = BlobServiceClient(account_url="https://%s.blob.core.windows.net/" % AZURE_STORAGE_ACCOUNT, credential=AZURE_STORAGE_ACCESS_KEY)
  folderPath = os.path.join(OUTPUT_FOLDER, task["container"], os.path.splitext(task["packFile"])[0])

  # Delete pack if already exists in Azure
  deletePack(client, task["container"], os.path.basename(folderPath))

  # Upload all files for that pack
  uploadPackFolder(client, task["container"], folderPath)

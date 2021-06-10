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



if not OUTPUT_FOLDER or not os.path.isfile(os.path.join(OUTPUT_FOLDER, "task.json")):
  sys.exit("[ProcessTask] %s is not a valid directory or task.json not found" % OUTPUT_FOLDER)

# Expected task information
# Example: { "type": "extract", "data": { "blob": "test.zip" } }
task = {}
with open(os.path.join(OUTPUT_FOLDER, "task.json")) as f:
  task = json.load(f)

client = BlobServiceClient(account_url="https://%s.blob.core.windows.net/" % AZURE_STORAGE_ACCOUNT, credential=AZURE_STORAGE_ACCESS_KEY)

folderPath = os.path.join(OUTPUT_FOLDER, os.path.splitext(task["data"]["blob"])[0])

# Clean
deletePack(client, task["data"]["container"], os.path.basename(folderPath))

# Upload
uploadPackFolder(client, task["data"]["container"], folderPath)

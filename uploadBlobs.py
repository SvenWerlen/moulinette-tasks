###
### This scripts gets the task to process and downloads the pack
###
import os
import sys
import json
import shutil
import requests
import logging

from azure.storage.blob import BlobServiceClient
from moulinette_utils.storage.azure import MoulinetteStorageAzure

# Get required environment variables
OUTPUT_FOLDER            = os.getenv('OUTPUT_FOLDER')             # Output folder (where to download the pack)
AZURE_STORAGE_ACCOUNT    = os.getenv('AZURE_STORAGE_ACCOUNT')     # Azure storage account
AZURE_STORAGE_ACCESS_KEY = os.getenv('AZURE_STORAGE_ACCESS_KEY')  # Azure storage access key

S3_STORAGE_ACCOUNT    = os.getenv('S3_STORAGE_ACCOUNT')     # S3 storage account
S3_STORAGE_ACCESS_KEY = os.getenv('S3_STORAGE_ACCESS_KEY')  # S3 storage access key

# logging information
logging.basicConfig(
    format="[%(levelname)s] %(message)s (%(filename)s, %(funcName)s(), line %(lineno)d)",
    level=logging.WARN,
)
logger = logging.getLogger("moulinette_utils")
logger.setLevel(logging.INFO)


# Constants
TASKS_STATUS = "moulinette-tasks-status.json"
TMP = "/tmp/"

# Check environment variables
if not AZURE_STORAGE_ACCOUNT or not AZURE_STORAGE_ACCESS_KEY or not S3_STORAGE_ACCOUNT or not S3_STORAGE_ACCESS_KEY:
  sys.exit("[UploadBlobs] environment variables missing")

# Check output folder
if not OUTPUT_FOLDER or not os.path.isdir(OUTPUT_FOLDER):
  sys.exit("[UploadBlobs] %s is not a valid directory" % OUTPUT_FOLDER)

# Check tasks (input)
if not os.path.isfile(os.path.join(TMP, TASKS_STATUS)):
  sys.exit("[UploadBlobs] no %s file found" % TASKS_STATUS)

tasks = []
with open(os.path.join(TMP, TASKS_STATUS)) as f:
  tasks = json.load(f)

# Only process 1 task at a time
if len(tasks) > 0:
  task = tasks[0]
  
  if task["status"] and task["status"] == "done":

    ############################################################################################################################
    ################################## TASK Extract ############################################################################
    ############################################################################################################################
    if task["type"] == "extract" or task["type"] == "byoa":
    
      print("[UploadBlobs] Updating blobs for %s from task #%d" % (task["packFile"], task["id"]))

      packName = os.path.splitext(task["packFile"])[0]
      folderPath = os.path.join(OUTPUT_FOLDER, task["container"], packName)

      # Manage assets on remote storage
      client = BlobServiceClient(account_url="https://%s.blob.core.windows.net/" % AZURE_STORAGE_ACCOUNT, credential=AZURE_STORAGE_ACCESS_KEY)
      storage = MoulinetteStorageAzure(client, task["container"])
      storage.deleteAssets(packName)
      storage.uploadAssets(folderPath)

      # Delete all temp files
      shutil.rmtree(folderPath)

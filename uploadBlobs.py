###
### This scripts gets the task to process and downloads the pack
###
import os
import sys
import json
import shutil
import requests
import boto3
from azurelib import deletePack, uploadPackFolder
from s3lib import deleteS3Pack, uploadS3PackFolder
from azure.storage.blob import BlobServiceClient, AccountSasPermissions, ResourceTypes, generate_account_sas, generate_container_sas

# Get required environment variables
OUTPUT_FOLDER            = os.getenv('OUTPUT_FOLDER')             # Output folder (where to download the pack)
AZURE_STORAGE_ACCOUNT    = os.getenv('AZURE_STORAGE_ACCOUNT')     # Azure storage account
AZURE_STORAGE_ACCESS_KEY = os.getenv('AZURE_STORAGE_ACCESS_KEY')  # Azure storage access key

S3_STORAGE_ACCOUNT    = os.getenv('S3_STORAGE_ACCOUNT')     # S3 storage account
S3_STORAGE_ACCESS_KEY = os.getenv('S3_STORAGE_ACCESS_KEY')  # S3 storage access key


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
    ################################## TASK BYOA ###############################################################################
    ############################################################################################################################
    if task["type"] == "byoa":
      print("[UploadBlobs] Updating blobs for %s from task #%d" % (task["packFile"], task["id"]))

      session = boto3.session.Session()
      client = session.client('s3',
        region_name='nyc3',
        endpoint_url='https://nyc3.digitaloceanspaces.com',
        aws_access_key_id=S3_STORAGE_ACCOUNT,
        aws_secret_access_key=S3_STORAGE_ACCESS_KEY)

      bucketName = "mtte" + task["container"]
      try:
        client.head_bucket(Bucket=bucketName)
      except: 
        client.create_bucket(Bucket=bucketName)

      folderPath = os.path.join(OUTPUT_FOLDER, task["container"], os.path.splitext(task["packFile"])[0])

      # Delete pack if already exists in Azure
      deleteS3Pack(client, bucketName, os.path.basename(folderPath))

      # Upload all files for that pack
      uploadS3PackFolder(client, bucketName, folderPath)

      # Delete all temp files
      shutil.rmtree(folderPath)

    ############################################################################################################################
    ################################## TASK Extract ############################################################################
    ############################################################################################################################
    elif task["type"] == "extract":
    
      print("[UploadBlobs] Updating blobs for %s from task #%d" % (task["packFile"], task["id"]))

      client = BlobServiceClient(account_url="https://%s.blob.core.windows.net/" % AZURE_STORAGE_ACCOUNT, credential=AZURE_STORAGE_ACCESS_KEY)
      folderPath = os.path.join(OUTPUT_FOLDER, task["container"], os.path.splitext(task["packFile"])[0])

      # Delete pack if already exists in Azure
      deletePack(client, task["container"], os.path.basename(folderPath))

      # Upload all files for that pack
      uploadPackFolder(client, task["container"], folderPath)

      # Delete all temp files
      shutil.rmtree(folderPath)

import os
import sys
import boto3
import unittest
import logging

from azure.storage.blob import BlobServiceClient
from moulinette_utils.storage.azure import MoulinetteStorageAzure
from moulinette_utils.storage.s3 import MoulinetteStorageS3

S3_STORAGE_ACCOUNT       = os.getenv('S3_STORAGE_ACCOUNT')
S3_STORAGE_ACCESS_KEY    = os.getenv('S3_STORAGE_ACCESS_KEY')

if not S3_STORAGE_ACCOUNT or not S3_STORAGE_ACCESS_KEY:
  sys.exit("Environment variables not set!")

# logging information
logging.basicConfig(
    format="[%(levelname)s] %(message)s (%(filename)s, %(funcName)s(), line %(lineno)d)",
    level=logging.WARN,
)
logger = logging.getLogger("moulinette_utils")
logger.setLevel(logging.INFO)


# S3 Storage
session = boto3.session.Session()
clientS3 = session.client('s3',
  region_name='nyc3', endpoint_url='https://nyc3.digitaloceanspaces.com',
  aws_access_key_id=S3_STORAGE_ACCOUNT,
  aws_secret_access_key=S3_STORAGE_ACCESS_KEY)

folder = os.path.basename(sys.argv[1])
files = os.listdir(sys.argv[1])

storage = MoulinetteStorageS3(clientS3, "moulinette")
storage.initialize()

for f in files:
  storage.uploadAsset(os.path.join(sys.argv[1], f), folder)

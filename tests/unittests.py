import os
import sys
import boto3
import unittest

from azure.storage.blob import BlobServiceClient
from moulinette_utils.storage.azure import MoulinetteStorageAzure
from moulinette_utils.storage.s3 import MoulinetteStorageS3

AZURE_STORAGE_ACCOUNT    = os.getenv('AZURE_STORAGE_ACCOUNT')
AZURE_STORAGE_ACCESS_KEY = os.getenv('AZURE_STORAGE_ACCESS_KEY')

S3_STORAGE_ACCOUNT       = os.getenv('S3_STORAGE_ACCOUNT')
S3_STORAGE_ACCESS_KEY    = os.getenv('S3_STORAGE_ACCESS_KEY')

if not AZURE_STORAGE_ACCOUNT or not AZURE_STORAGE_ACCESS_KEY or not S3_STORAGE_ACCOUNT or not S3_STORAGE_ACCESS_KEY:
  sys.exit("Environment variables not set!\nUsage: source ../environment.sh && python3 unittests.py")

# Azure Blob Storage Account
clientAzure = BlobServiceClient(
  account_url="https://%s.blob.core.windows.net/" % AZURE_STORAGE_ACCOUNT,
  credential=AZURE_STORAGE_ACCESS_KEY)

# S3 Storage
session = boto3.session.Session()
clientS3 = session.client('s3',
  region_name='nyc3', endpoint_url='https://nyc3.digitaloceanspaces.com',
  aws_access_key_id=S3_STORAGE_ACCOUNT,
  aws_secret_access_key=S3_STORAGE_ACCESS_KEY)


class TestS3(unittest.TestCase):

  ## delete / upload / list / delete
  def happyPath(self, storage):
    storage.initialize()

    deleted1 = storage.deleteAssets("testpack.zip")
    self.assertEqual(deleted1, 0)

    storage.uploadAssets("testpack")

    packs = storage.getAvailablePacks()
    self.assertEqual(len(packs), 1)
    self.assertEqual(packs[0], "testpack")

    assets = storage.getAssets("testpack.zip")
    self.assertEqual(len(assets["assets"]), 3)
    self.assertEqual(len(assets["data"]), 1)
    self.assertEqual(assets["size"], 481439)

    deleted2 = storage.deleteAssets("testpack.zip")
    self.assertEqual(deleted2, 4)

    success = storage.uploadAsset("other/screenshot2.webp", "testpack/othertests")
    self.assertTrue(success)

    assets = storage.getAssets("testpack")
    self.assertEqual(len(assets["assets"]), 1)
    success = storage.deleteAsset("testpack/othertests/screenshot2.webp")
    self.assertTrue(success)
    success = storage.deleteAsset("testpack/othertests/screenshot3.webp")
    self.assertFalse(success)
    assets = storage.getAssets("testpack")
    self.assertEqual(len(assets["assets"]), 0)

  def test_happyPath(self):
    self.happyPath(MoulinetteStorageS3(clientS3, "moulinettetests"))
    self.happyPath(MoulinetteStorageAzure(clientAzure, "moulinettetests"))


if __name__ == '__main__':
    unittest.main()

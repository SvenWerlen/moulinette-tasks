###
### This scripts uploads the backups on Azure Storage
### - Copies entire folder (#1) into container (#2)
### - Doesn't overwrite existing files
###
import os
import sys
import shutil
import logging

from azure.storage.blob import BlobServiceClient
from moulinette_utils.storage.azure import MoulinetteStorageAzure

AZURE_STORAGE_ACCOUNT    = os.getenv('AZURE_STORAGE_ACCOUNT_BACKUPS')   # Azure storage account for backups
AZURE_STORAGE_ACCESS_KEY = os.getenv('AZURE_STORAGE_ACCESS_KEY_BACKUPS') # Azure storage access key for backups

# logging information
logging.basicConfig(
    format="[%(levelname)s] %(message)s (%(filename)s, %(funcName)s(), line %(lineno)d)",
    level=logging.ERROR,
)
logger = logging.getLogger("moulinette_utils")
logger.setLevel(logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Check programm arguments
if len(sys.argv) != 3:
  sys.exit("Usage: %s [source] [container]" % sys.argv[0])

# Check environment variables
if not AZURE_STORAGE_ACCOUNT or not AZURE_STORAGE_ACCESS_KEY:
  sys.exit("Missing environment variables")


source = sys.argv[1]
container = sys.argv[2]
logger.info("Backup task: %s => %s (%s)" % (source, AZURE_STORAGE_ACCOUNT, container))

# Check that target path is a valid folder
if not os.path.isdir(source):
  sys.exit("Invalid folder %s" % source)

# Upload files
packName = source[len(os.path.dirname(source))+1:]

client = BlobServiceClient(account_url="https://%s.blob.core.windows.net/" % AZURE_STORAGE_ACCOUNT, credential=AZURE_STORAGE_ACCESS_KEY)
storage = MoulinetteStorageAzure(client, container)
storage.deleteAssets(packName)
storage.uploadAssets(source)

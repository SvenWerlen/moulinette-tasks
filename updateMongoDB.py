###
### This scripts gets the task to update MongoDB with all the assets
###
import os
import sys
import json
from pymongo import MongoClient
import logging

# Get required environment variables
OUTPUT_FOLDER = os.getenv('OUTPUT_FOLDER') # Output folder (where data is ready for upload)
MONGODEV      = os.environ['MONGO_DEV'] == "1"
MONGODB_URI   = f"mongodb+srv://{os.environ['MONGO_CREDS']}/?retryWrites=true&w=majority"

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

# Check output folder
if not OUTPUT_FOLDER or not os.path.isdir(OUTPUT_FOLDER):
  sys.exit(f'[UpdateMongoDB] {OUTPUT_FOLDER} is not a valid directory')

# Check tasks (input)
if not os.path.isfile(os.path.join(TMP, TASKS_STATUS)):
  sys.exit(f'[UpdateMongoDB] no {TASKS_STATUS} file found')

tasks = []
with open(os.path.join(TMP, TASKS_STATUS)) as f:
  tasks = json.load(f)

# Only process 1 task at a time
if len(tasks) > 0:
  task = tasks[0]
  
  if task["status"] and task["status"] == "done":
    logger.info(f'Updating DB for {task["packFile"]} from task {task["id"]}')
    
    packName = os.path.splitext(task["packFile"])[0]
    assetsFile = os.path.join(OUTPUT_FOLDER, task["container"], packName, "json", "assets.json")

    if not os.path.isfile(assetsFile):
      logger.info(f'No {assetsFile} file found')
    else:
      with open(assetsFile, "r") as f:
        assets = json.load(f)
        if not assets or len(assets) == 0:
          logger.info(f'No asset to be indexed for that pack')
        else:
          client = MongoClient(MONGODB_URI)
          client.admin.command('ping')
          db = client.moulinettedev if MONGODEV else client.moulinette
          coll = db.assets
          
          # removing existing entries
          unique = { 'creatorId': task["container"], 'packFile': task["packFile"] }
          result = coll.delete_many(unique)
          logger.info(f"{result.deleted_count} documents ont été supprimés avec succès (MongoDB).")

          # upload to MongoDB
          result = coll.insert_many(assets)
          if result.inserted_ids:
            logger.info(f"{len(result.inserted_ids)} documents insérés avec succès (MongoDB).")
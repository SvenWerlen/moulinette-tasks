import os
import sys
import json
import requests

# Environment variables
OUTPUT_FOLDER = os.getenv('OUTPUT_FOLDER')
DISCORD_HOOK = os.getenv('DISCORD_HOOK')

# Constants
TASKS_STATUS = "moulinette-tasks-status.json"
TMP = "/tmp/"

# Check parameters
if len(sys.argv) != 2:
  sys.exit("[CompleteTasks] Missing status")
OK = sys.argv[1]

# Check environment variables
if not OUTPUT_FOLDER or not DISCORD_HOOK:
  sys.exit("[NotifyDiscord] Missing environment variables")

# Check tasks (output)
if not os.path.isfile(os.path.join(TMP, TASKS_STATUS)):
  sys.exit("[NotifyDiscord] no %s file found" % TASKS_STATUS)

tasks = []
with open(os.path.join(TMP, TASKS_STATUS)) as f:
  tasks = json.load(f)

url = DISCORD_HOOK

# Only process 1 task at a time
if len(tasks) > 0:
  task = tasks[0]
  
  if not OK:
    content = {"username": "Tasks", "content": "Moulinette Cloud : Task #%d failed unexpectedly for pack '%s' on container '%s'" % (task["id"], task["packFile"], task["container"])}
  elif task["status"] and task["status"] == "done":
    content = {"username": "Tasks", "content": "Moulinette Cloud : Task #%d completed for pack '%s' on container '%s'" % (task["id"], task["packFile"], task["container"])}
  else:
    content = {"username": "Tasks", "content": "Moulinette Cloud : Task #%d failed for pack '%s' on container '%s'" % (task["id"], task["packFile"], task["container"])}
    
  requests.post(url, data = content)
  

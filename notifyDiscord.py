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
  details = task["details"] if "details" in task else ""
  
  if not OK:
    status = "CRIT"
  elif task["status"] and task["status"] == "done":
    status = "SUCC"
  else:
    status = "FAIL"
    
  packFile = task["packFile"].spit("#")[0] # don't make token visible
  content = {"username": "Tasks", "content": "[**%s**] #%d   **%s** (type)   **%s** (pack)   **%s** (container).\n*%s*" % (status, task["id"], task["type"], packFile, task["container"], details)}

  requests.post(url, data = content)
  

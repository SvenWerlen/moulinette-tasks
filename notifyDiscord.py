import os
import json
import requests

OUTPUT_FOLDER = os.getenv('OUTPUT_FOLDER')
DISCORD_HOOK = os.getenv('DISCORD_HOOK')

task = {}
with open(os.path.join(OUTPUT_FOLDER, "task.json")) as f:
  task = json.load(f)

url = DISCORD_HOOK
content = {"username": "Tasks", "content": "Task #%d completed for pack '%s' on container '%s'" % (task["id"], task["data"]["blob"], task["data"]["container"])}
requests.post(url, data = content)

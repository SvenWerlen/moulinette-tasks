import os
import sys
import time
import requests

MAX_TIME=90

if len(sys.argv) >= 2:
  lockFile = sys.argv[1]
  
  lockFileCreationTime = os.path.getctime(lockFile)
  nowTime = time.time()
  
  minutesSince = round((nowTime - lockFileCreationTime)/60)
  
  if minutesSince > MAX_TIME:    
    url = os.getenv('DISCORD_HOOK')
    content = {"username": "Lock", "content": "Moulinette Cloud : Lock is set for more than %d minutes. Please check!" % (minutesSince)}
    requests.post(url, data = content)

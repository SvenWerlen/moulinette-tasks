#!/bin/bash
set -e

source environment.sh

LOCK=/tmp/moulinette-tasks.lock

# check if process already running
if [ -f "$LOCK" ]; then
  python3 ./checkLock.py $LOCK
  exit 1
fi

# add lock
touch $LOCK

python3 ./retrieveTasks.py
python3 ./processTasks.py
python3 ./uploadBlobs.py
python3 ./completeTasks.py
python3 ./notifyDiscord.py

# remove lock
rm -f $LOCK

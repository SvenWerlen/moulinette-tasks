#!/bin/bash
set -e

source environment.sh

JSON=/tmp/moulinette-tasks.json
LOCK=/tmp/moulinette-tasks.lock

# check if process already running
if [ -f "$LOCK" ]; then
  python3 ./checkLock.py $LOCK
  exit 1
fi

# add lock
touch $LOCK

CONTINUE=true
while $CONTINUE
do
    python3 ./retrieveTasks.py
    python3 ./processTasks.py
    python3 ./uploadBlobs.py
    python3 ./completeTasks.py
    python3 ./notifyDiscord.py

    # check that there is no task any more.
    # If output size = 2 that means that list is []
    list=$(cat $JSON)
    if [ ${#list} -eq 2 ]; then
      CONTINUE=false
    fi
done

# remove lock
rm -f $LOCK

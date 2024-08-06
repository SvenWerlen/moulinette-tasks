#!/bin/bash
source environment.sh
source {{ venv_path }}/bin/activate

DEBUG=$1

JSON=/tmp/moulinette-tasks.json
LOCK=/tmp/moulinette-tasks.lock

CONTINUE=true
while $CONTINUE
do
    # check if process already running
    if [ -f "$LOCK" ]; then
      python3 ./checkLock.py $LOCK
      exit 1
    fi

    # add lock
    if [ ! "$DEBUG" = "true" ]; then
      touch $LOCK
    fi

    OK=true

    if [ "$OK" = true ]; then python3 ./retrieveTasks.py || OK=false; fi
    if [ "$OK" = true ]; then python3 ./processTasks.py $DEBUG || OK=false; fi
    if [ "$OK" = true ]; then python3 ./processMetadata.py $DEBUG || OK=false; fi

    if [ "$DEBUG" = "true" ]; then
      echo "Debug completed!"
      exit 1
    fi

    if [ "$OK" = true ]; then python3 ./updateMongoDB.py || OK=false; fi
    #exit 1
    if [ "$OK" = true ]; then python3 ./uploadBlobs.py || OK=false; fi
    
    python3 ./completeTasks.py $OK
    python3 ./notifyDiscord.py $OK

    # check that there is no task any more.
    # If output size = 2 that means that list is []
    list=$(cat $JSON)
    if [ ${#list} -eq 2 ]; then
      CONTINUE=false
    fi

    # remove lock
    rm -f $LOCK
done
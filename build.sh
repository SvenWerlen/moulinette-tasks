#!/bin/bash
set -e

if [ -n "$AZURE_STORAGE_CONTAINER" ]; then 

  if [ -n "$TASK_ID" ]; then 
    
    sudo mkdir /mnt/blobfusetmp
    sudo chown appveyor /mnt/blobfusetmp
    sudo mount -t tmpfs -o size=16g tmpfs /mnt/blobfusetmp
    sudo mkdir /mnt/blob
    sudo chown appveyor /mnt/blob
    blobfuse /mnt/blob --tmp-path=/mnt/blobfusetmp -o attr_timeout=240 -o entry_timeout=240 -o negative_timeout=120 --file-cache-timeout-in-seconds=120 --container-name=$AZURE_STORAGE_CONTAINER
    AZURE_STORAGE_MOUNT=/mnt/blob python3 AZURE_STORAGE_ACCESS_KEY="" AZURE_STORAGE_ACCOUNT="" ./processTask.py
    python3 ./completeTask.py
    sudo umount /mnt/blob
  
  else
    echo "TASK_ID is not defined or empty. Skipping..."
  fi

else
  echo "AZURE_STORAGE_CONTAINER is not defined or empty. Skipping..."
fi

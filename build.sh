#!/bin/bash
set -e

mkdir -p output
OUTPUT_FOLDER=output python3 ./downloadPack.py
OUTPUT_FOLDER=output python3 ./processTask.py
OUTPUT_FOLDER=output python3 ./uploadBlobs.py
OUTPUT_FOLDER=output python3 ./completeTask.py
OUTPUT_FOLDER=output python3 ./notifyDiscord.py

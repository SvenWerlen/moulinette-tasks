#!/bin/bash
set -e

source environment.sh
python3 ./retrieveTasks.py
python3 ./processTasks.py
python3 ./uploadBlobs.py
python3 ./completeTasks.py
python3 ./notifyDiscord.py

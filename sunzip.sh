#!/bin/bash

if [ $# -ne 2 ] || ! [ -f "$1" ]
then
    printf '%s\n' "Expected a filename as the first argument and target folder as second argument only. Aborting."
    exit 1
fi

##
## Unzip
##
echo "Unziping $1"
unzip -q -d "$2" "$1"
chmod -R 755 "$2"
echo "Done."

##
## Remove undesired __MACOSX files from zip
##
find $2 -name "__MACOSX*" -exec rm -rf {} \;

##
## Create subfolder if files at root
##
FILES=$(find $2 -maxdepth 1 -type f | wc -l)
DIRS=$(find $2 -maxdepth 1 -type d | wc -l)

##
## Create folder matching ZIP if multiple files or not 1 single folder
##
subfolder="$2/$(basename "$1" .zip)"
if [ ! "$FILES" -eq "0" ] || [ ! "$DIRS" -eq "2" ]; then
  echo "Moving all files to $subfolder..."
  mkdir "$subfolder"
  mv "$2"/* "$subfolder/"
##
## 1 single folder ? rename it to match the ZIP name
##
else
  echo "Renaming subfolder to match $subfolder..."
  mv $2/* "$subfolder"
fi

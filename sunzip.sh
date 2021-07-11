#!/bin/bash

if [ $# -ne 2 ] || ! [ -f "$1" ]
then
    printf '%s\n' "Expected a filename as the first argument and target folder as second argument only. Aborting."
    exit 1
fi

##
## Remove undesired __MACOSX files from zip
##
zip -d "$1" "__MACOSX*"

extract_dir="$2"

# Strip the leading and trailing information about the zip file (leaving
# only the lines with filenames), then check to make sure *all* filenames
# contain a /.
# If any file doesn't contain a / (i.e. is not located in a directory or is
# a directory itself), exit with a failure code to trigger creating a new
# directory for the extraction.
if ! unzip -l "$1" | tail -n +4 | head -n -2 | awk 'BEGIN {lastprefix = ""} {if (match($4, /[^/]+/)) {prefix=substr($4, RSTART, RLENGTH); if (lastprefix != "" && prefix != lastprefix) {exit 1}; lastprefix=prefix}}'
then
    extract_dir="$2/$(basename "$1" .zip)"
fi

echo "[Unzip] Extracting dir is $extract_dir"
unzip -q -d "$extract_dir" "$1"


#!/bin/bash
set -e

# set locale to avoid issues with number format
LC_ALL="en_US.UTF-8"

# extract video length
DURATION=$(ffprobe -loglevel error -of csv=p=0 -show_entries format=duration $1)

# get half length
HALF=$(printf "%0.2f" "$(bc -l <<< "$DURATION*0.5")")

# extract frame in the middle of the video
ffmpeg -ss "$HALF" -loglevel error -c:v libvpx-vp9 -i "$1" -frames:v 1 "$2.png"

# convert to webp format
mogrify -format webp -quality 60 "$2.png"
rm "$2.png"

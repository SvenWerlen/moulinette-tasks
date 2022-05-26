import os
import logging

DEFAULT_QUALITY = 60
DEFAULT_SIZE    = 400

##
## Python utilities for media (image/video) processing
##


##
## Converts image to WebP format
## Returns false if something went wrong (ex: missing image)
##
def convertImage( imagePath, destPath, quality = DEFAULT_QUALITY ):

  if not os.path.isfile(imagePath):
    logging.warning("Cannot convert to WebP. Image %s doesn't exist" % imagePath)
    return False

  os.system("convert -quality %s %s %s" % (quality, imagePath, destPath))

##
## Generates thumbnail
## Returns false if something went wrong (ex: missing image)
##
def generateThumnail( imagePath, thumbPath, size = DEFAULT_SIZE, keepRatio = False ):

  if not os.path.isfile(imagePath):
    logging.warning("Cannot generate thumbnail. Image %s doesn't exist" % imagePath)
    return False

  sizes = "%sx%s" % (size, size)

  # image is video
  if imagePath.endswith(".webm") or imagePath.endswith(".mp4"):
    os.system('./thumbnailFromVideo.sh "%s" "%s"' % (imagePath, "/tmp/thumbnail"))
    generateThumnail( "/tmp/thumbnail.webp", thumbPath, size, keepRatio )
  else:
    os.system('convert "%s" -background none -resize %s%s -gravity center -extent %s "%s"' % (imagePath, sizes, "^" if not keepRatio else "", sizes, thumbPath))

##
## Generates watermarked version
##
def generateWatermark( imagePath, wmPath, watermark, size = DEFAULT_SIZE ):

  if not os.path.isfile(imagePath):
    logging.warning("Cannot generate watermarked thumbnail. Image %s doesn't exist" % imagePath)
    return False

  os.system('convert -thumbnail %sx%s -background none -gravity center "%s" -extent %sx%s /tmp/img.webp' % (size, size, imagePath, size, size))
  os.system('composite %s /tmp/img.webp -gravity Center "%s"' % (watermark, wmPath))

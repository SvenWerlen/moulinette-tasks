import os
import logging

DEFAULT_QUALITY = 60

##
## Python utilities for media (image/video) processing
##


##
## Generates a thumbnail for the give image
## Returns false if something went wrong (ex: missing image)
##
def generateThumnail( imagePath, destPath, quality = DEFAULT_QUALITY ):

  if not os.path.isfile(imagePath):
    logging.warning("Cannot generate thumbnail. Image %s doesn't exist" % imagePath)
    return False

  os.system("convert -quality %s %s %s" % (quality, imagePath, destPath))


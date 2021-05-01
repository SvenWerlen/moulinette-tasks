import os
import sys

fromPath = sys.argv[1]
(file, ext) = os.path.splitext(fromPath)
(file, ext) = os.path.splitext(file)
toPath = file + ".webp"
os.rename(fromPath, toPath)

import os
from time import time
import boto3

##
## Deletes an entire pack (folder) from the given bucket
## Deletes the pack or dungeonpack
##
def deleteS3Pack(client, bucketName, packname):
  secs = time()
  
  response = client.list_objects(Bucket=bucketName,Prefix=packname + "/")
  if not 'Contents' in response:
    return 0

  count = 0
  for obj in response['Contents']:
    client.delete_object(Bucket=bucketName, Key=obj['Key'])
    count += 1

  print("[S3LIB] %d assets deleted in %.1f seconds" % (count, time() - secs))
  return count
          
##
## Uploads an entire folder
##
def uploadS3PackFolder(client, bucketName, path):
  print("[S3LIB] Uploading %s to %s" % (path, bucketName))
  secs = time()
  
  folderName = os.path.basename(path)
  
  total = 0
  for r, d, f in os.walk(path):
    total += len(f)
  
  count = 0
  for root, dirs, files in os.walk(path):
    for file in files:
      fullpath = os.path.join(root, file)
      path = fullpath[fullpath.find(folderName):]
      
      try:
        client.upload_file(
          fullpath, 
          bucketName, 
          path,
          ExtraArgs={'ACL': 'private'})
      except Exception as e:
        print("[S3LIB] Couldn't upload %s" % path)
      
      count += 1
      if count % 100 == 0:
        print("[S3LIB] - %d/%d files uploaded" % (count, total))
  
  print("[S3LIB] %d assets uploaded in %.1f seconds" % (count, (time() - secs)))

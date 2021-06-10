import os
from time import time
from azure.storage.blob import BlobServiceClient

##
## Downloads a single blob file
##
def downloadBlob(client, containerName, blobName, outputPath):
  secs = time()
  cClient = client.get_container_client(containerName)
  
  # Full path to output file
  download_file_path = os.path.join(outputPath, blobName)

  # For nested blobs, create local path as well
  os.makedirs(os.path.dirname(download_file_path), exist_ok=True)

  # Download blob
  bClient = cClient.get_blob_client(blobName)
  if bClient.exists():
    download_stream = bClient.download_blob(max_concurrency=10)

    with open(download_file_path, 'wb') as file:
        download_stream.readinto(file)
    
    print("[AZURELIB] %s downloaded in %.1f seconds" % (blobName, time() - secs))

  else:
    print("[AZURELIB] Blob %s doesn't exist!" % blobName)


##
## Deletes an entire pack (folder) from the given container
## Deletes the pack or dungeonpack
##
def deletePack(client, containerName, packname):
  secs = time()
  cClient = client.get_container_client(containerName)
  blobs = [blob.name for blob in cClient.list_blobs(name_starts_with=packname + "/")]
  blobs.sort(reverse=True, key=len)
  count = 0
  if len(blobs) > 0:
    for blob in blobs:
      cClient.delete_blob(blob)
      count += 1
  
  #count += 1 if deleteBlob(cClient, packname + ".zip") else 0
  #count += 1 if deleteBlob(cClient, packname + ".dungeondraft_pack") else 0
  print("[AZURELIB] %d assets deleted in %.1f seconds" % (count, time() - secs))
  return count
      
##
## Deletes a single blob file if exists
## Return true if existed
##
def deleteBlob(cClient, blobName):
  bClient = cClient.get_blob_client(blobName)
  if bClient.exists():
    bClient.delete_blob()
    return True
  return False
    
##
## Uploads an entire folder
##
def uploadPackFolder(client, containerName, path):
  print("[AZURELIB] Uploading %s to %s" % (path, containerName))
  secs = time()
  cClient = client.get_container_client(containerName)
  
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
        with open(fullpath, "rb") as data:
          cClient.upload_blob(path, data)
      except Exception as e:
        print("[AZURELIB] Couldn't upload %s" % path)
      
      count += 1
      if count % 100 == 0:
        print("[AZURELIB] - %d/%d files uploaded" % (count, total))
  
  print("[AZURELIB] Upload in %.1f seconds" % (time() - secs))

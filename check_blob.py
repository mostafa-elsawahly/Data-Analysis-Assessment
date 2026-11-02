# check_blob.py
import os, re, collections
from azure.storage.blob import BlobServiceClient

c = BlobServiceClient.from_connection_string(
    os.environ["AZURE_STORAGE_CONNECTION_STRING"]).get_container_client("incoming")

cnt = collections.Counter()
for b in c.list_blobs():
    m = re.match(r"(\d{4})/(Accessions|Separations|Employment)/.+\.parquet$", b.name)
    if m:
        cnt[(m.group(2), m.group(1))] += 1

for (ds, year), n in sorted(cnt.items()):
    print(ds, year, n)

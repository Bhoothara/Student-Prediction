# test_mongo_connect.py
from pymongo import MongoClient
import os
from urllib.parse import quote_plus

# Option 1: read from env var
uri = os.environ.get("MONGO_URI", None)
if not uri:
    # Option 2: build here (replace values) - prefer env var
    user = "bhootharajume1_db_user"
    pwd = "Manyamanya"   # only for local testing; don't commit
    pwd_enc = quote_plus(pwd)
    host = "cluster0.djel7c3.mongodb.net"
    uri = f"mongodb+srv://{user}:{pwd_enc}@{host}/?retryWrites=true&w=majority"

print("Testing URI (hidden password) -> host:", uri.split("@")[-1].split("/")[0])
try:
    client = MongoClient(uri, serverSelectionTimeoutMS=8000)
    client.admin.command("ping")
    print("SUCCESS: connected to Atlas. Databases visible:", client.list_database_names())
    db = client.get_database()  # default DB from URI; might need name
    # check collections if you want
    print("Collections (example):", db.list_collection_names())
except Exception as e:
    print("ERROR:", e)

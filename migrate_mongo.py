import sqlite3
from pymongo import MongoClient
import os

# --- Config ---
SQLITE_DB = "accounts.db"   # tên file SQLite cũ
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB  = os.getenv("MONGO_DB", "printful_bot")

# --- Kết nối ---
conn = sqlite3.connect(SQLITE_DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
col = db.accounts

# --- Đọc SQLite ---
cur.execute("SELECT * FROM accounts")
rows = cur.fetchall()

docs = []
for row in rows:
    docs.append({
        "email": row["email"],
        "password": row["password"],
        "fullname": row["fullname"],
        "status": row["status"],
        "profile_id": row["profile_id"] if "profile_id" in row.keys() else None,
    })

if docs:
    # --- Insert vào Mongo ---
    result = col.insert_many(docs, ordered=False)
    print(f"Đã migrate {len(result.inserted_ids)} account sang MongoDB")
else:
    print("Không có account nào trong SQLite.")

conn.close()

import logging
from pymongo import MongoClient
from bson.objectid import ObjectId

# ------------------------
# Kết nối MongoDB
# ------------------------
client = MongoClient("mongodb://localhost:27017/")
db = client["printful_bot"]

# ------------------------
# Collection
# ------------------------
accounts_col = db["accounts"]
billing_col = db["billing_accounts"]
bin_col = db["binpool"]

# ------------------------
# Register Accounts
# ------------------------
def get_accounts():
    return list(accounts_col.find())

def insert_account(email, password, fullname):
    accounts_col.insert_one({
        "email": email,
        "password": password,
        "fullname": fullname,
        "status": "idle",
        "profile_id": None
    })

def delete_account(acc_id: str):
    accounts_col.delete_one({"_id": ObjectId(acc_id)})

def update_status(acc_id: str, status: str):
    accounts_col.update_one({"_id": ObjectId(acc_id)}, {"$set": {"status": status}})

# ------------------------
# Billing Accounts
# ------------------------
def get_billing_accounts():
    return list(billing_col.find())

def insert_billing_account(profile_id, email, password, fullname, address, city, state, zipcode):
    billing_col.insert_one({
        "profile_id": profile_id,
        "email": email,
        "password": password,
        "fullname": fullname,
        "address": address,
        "city": city,
        "state": state,
        "zipcode": zipcode,
        "status": "idle"
    })

def delete_billing_account(acc_id: str):
    billing_col.delete_one({"_id": ObjectId(acc_id)})

def update_billing_status(acc_id: str, status: str):
    billing_col.update_one({"_id": ObjectId(acc_id)}, {"$set": {"status": status}})

# ------------------------
# BIN Pool
# ------------------------
def get_binpool():
    return list(bin_col.find())

def insert_bin(number, month, year, desc):
    bin_col.insert_one({
        "number": number,
        "month": month,
        "year": year,
        "desc": desc,
        "status": "idle"
    })

def update_bin_status(bin_id: str, status: str):
    bin_col.update_one({"_id": ObjectId(bin_id)}, {"$set": {"status": status}})

import sqlite3

DB_FILE = "accounts.db"

def reset_status():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("UPDATE accounts SET status='registered'")
    conn.commit()
    conn.close()
    print("All accounts reset to 'registered'")

if __name__ == "__main__":
    reset_status()

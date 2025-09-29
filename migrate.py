import sqlite3

DB_FILE = "accounts.db"

def migrate():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # thêm các cột nếu chưa có
    try: cur.execute("ALTER TABLE accounts ADD COLUMN address TEXT")
    except: pass
    try: cur.execute("ALTER TABLE accounts ADD COLUMN city TEXT")
    except: pass
    try: cur.execute("ALTER TABLE accounts ADD COLUMN state TEXT")
    except: pass
    try: cur.execute("ALTER TABLE accounts ADD COLUMN zipcode TEXT")
    except: pass

    conn.commit()
    conn.close()
    print("Migration done!")

if __name__ == "__main__":
    migrate()

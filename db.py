import sqlite3
import logging

DB_FILE = "accounts.db"


def get_conn():
    """Kết nối tới DB SQLite"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Tạo bảng nếu chưa có"""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password TEXT,
        fullname TEXT,
        status TEXT DEFAULT 'pending',
        profile_id TEXT
    )
    """)

    conn.commit()
    conn.close()


def mark_account_registered(acc_id: int):
    """
    Cập nhật trạng thái account thành 'registered'
    """
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE accounts SET status=? WHERE id=?", ("registered", acc_id))
        conn.commit()
        conn.close()
        logging.info(f"[db] Account {acc_id} đã được đánh dấu là registered")
    except Exception as e:
        logging.error(f"[db] Lỗi khi cập nhật account {acc_id}: {e}")


def get_accounts(mode: str = None):
    """
    Lấy danh sách account theo mode:
      - None: tất cả
      - 'register': account chưa đăng ký
      - 'manage': account đã đăng ký
    """
    conn = get_conn()
    cur = conn.cursor()

    if mode == "register":
        cur.execute("SELECT * FROM accounts WHERE status != 'registered' ORDER BY id DESC")
    elif mode == "manage":
        cur.execute("SELECT * FROM accounts WHERE status = 'registered' ORDER BY id DESC")
    else:
        cur.execute("SELECT * FROM accounts ORDER BY id DESC")

    rows = cur.fetchall()
    conn.close()
    return rows

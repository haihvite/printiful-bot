import time
import logging
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from automation.worker import worker_register
from db import get_conn, init_db, get_accounts

# ---------- cấu hình executor ----------
MAX_WORKERS = 5
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

# ---------- init DB ----------
init_db()

# ---------- logging ----------
logging.basicConfig(
    level=logging.INFO,  # mức log: DEBUG / INFO / WARNING / ERROR
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),  # log ra file
        logging.StreamHandler()  # log ra console
    ]
)
# ---------- FastAPI ----------
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ---------- Trang chính ----------
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    rows = get_accounts()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "accounts": rows,
        "active": "home",
        "title": "Tất cả tài khoản"
    })


# ---------- Import account từ textarea ----------
@app.post("/import")
def import_accounts(data: str = Form(...)):
    conn = get_conn()
    cur = conn.cursor()
    lines = [ln.strip() for ln in data.splitlines() if ln.strip()]
    for ln in lines:
        parts = ln.split("|")
        if len(parts) < 3:
            continue
        email, password, fullname = parts
        cur.execute(
            "INSERT INTO accounts (email, password, fullname, status) VALUES (?, ?, ?, 'idle')",
            (email.strip(), password.strip(), fullname.strip())
        )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/register", status_code=303)


# ---------- API lấy danh sách ----------
@app.get("/api/accounts")
def api_accounts(mode: str = None):
    rows = get_accounts(mode)
    return JSONResponse([dict(r) for r in rows])


# ---------- Chạy action ----------
@app.post("/run/{acc_id}/{action}")
def run_action(acc_id: int, action: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM accounts WHERE id=?", (acc_id,))
    acc = cur.fetchone()
    if not acc:
        conn.close()
        return JSONResponse({"ok": False, "error": "Account not found"}, status_code=404)

    cur.execute("UPDATE accounts SET status=? WHERE id=?", (f"Running: {action}", acc_id))
    conn.commit()
    conn.close()

    if action == "register":
        executor.submit(worker_register, acc_id)
    else:
        logging.warning(f"Hành động {action} chưa được implement.")
    return JSONResponse({"ok": True})


# ---------- Xoá account ----------
@app.post("/delete/{acc_id}")
def delete_account(acc_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM accounts WHERE id=?", (acc_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)


# ---------- Trang Đăng ký ----------
@app.get("/register", response_class=HTMLResponse)
def page_register(request: Request):
    rows = get_accounts(mode="register")
    return templates.TemplateResponse("register.html", {
        "request": request,
        "accounts": rows,
        "active": "register",
        "title": "Đăng ký"
    })


# ---------- Trang Quản lý ----------
@app.get("/manage", response_class=HTMLResponse)
def page_manage(request: Request):
    rows = get_accounts(mode="manage")
    return templates.TemplateResponse("manage.html", {
        "request": request,
        "accounts": rows,
        "active": "manage",
        "title": "Quản lý tài khoản"
    })

import time
import logging
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from automation.proxy_utils import get_proxies

from automation.worker import worker_register, worker_login, worker_deposit, worker_billing
from db import get_conn, init_db, get_accounts
from fastapi.responses import StreamingResponse
import io, csv

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


# ---------- API Run All ----------
@app.post("/api/register_all")
def register_all():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM accounts WHERE status='idle'")
    accounts = cur.fetchall()
    conn.close()

    count = len(accounts)
    if count == 0:
        return {"status": "ok", "message": "Không có account idle để chạy."}

    proxies = get_proxies(count) or []
    if len(proxies) < count:
        logging.error(f"Yêu cầu {count} proxy nhưng chỉ lấy được {len(proxies)} → hủy chạy.")
        return {
            "status": "error",
            "message": f"Không đủ proxy ({len(proxies)}/{count}) → không chạy account nào."
        }

    # đủ proxy mới chạy
    started = 0
    for i, acc in enumerate(accounts):
        acc_id = acc["id"]
        proxy = proxies[i]

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE accounts SET status=? WHERE id=?", ("Running: register", acc_id))
        conn.commit()
        conn.close()

        executor.submit(worker_register, acc_id, proxy)
        started += 1

    return {
        "status": "ok",
        "message": f"Đã khởi chạy {started} account (idle)."
    }

@app.get("/export_registered")
def export_registered():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT profile_id, email, password, fullname FROM accounts WHERE status='registered'")
    rows = cur.fetchall()
    conn.close()

    # tạo file CSV trong memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["profile_id", "email", "password", "fullname"])
    for r in rows:
        writer.writerow([r["profile_id"], r["email"], r["password"], r["fullname"]])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=registered_accounts.csv"}
    )

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
        proxies = get_proxies(1)
        if proxies:
            proxy = proxies[0]
            executor.submit(worker_register, acc_id, proxy)
    elif action == "login":
        proxies = get_proxies(1)
        if proxies:
            proxy = proxies[0]
            executor.submit(worker_login, acc_id, proxy)
    else:
        logging.warning(f"Hành động {action} chưa được implement.")

    return JSONResponse({"ok": True})

@app.get("/deposit")
def deposit(request: Request):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM accounts WHERE profile_id IS NOT NULL")
    accounts = cur.fetchall()
    conn.close()
    return templates.TemplateResponse("deposit.html", {"request": request, "accounts": accounts, "active": "deposit"})

@app.post("/import_deposit")
async def import_deposit(request: Request):
    form = await request.form()
    lines = form.get("accounts", "").splitlines()
    conn = get_conn()
    cur = conn.cursor()
    for line in lines:
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 5:
            profile_id, email, password, fullname, amount = parts
            cur.execute("SELECT id FROM accounts WHERE profile_id=?", (profile_id,))
            row = cur.fetchone()
            if row:
                cur.execute("UPDATE accounts SET amount=?, email=?, password=?, fullname=? WHERE profile_id=?",
                            (amount, email, password, fullname, profile_id))
            else:
                cur.execute("INSERT INTO accounts (profile_id,email,password,fullname,amount,status) VALUES (?,?,?,?,?,'idle')",
                            (profile_id,email,password,fullname,amount))
    conn.commit()
    conn.close()
    return RedirectResponse("/deposit", status_code=303)

@app.post("/api/deposit_all")
def deposit_all():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM accounts WHERE status='idle' AND profile_id IS NOT NULL AND amount IS NOT NULL")
    accounts = cur.fetchall()
    conn.close()

    if not accounts:
        return {"status":"error","message":"Không có account để deposit"}

    proxies = get_proxies(len(accounts))
    if len(proxies) < len(accounts):
        return {"status":"error","message":"Không đủ proxy"}

    for i, acc in enumerate(accounts):
        proxy = proxies[i]
        executor.submit(worker_deposit, acc["id"], proxy)

    return {"status":"ok","message":"Đã bắt đầu deposit"}

@app.get("/billing")
def billing(request: Request):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM accounts WHERE profile_id IS NOT NULL")
    accounts = cur.fetchall()
    conn.close()
    return templates.TemplateResponse("billing.html", {"request": request, "accounts": accounts, "active": "billing"})


@app.post("/import_billing")
async def import_billing(request: Request):
    form = await request.form()
    lines = form.get("accounts", "").splitlines()
    conn = get_conn()
    cur = conn.cursor()
    for line in lines:
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 8:
            profile_id, email, password, fullname, address, city, state, zipcode = parts
            cur.execute("SELECT id FROM accounts WHERE profile_id=?", (profile_id,))
            row = cur.fetchone()
            if row:
                cur.execute("""UPDATE accounts 
                               SET email=?, password=?, fullname=?, address=?, city=?, state=?, zipcode=? 
                               WHERE profile_id=?""",
                            (email,password,fullname,address,city,state,zipcode,profile_id))
            else:
                cur.execute("""INSERT INTO accounts 
                               (profile_id,email,password,fullname,address,city,state,zipcode,status) 
                               VALUES (?,?,?,?,?,?,?,?,'idle')""",
                            (profile_id,email,password,fullname,address,city,state,zipcode))
    conn.commit()
    conn.close()
    return RedirectResponse("/billing", status_code=303)

@app.post("/api/billing_all")
def billing_all():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""SELECT * FROM accounts 
                   WHERE status='idle' AND profile_id IS NOT NULL 
                   AND address IS NOT NULL AND city IS NOT NULL AND state IS NOT NULL AND zipcode IS NOT NULL""")
    accounts = cur.fetchall()
    conn.close()

    if not accounts:
        return {"status":"error","message":"Không có account để billing"}

    proxies = get_proxies(len(accounts))
    if len(proxies) < len(accounts):
        return {"status":"error","message":"Không đủ proxy"}

    for i, acc in enumerate(accounts):
        proxy = proxies[i]
        executor.submit(worker_billing, acc["id"], proxy)

    return {"status":"ok","message":"Đã bắt đầu add billing"}

import logging
import time
from automation.gpm_profile import GpmProfile
from automation.proxy_utils import get_proxies
from automation.browser_utils import get_random_browser_version, make_user_agent
from automation.site_actions import (
    create_account,
    submit_signup,
    handle_popups,
    check_registration_success,
    login_account,
    do_deposit,
    add_billing_info
)
from db import get_conn

import csv

def save_registered_account(acc):
    """Lưu account đã đăng ký thành công ra file CSV"""
    with open("registered_accounts.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            acc["profile_id"],
            acc["email"],
            acc["password"],
            acc["fullname"]
        ])

def update_status(acc_id: int, status: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE accounts SET status=? WHERE id=?", (status, acc_id))
    conn.commit()
    conn.close()
    logging.info(f"[Account {acc_id}] {status}")


def safe_goto(page, url, timeout=60000, retries=1):
    for attempt in range(retries + 1):
        try:
            page.goto(url, timeout=timeout, wait_until="load")
            return True
        except Exception as e:
            logging.warning(f"[safe_goto] Goto thất bại (lần {attempt+1}): {e}")
            if attempt < retries:
                logging.info("[safe_goto] Thử lại goto sau 2s...")
                time.sleep(2)
            else:
                return False


def worker_register(acc_id: int, proxy: dict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM accounts WHERE id=?", (acc_id,))
    acc = cur.fetchone()
    conn.close()
    if not acc:
        return

    email, password, fullname = acc["email"], acc["password"], acc["fullname"]

    gpm = None
    port = proxy["local_port"]
    proxy_str = f"{proxy['type']}://{proxy['host']}:{proxy['port']}"

    try:
        update_status(acc_id, f"Register: bắt đầu với proxy {proxy_str} (local {port})")

        gpm = GpmProfile()
        browser_version = get_random_browser_version()
        ua = make_user_agent(browser_version)

        payload = {
            "profile_name": f"acc_{email}",
            "group_name": "All",
            "browser_core": "chromium",
            "browser_name": "Chrome",
            "browser_version": browser_version,
            "is_random_browser_version": False,
            "raw_proxy": proxy_str,
            "startup_urls": "https://printful.com",
            "is_masked_font": True,
            "is_noise_canvas": False,
            "is_noise_webgl": False,
            "is_noise_client_rect": False,
            "is_noise_audio_context": True,
            "is_random_screen": False,
            "is_masked_webgl_data": True,
            "is_masked_media_device": True,
            "is_random_os": False,
            "os": "Windows 10",
            "webrtc_mode": 2,
            "user_agent": ua,
        }

        profile_id = gpm.create_profile(payload)
        update_status(acc_id, f"Profile đã tạo: {profile_id}")

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE accounts SET profile_id=? WHERE id=?", (profile_id, acc_id))
        conn.commit()
        conn.close()

        gpm.start(width=925, height=925)
        page = gpm.connect()
        update_status(acc_id, "Profile đã mở")

        ok = safe_goto(page, "https://www.printful.com", retries=1)
        if not ok:
            update_status(acc_id, "Goto Printful thất bại")
            return

        handle_popups(page, timeout=8)
        update_status(acc_id, "Đã load Printful + xử lý popup")

        create_account(page, fullname, email, password)
        update_status(acc_id, "Form đã điền")

        submit_signup(page)
        update_status(acc_id, "Đã ấn Submit – Đang chờ survey/dashboard...")

        success = check_registration_success(
            page, None, timeout=180, status_cb=update_status, acc_id=acc_id
        )
        if success:
            #update_status(acc_id, "Đăng ký thành công ✅")
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("UPDATE accounts SET status=? WHERE id=?", ("registered", acc_id))
            conn.commit()
            cur.execute("SELECT * FROM accounts WHERE id=?", (acc_id,))
            acc = cur.fetchone()
            conn.close()
            save_registered_account(acc)   # 🔹 lưu ra CSV
        else:
            update_status(acc_id, "Đăng ký thất bại ❌")

    except Exception as e:
        update_status(acc_id, f"error: {e}")
        logging.exception(f"[worker_register] Lỗi khi xử lý {email}: {e}")
    finally:
        if gpm:
            try:
                gpm.stop()
                logging.info(f"[Account {acc_id}] Profile đã đóng")
            except Exception:
                pass


def worker_login(acc_id: int, proxy: dict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM accounts WHERE id=?", (acc_id,))
    acc = cur.fetchone()
    conn.close()
    if not acc:
        return

    email, password, fullname, profile_id = acc["email"], acc["password"], acc["fullname"], acc["profile_id"]

    gpm = None
    try:
        update_status(acc_id, "Login: bắt đầu")

        if not profile_id:
            update_status(acc_id, "Không có profile_id, cần đăng ký trước")
            return

        # mở lại profile cũ
        gpm = GpmProfile()
        gpm.profile_id = profile_id
        gpm.start()   # start theo profile_id có sẵn
        page = gpm.connect()

        # thử vào dashboard
        page.goto("https://www.printful.com/dashboard/default", timeout=60000)
        page.wait_for_load_state("domcontentloaded", timeout=10000)
        handle_popups(page)

        if "auth/login" in page.url:
            update_status(acc_id, "Session hết hạn → cần login lại")
            success = login_account(page, email, password, update_status, acc_id)
            if success:
                update_status(acc_id, "Login thành công ✅")
            else:
                update_status(acc_id, "Login thất bại ❌")
        else:
            update_status(acc_id, "Login thành công (session) ✅")

    except Exception as e:
        update_status(acc_id, f"Lỗi login: {e}")
        logging.exception(f"[worker_login] {e}")
    finally:
        if gpm:
            try:
                gpm.stop()
                logging.info(f"[Account {acc_id}] Profile đã đóng")
            except Exception:
                pass

def worker_deposit(acc_id: int, proxy: dict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM accounts WHERE id=?", (acc_id,))
    acc = cur.fetchone()
    conn.close()
    if not acc:
        return

    gpm = None
    try:
        update_status(acc_id, "Deposit: bắt đầu")

        profile_id = acc["profile_id"]
        if not profile_id:
            update_status(acc_id, "Chưa có profile_id → bỏ qua")
            return

        gpm = GpmProfile()
        gpm.profile_id = profile_id
        gpm.start()
        page = gpm.connect()

        handle_popups(page)

        success = do_deposit(page, acc["amount"], update_status, acc_id)

        if success:
            update_status(acc_id, "Deposit thành công ✅")
        else:
            update_status(acc_id, "Deposit thất bại ❌")

    except Exception as e:
        update_status(acc_id, f"Lỗi deposit: {e}")
    finally:
        if gpm:
            try: gpm.stop()
            except: pass

def worker_billing(acc_id: int, proxy: dict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM accounts WHERE id=?", (acc_id,))
    acc = cur.fetchone()
    conn.close()
    if not acc:
        return

    gpm = None
    try:
        update_status(acc_id, "Billing: bắt đầu")

        profile_id = acc["profile_id"]
        if not profile_id:
            update_status(acc_id, "Chưa có profile_id → bỏ qua")
            return

        gpm = GpmProfile()
        gpm.profile_id = profile_id
        gpm.start()
        page = gpm.connect()

        handle_popups(page)

        success = add_billing_info(
            page,
            acc["fullname"],
            acc["address"],
            acc["city"],
            acc["state"],
            acc["zipcode"],
            update_status,
            acc_id
        )

        if success:
            update_status(acc_id, "Billing thành công ✅")
        else:
            update_status(acc_id, "Billing thất bại ❌")

    except Exception as e:
        update_status(acc_id, f"Lỗi billing: {e}")
    finally:
        if gpm:
            try: gpm.stop()
            except: pass

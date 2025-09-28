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
)
from db import get_conn


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


def worker_register(acc_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM accounts WHERE id=?", (acc_id,))
    acc = cur.fetchone()
    conn.close()
    if not acc:
        return

    email, password, fullname = acc["email"], acc["password"], acc["fullname"]

    gpm = None
    try:
        update_status(acc_id, "Register: bắt đầu")

        proxies = get_proxies(1)
        proxy = proxies[0]
        proxy_str = f"{proxy['type']}://{proxy['host']}:{proxy['port']}"
        update_status(acc_id, f"Proxy: {proxy_str}")

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

        success = check_registration_success(page, None, timeout=180,
                                             status_cb=update_status, acc_id=acc_id)
        if success:
            update_status(acc_id, "Đăng ký thành công ✅")
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("UPDATE accounts SET status=? WHERE id=?", ("registered", acc_id))
            conn.commit()
            conn.close()
        else:
            update_status(acc_id, "Đăng ký thất bại ❌")

    except Exception as e:
        update_status(acc_id, f"error: {e}")
        logging.exception(f"[worker_register] Lỗi khi xử lý {email}: {e}")
    finally:
        try:
            if gpm:
                gpm.stop()
                logging.info(f"[Account {acc_id}] Profile đã đóng")
                #update_status(acc_id, "Profile đã đóng")
        except Exception:
            pass

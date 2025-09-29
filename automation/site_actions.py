import logging
import random
import time

# ---------- Utility ----------
def human_delay(min_sec=0.5, max_sec=1.5):
    t = random.uniform(min_sec, max_sec)
    logging.debug(f"[human_delay] Ngủ {t:.2f}s")
    time.sleep(t)


# ---------- SAFE ACTIONS ----------
def safe_click(page, selector, timeout=5000):
    logging.info(f"[safe_click] Thử click: {selector}")
    try:
        page.wait_for_selector(selector, state="visible", timeout=timeout)
        human_delay()
        page.click(selector)
        logging.info(f"[safe_click] Click thành công: {selector}")
    except Exception as e:
        logging.warning(f"[safe_click] Lỗi click {selector}: {e}. Thử xử lý popup...")
        handle_popups(page, timeout=5)
        page.wait_for_selector(selector, state="visible", timeout=timeout)
        human_delay()
        page.click(selector)
        logging.info(f"[safe_click] Click thành công sau khi đóng popup: {selector}")


def safe_click_any(page, selectors, timeout=5000):
    for sel in selectors:
        try:
            logging.info(f"[safe_click_any] Thử selector: {sel}")
            page.wait_for_selector(sel, state="visible", timeout=2000)
            human_delay()
            page.click(sel)
            logging.info(f"[safe_click_any] Click thành công: {sel}")
            return
        except Exception as e:
            logging.debug(f"[safe_click_any] Selector {sel} không hợp: {e}")
    raise Exception(f"[safe_click_any] Không tìm thấy selector nào trong list: {selectors}")


def safe_type(page, selector, text, timeout=5000, per_char_delay=(50, 120)):
    """
    Gõ text vào input theo kiểu con người: từng ký tự, delay ngẫu nhiên
    per_char_delay: tuple (min_ms, max_ms)
    """
    logging.info(f"[safe_type] Gõ vào {selector}: {text}")
    try:
        page.wait_for_selector(selector, state="visible", timeout=timeout)
        human_delay()  # pause trước khi gõ
        page.click(selector)  # focus vào input

        for ch in text:
            page.keyboard.type(ch, delay=random.randint(*per_char_delay))
        logging.info(f"[safe_type] Nhập thành công: {selector}")
    except Exception as e:
        logging.error(f"[safe_type] Lỗi nhập {selector}: {e}")
        raise


def safe_check(page, selector, timeout=5000):
    logging.info(f"[safe_check] Tick checkbox: {selector}")
    try:
        el = page.wait_for_selector(selector, state="visible", timeout=timeout)
        human_delay()
        el.check()
        logging.info(f"[safe_check] Đã tick: {selector}")
    except Exception as e:
        logging.error(f"[safe_check] Lỗi tick {selector}: {e}")
        raise


# ---------- POPUP HANDLER ----------
def handle_popups(page, timeout=8, interval=1):
    logging.debug("Kiểm tra popup...")
    start = time.time()
    while time.time() - start < timeout:
        handled = False
        try:
            cookie_btn = page.query_selector("button[data-cookiefirst-action='accept']")
            if cookie_btn and cookie_btn.is_visible():
                cookie_btn.click()
                logging.info("Đã đóng popup Cookie")
                handled = True
        except Exception:
            pass
        try:
            promo = page.query_selector("div.promo-popup__content")
            if promo and promo.is_visible():
                btn = promo.query_selector("a.pf-btn")
                if btn and btn.is_visible():
                    btn.click()
                    logging.info("Đã đóng promo popup (old style)")
                else:
                    page.keyboard.press("Escape")
                    logging.info("Đã gửi ESC để đóng promo popup")
                handled = True
        except Exception:
            pass
        try:
            modal = page.query_selector("div.pf-modal__content")
            if modal and modal.is_visible():
                close_btn = modal.query_selector("button[aria-label='Close']")
                if close_btn and close_btn.is_visible():
                    close_btn.click()
                    logging.info("Đã đóng promo popup (new 30% modal)")
                else:
                    page.keyboard.press("Escape")
                    logging.info("Đã gửi ESC để đóng promo modal (new 30%)")
                handled = True
        except Exception:
            pass
        if handled:
            return True
        time.sleep(interval)
    return False


# ---------- REGISTER HELPERS ----------
def is_on_register_page(page):
    try:
        if "/auth/register" in (page.url or ""):
            return True
        if page.query_selector("a.register__email") or (
            page.query_selector("input[name='email']") and page.query_selector("input[name='password']")
        ):
            return True
    except Exception:
        pass
    return False


def ensure_on_register(page, retries=3):
    if is_on_register_page(page):
        logging.info("[ensure_on_register] Đã ở trang đăng ký, bỏ qua click header.")
        return

    # xử lý popup ngay khi vào
    handle_popups(page, timeout=10)

    selectors = [
        "a.pf-btn.pf-btn-primary[href*='/auth/register']",
        "xpath=//a[contains(@href, '/auth/register')]",
        "xpath=//a[contains(@href, '/auth/sign-up')]",
        "text=Sign up",
        "role=link[name='Sign up']",
        "role=button[name='Sign up']",
        "xpath=//button[@aria-label='Sign up']",
        "button.site-header__button.pf-d-md-none.pf-mx-12",
    ]

    for attempt in range(1, retries + 1):
        for sel in selectors:
            try:
                safe_click(page, sel, timeout=5000)
                logging.info(f"[ensure_on_register] Đã click: {sel}")
                page.wait_for_load_state("domcontentloaded", timeout=10000)
                if is_on_register_page(page):
                    logging.info("[ensure_on_register] Đã vào trang đăng ký.")
                    return
                time.sleep(2)
                if is_on_register_page(page):
                    logging.info("[ensure_on_register] Đã vào trang đăng ký (check lại).")
                    return
            except Exception as e:
                logging.debug(f"[ensure_on_register] Selector {sel} fail: {e}")
        logging.warning(f"[ensure_on_register] Thử vòng {attempt}/{retries} chưa vào được register.")

    logging.info("[ensure_on_register] Fallback: goto /auth/register")
    page.goto("https://www.printful.com/auth/register", timeout=30000)
    page.wait_for_load_state("domcontentloaded", timeout=10000)
    if not is_on_register_page(page):
        raise Exception("Không thể mở trang đăng ký (/auth/register)")


# ---------- FORM FLOW ----------
def create_account(page, fullname, email, password):
    logging.info(f"[create_account] Bắt đầu flow tạo tài khoản cho {email}")
    ensure_on_register(page)
    try:
        safe_click(page, "a.register__email")
    except Exception:
        logging.debug("[create_account] Không thấy 'Sign up with email' → form có thể đã hiện sẵn.")
    safe_type(page, "input[name='fullName']", fullname)
    safe_type(page, "input[name='email']", email)
    safe_type(page, "input[name='password']", password)
    safe_check(page, "input[name='hasAcceptedTerms']")
    logging.info("[create_account] Form đã được điền xong (chưa submit).")


def submit_signup(page, timeout=10000):
    selector = "input[type='submit'][value='Sign up']"
    logging.info("[submit_signup] Bắt đầu tìm và click nút Sign up")
    try:
        page.wait_for_selector(selector, state="visible", timeout=timeout)
        human_delay(3, 5)
        page.click(selector)
        logging.info("[submit_signup] Đã ấn Submit – Đang chờ survey/dashboard...")
        try:
            page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass
    except Exception as e:
        logging.warning(f"[submit_signup] Thất bại: {e}. Thử xử lý popup...")
        handle_popups(page, timeout=5)
        page.wait_for_selector(selector, state="visible", timeout=timeout)
        human_delay(3, 5)
        page.click(selector)
        logging.info("[submit_signup] Đã ấn Submit (sau popup) – Đang chờ survey/dashboard...")
        try:
            page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass


# ---------- SURVEY + CHECK REGISTER ----------
def complete_survey(page, status_cb=None, acc_id=None, max_steps=10):
    import time, logging, random

    try:
        for step in range(max_steps):
            container = page.query_selector("div.lead-scoring-survey")
            if not container:
                logging.info(f"[survey][{acc_id}] Không còn survey → kết thúc")
                if status_cb and acc_id:
                    status_cb(acc_id, "Survey hoàn tất")
                return True

            # --- Xử lý input text ---
            text_input = container.query_selector("input.pf-form-control")
            if text_input and text_input.is_visible():
                answer = random.choice(["Google", "Facebook", "Friend", "Internet", "Ads"])
                logging.info(f"[survey][{acc_id}] Điền survey input: {answer}")
                if status_cb and acc_id:
                    status_cb(acc_id, f"Survey input: {answer}")

                text_input.click()
                time.sleep(random.uniform(0.5, 1.2))  # delay trước khi gõ
                page.type("input.pf-form-control", answer, delay=random.randint(80,150))
                time.sleep(random.uniform(0.8, 1.5))  # delay sau khi gõ

                btn_finish = container.query_selector("button.pf-btn-primary")
                if btn_finish and btn_finish.is_visible():
                    logging.info(f"[survey][{acc_id}] Nhấn Finish survey (input)")
                    btn_finish.click()
                    time.sleep(random.uniform(1.5, 2.5))
                    continue

            # --- Xử lý các nút lựa chọn ---
            answers = container.query_selector_all("div.lead-scoring-survey__answer-button")
            if answers:
                choice = random.choice(answers)
                logging.info(f"[survey][{acc_id}] Chọn đáp án (step {step+1})")
                if status_cb and acc_id:
                    status_cb(acc_id, f"Survey bước {step+1}")
                choice.click()
                time.sleep(random.uniform(0.8, 1.5))  # delay sau click

                btn_next = container.query_selector("button.pf-btn-primary")
                if btn_next and btn_next.is_visible():
                    logging.info(f"[survey][{acc_id}] Nhấn Next")
                    btn_next.click()
                    time.sleep(random.uniform(1.5, 2.5))
                continue

            # --- Nếu không có gì để chọn / điền ---
            logging.info(f"[survey][{acc_id}] Không tìm thấy input hay answer (step {step+1}) → thoát")
            break

        logging.info(f"[survey][{acc_id}] Survey kết thúc sau {max_steps} bước")
        if status_cb and acc_id:
            status_cb(acc_id, "Survey hoàn tất")
        return True

    except Exception as e:
        logging.exception(f"[survey][{acc_id}] Lỗi survey: {e}")
        if status_cb and acc_id:
            status_cb(acc_id, f"Lỗi survey: {e}")
        return False



def check_registration_success(page, fullname=None, timeout=180, idle_limit=15, status_cb=None, acc_id=None):
    start, last_url, idle, did_try_dashboard = time.time(), page.url, 0, False
    try:
        logging.info("[register] Chờ form đăng ký biến mất...")
        page.wait_for_selector("input[name='fullName']", state="detached", timeout=20000)
        logging.info("[register] Form đã biến mất.")
    except Exception:
        logging.info("[register] Không chắc form biến mất, tiếp tục polling...")

    def success_signals():
        if page.url and page.url.startswith("https://www.printful.com/dashboard/default"):
            logging.info("[register] Thành công! Đã vào dashboard mặc định.")
            if status_cb and acc_id:
                status_cb(acc_id, "Đăng ký thành công ✅")
            return True
        try:
            if page.query_selector("a[href='/orders']") or \
               page.query_selector("a[href='/stores']") or \
               page.query_selector("a[href='/products']"):
                logging.info("[register] Thành công! Phát hiện menu người dùng.")
                if status_cb and acc_id:
                    status_cb(acc_id, "Đăng ký thành công ✅")
                return True
        except Exception:
            pass
        return False

    while (time.time() - start) < timeout and idle < idle_limit:
        progressed = False

        # Survey
        try:
            if page.query_selector("div.lead-scoring-survey"):
                logging.info("[register] Survey xuất hiện → làm survey...")
                if status_cb and acc_id:
                    status_cb(acc_id, "Đang xử lý survey...")
                complete_survey(page, max_steps=50, idle_limit=15,
                                status_cb=status_cb, acc_id=acc_id)
                progressed, idle = True, 0
                if success_signals():
                    return True
                continue
        except Exception:
            pass

        # Popup confirm email
        try:
            confirm_close = page.query_selector("button[data-test^='email-confirm-popup-closer-btn']")
            if confirm_close and confirm_close.is_visible():
                logging.info("[register] Đóng popup confirm email")
                confirm_close.click()
                try:
                    page.wait_for_selector("button[data-test^='email-confirm-popup-closer-btn']",
                                           state="detached", timeout=10000)
                except Exception:
                    pass
                progressed, idle = True, 0
                if success_signals():
                    return True
                continue
        except Exception:
            pass

        # Thành công?
        if success_signals():
            return True

        # URL thay đổi
        if page.url != last_url:
            last_url, progressed, idle = page.url, True, 0

        # Fallback chuyển /dashboard (sau 60s) nhưng chỉ khi không có survey
        if not did_try_dashboard and (time.time() - start) > 60:
            if not page.query_selector("div.lead-scoring-survey"):
                logging.info("[register] Không thấy survey, chuyển hướng /dashboard để xác nhận...")
                if status_cb and acc_id:
                    status_cb(acc_id, "Chuyển hướng /dashboard...")
                try:
                    page.goto("https://www.printful.com/dashboard", timeout=30000)
                    try:
                        page.wait_for_load_state("domcontentloaded", timeout=10000)
                    except Exception:
                        pass
                    did_try_dashboard, progressed, idle = True, True, 0
                    if success_signals():
                        return True
                    continue
                except Exception as e:
                    logging.warning(f"[register] goto /dashboard lỗi: {e}")
            else:
                logging.info("[register] Survey vẫn có thể xuất hiện → tiếp tục chờ.")

        if not progressed:
            idle += 1
            time.sleep(1)

    # Nếu tới đây là hết thời gian/idle
    logging.error("[register] Hết thời gian hoặc không có tiến triển để xác nhận đăng ký.")
    if status_cb and acc_id:
        status_cb(acc_id, "Đăng ký thất bại ❌")
    return False

def login_account(page, email, password, status_cb=None, acc_id=None):
    import time, logging
    try:
        page.goto("https://www.printful.com/auth/login", timeout=60000)
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # điền email
        page.fill("input[name='email']", email)
        # điền password
        page.fill("input[name='password']", password)
        # click nút Login
        page.click("button[type='submit']")

        if status_cb and acc_id:
            status_cb(acc_id, "Đã submit login form...")

        # chờ dashboard
        page.wait_for_url("**/dashboard", timeout=30000)
        logging.info(f"[Account {acc_id}] Login thành công ✅")
        if status_cb and acc_id:
            status_cb(acc_id, "Login thành công ✅")
        return True
    except Exception as e:
        logging.error(f"[Account {acc_id}] Lỗi khi login: {e}")
        if status_cb and acc_id:
            status_cb(acc_id, "Login thất bại ❌")
        return False
    

def do_deposit(page, amount, status_cb=None, acc_id=None):
    import time, logging
    try:
        page.goto("https://www.printful.com/dashboard/deposit", timeout=60000)
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        if status_cb: status_cb(acc_id, f"Đang mở deposit page...")

        # chọn số tiền
        page.fill("input[name='amount']", str(amount))

        # chọn phương thức thanh toán (ví dụ: PayPal)
        btn = page.query_selector("button[data-test='deposit-paypal-btn']")
        if btn and btn.is_visible():
            btn.click()
            logging.info(f"[Deposit] Submit PayPal {amount}")
        else:
            logging.warning("[Deposit] Không tìm thấy nút PayPal")

        if status_cb: status_cb(acc_id, f"Đã submit deposit {amount}")

        time.sleep(3)
        return True
    except Exception as e:
        logging.error(f"Lỗi deposit: {e}")
        return False
    
def add_billing_info(page, fullname, address, city, state, zipcode, status_cb=None, acc_id=None):
    import time, logging
    try:
        logging.info(f"[Billing][{acc_id}] Mở trang billing...")
        page.goto("https://www.printful.com/dashboard/billing", timeout=60000)
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        if status_cb: status_cb(acc_id, "Đang điền form billing...")

        # Điền Full Name
        logging.info(f"[Billing][{acc_id}] Điền fullname: {fullname}")
        page.click("input[name='fullName']")
        page.type("input[name='fullName']", fullname, delay=100)

        # Điền Address
        logging.info(f"[Billing][{acc_id}] Điền address: {address}")
        page.click("input[name='addressLine1']")
        page.type("input[name='addressLine1']", address, delay=100)

        # Điền City
        logging.info(f"[Billing][{acc_id}] Điền city: {city}")
        page.click("input[name='city']")
        page.type("input[name='city']", city, delay=100)

        # Điền State
        logging.info(f"[Billing][{acc_id}] Điền state: {state}")
        page.click("input[name='state']")
        page.type("input[name='state']", state, delay=100)

        # Điền Zipcode
        logging.info(f"[Billing][{acc_id}] Điền zipcode: {zipcode}")
        page.click("input[name='zip']")
        page.type("input[name='zip']", zipcode, delay=100)

        # Submit form
        save_btn = page.query_selector("button[type='submit']")
        if save_btn and save_btn.is_visible():
            logging.info(f"[Billing][{acc_id}] Nhấn submit form billing")
            save_btn.click()
            if status_cb: status_cb(acc_id, "Đã submit billing info")
        else:
            logging.warning(f"[Billing][{acc_id}] Không tìm thấy nút submit")
            if status_cb: status_cb(acc_id, "Không tìm thấy nút submit billing")
            return False

        time.sleep(3)  # đợi form xử lý
        logging.info(f"[Billing][{acc_id}] Hoàn tất add billing")
        return True

    except Exception as e:
        logging.exception(f"[Billing][{acc_id}] Lỗi add billing: {e}")
        if status_cb: status_cb(acc_id, f"Lỗi billing: {e}")
        return False
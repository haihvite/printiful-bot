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
def complete_survey(page, max_steps=50, idle_limit=15, status_cb=None, acc_id=None):
    """
    Xử lý survey sau khi đăng ký Printful.
    - Trả lời từng câu với delay ngẫu nhiên dài để giống người thật.
    - Dừng khi container biến mất hoặc đạt max_steps/idle_limit.
    """
    steps, idle = 0, 0

    while steps < max_steps and idle < idle_limit:
        container = page.query_selector("div.lead-scoring-survey")
        if not container:
            logging.info("[survey] Không còn survey.")
            return

        answers = page.locator("div.lead-scoring-survey__answer-button")
        try:
            answers.first.wait_for(state="visible", timeout=10000)
        except Exception:
            idle += 1
            time.sleep(1)
            continue

        count = answers.count()
        if count == 0:
            logging.info("[survey] Hết câu hỏi.")
            return

        # chọn random một đáp án
        idx = random.randrange(count)
        choice = answers.nth(idx)

        try:
            text = choice.inner_text(timeout=1000).strip()
        except Exception:
            text = "N/A"

        logging.info(f"[survey] Đang xử lý survey (bước {steps+1}): {text}")
        if status_cb and acc_id:
            status_cb(acc_id, f"Survey bước {steps+1}: {text}")

        # mô phỏng người đọc câu hỏi
        time.sleep(random.uniform(2.5, 5.0))

        # mô phỏng người rê chuột rồi click
        human_delay(1.0, 2.5)
        try:
            choice.click(timeout=5000)
        except Exception as e:
            logging.warning(f"[survey] Lỗi click answer: {e}, chờ 1s rồi thử tiếp")
            idle += 1
            time.sleep(1)
            continue

        # mô phỏng người đọc câu tiếp theo
        time.sleep(random.uniform(3.0, 6.0))

        steps += 1

        # stop early nếu đã thấy dashboard
        if page.url.startswith("https://www.printful.com/dashboard/default"):
            logging.info("[survey] Đã detect dashboard → dừng survey sớm.")
            return

        # check tiến triển (URL hoặc câu hỏi thay đổi)
        prev_url, changed = page.url, False
        for _ in range(6):
            time.sleep(0.6)
            if not page.query_selector("div.lead-scoring-survey"):
                changed = True
                break
            if page.url != prev_url:
                changed = True
                break
        idle = 0 if changed else (idle + 1)

    logging.info("[survey] Dừng survey (đạt giới hạn bước hoặc idle).")


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

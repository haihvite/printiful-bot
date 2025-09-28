import requests
import time
from playwright.sync_api import sync_playwright
import logging


class GpmProfile:
    def __init__(self, profile_id=None, api_url="http://127.0.0.1:19995"):
        self.profile_id = profile_id
        self.api_url = api_url
        self.remote_debugging = None
        self.browser = None
        self.context = None
        self.page = None
        self.play = None

    def create_profile(self, payload):
        """Tạo profile mới trong GPM bằng payload đã chuẩn hóa"""
        url = f"{self.api_url}/api/v3/profiles/create"
        logging.info(f"Tạo profile mới với tên {payload['profile_name']}")
        logging.debug(f"Payload gửi đi: {payload}")

        resp = requests.post(url, headers={"Content-Type": "application/json"}, json=payload)
        resp.raise_for_status()
        data = resp.json()
        logging.debug(f"GPM create_profile response: {data}")

        if not data.get("success"):
            raise Exception(f"Tạo profile thất bại: {data}")

        self.profile_id = data["data"]["id"]
        logging.info(f"Đã tạo profile mới: {self.profile_id}")
        return self.profile_id

    def start(self, width=925, height=925, x=100, y=100):
        logging.info(f"Đang mở profile {self.profile_id}")
        url = f"{self.api_url}/api/v3/profiles/start/{self.profile_id}?win_size={width},{height}&win_pos={x},{y}"
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            raise Exception(f"Không mở được profile: {data}")
        self.remote_debugging = data["data"]["remote_debugging_address"]
        logging.info(f"Profile {self.profile_id} đã khởi động, remote_debugging={self.remote_debugging}")
        time.sleep(5)

    def connect(self):
        if not self.remote_debugging:
            raise Exception("Bạn cần gọi start() trước khi connect()")
        self.play = sync_playwright().start()
        self.browser = self.play.chromium.connect_over_cdp(f"http://{self.remote_debugging}")
        self.context = self.browser.contexts[0]
        self.page = self.context.pages[0]
        return self.page

    def stop(self):
        logging.info(f"Dừng profile {self.profile_id}")
        requests.get(f"{self.api_url}/api/v3/profiles/stop/{self.profile_id}")
        if self.browser:
            self.browser.close()
        if self.play:
            self.play.stop()

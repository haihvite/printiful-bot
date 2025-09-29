import requests
import logging

API_URL = "http://127.0.0.1:10101/api/proxy"
API_TYPE = "socks5"   # hoặc http nếu cần
BASE_PORT = 60100     # port mặc định

def get_proxies(count: int = 1, base_port: int = BASE_PORT, proxy_type: str = API_TYPE, country: str = "US"):
    """
    Lấy danh sách proxy từ API 9Proxy.
    Ví dụ: count=5, base_port=60100 → trả về 60100..60104
    """
    try:
        url = f"{API_URL}?t=2&num={count}&port={base_port}&country={country}"
        logging.info(f"[Proxy] Gọi API lấy {count} proxy từ {url}")
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if data.get("error"):
            logging.error(f"[Proxy] API báo lỗi: {data}")
            return []

        proxies = []
        for i, entry in enumerate(data.get("data", [])):
            # entry có dạng "127.0.0.1:60100"
            if ":" not in entry:
                logging.warning(f"[Proxy] entry không hợp lệ: {entry}")
                continue
            host, port_str = entry.split(":")
            port = int(port_str)

            proxy = {
                "host": host,
                "port": port,
                "username": None,
                "password": None,
                "type": proxy_type,
                "local_port": port  # ở đây local_port = port do API cấp
            }
            proxies.append(proxy)
            logging.info(f"[Proxy] Proxy {i+1}/{count}: {proxy_type}://{host}:{port}")

        logging.info(f"[Proxy] Hoàn tất lấy {len(proxies)}/{count} proxy (base_port={base_port}, country={country})")
        return proxies

    except Exception as e:
        logging.exception(f"[Proxy] Lỗi khi lấy proxy: {e}")
        return []
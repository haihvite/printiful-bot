import requests
import logging


def get_proxies(count, country="US", proxy_type="socks5"):
    """Lấy proxy từ 9Proxy API"""
    url = f"http://127.0.0.1:10101/api/proxy?t=2&num={count}&country={country}"
    logging.info(f"Đang gọi API lấy {count} proxy: {url}")
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    logging.debug(f"Proxy API response: {data}")

    if not data or "data" not in data or not data["data"]:
        raise Exception("Không lấy được proxy từ 9Proxy")

    proxies = []
    for proxy_raw in data["data"]:
        host, port = proxy_raw.split(":")
        proxies.append({
            "host": host,
            "port": int(port),
            "username": "",
            "password": "",
            "type": proxy_type
        })

    logging.info(f"Đã lấy {len(proxies)} proxy thành công")
    return proxies

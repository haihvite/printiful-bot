import requests
import logging
import json
import os

PORT_FILE = "ports.json"
BASE_PORT = 60100

def load_ports():
    if not os.path.exists(PORT_FILE):
        return {"last_used": BASE_PORT - 1, "in_use": []}
    with open(PORT_FILE, "r") as f:
        return json.load(f)

def save_ports(data):
    with open(PORT_FILE, "w") as f:
        json.dump(data, f)

def allocate_port():
    """Tạo port local tăng dần (cho mapping với proxy IP)"""
    data = load_ports()
    port = data["last_used"] + 1
    data["last_used"] = port
    data["in_use"].append(port)
    save_ports(data)
    logging.info(f"[proxy_utils] Allocated port {port}")
    return port

def release_port(port):
    """Giải phóng port"""
    data = load_ports()
    if port in data["in_use"]:
        data["in_use"].remove(port)
        save_ports(data)
        logging.info(f"[proxy_utils] Released port {port}")

def get_proxies(count, country="US", proxy_type="socks5"):
    """
    Lấy proxies từ 9Proxy API và phân bổ qua port manager.
    Trả về list dict proxy {host, port, type}
    """
    url = f"http://127.0.0.1:10101/api/proxy?t=2&num={count}&country={country}"
    logging.info(f"Đang gọi API lấy {count} proxy: {url}")
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()

    if not data or "data" not in data or not data["data"]:
        raise Exception("Không lấy được proxy từ 9Proxy")

    proxies = []
    for proxy_raw in data["data"]:
        host, port_api = proxy_raw.split(":")
        local_port = allocate_port()  # gán port local cho từng proxy
        proxies.append({
            "host": host,
            "port": int(port_api),     # port thật từ API 9Proxy
            "local_port": local_port,  # port local để map vào profile
            "username": "",
            "password": "",
            "type": proxy_type
        })

    logging.info(f"Đã lấy {len(proxies)} proxy thành công")
    return proxies

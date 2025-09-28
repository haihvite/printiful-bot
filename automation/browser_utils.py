import random
import logging


def get_random_browser_version():
    versions = [
        "139.0.7258.139",
        "137.0.7151.41",
        "135.0.7049.42",
        "134.0.6998.89",
        "132.0.6834.84",
        "129.0.6533.73",
        "127.0.6533.73",
        "124.0.6367.29",
        "121.0.6167.140",
        "119.0.6045.124",
    ]
    top5 = versions[:5]
    chosen = random.choice(top5)
    logging.info(f"Đã chọn browser_version: {chosen}")
    return chosen


def make_user_agent(browser_version):
    return (f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{browser_version} Safari/537.36")

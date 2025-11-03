import requests
import json

AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
GRAPH_URL = "https://graph.microsoft.com/v1.0"

def get_access_token(client_id: str, refresh_token: str) -> str:
    data = {
        "client_id": client_id,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        # Bỏ scope đi để thử lấy mặc định
    }
    r = requests.post(AUTH_URL, data=data, timeout=30)
    try:
        r.raise_for_status()
    except requests.HTTPError:
        print("DEBUG response:", r.text)  # In ra chi tiết
        raise
    j = r.json()
    if "access_token" not in j:
        raise RuntimeError(f"Không có access_token: {j}")
    return j["access_token"]

def get_all_mails(client_id: str, refresh_token: str, top: int = 50):
    token = get_access_token(client_id, refresh_token)
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_URL}/me/messages?$top={top}&$orderby=receivedDateTime desc"
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json().get("value", [])

def read_accounts_from_file(file_path: str):
    accounts = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) < 4:
                print(f"Bỏ qua dòng sai định dạng: {line}")
                continue
            email, password, refresh_token, client_id = parts
            accounts.append({
                "email": email,
                "client_id": client_id,
                "refresh_token": refresh_token
            })
    return accounts

if __name__ == "__main__":
    FILE_INPUT = "accounts.txt"   # file txt chứa danh sách account
    accounts = read_accounts_from_file(FILE_INPUT)

    for acc in accounts:
        print("="*50)
        print(f"Đang đọc mail cho: {acc['email']}")
        try:
            mails = get_all_mails(acc["client_id"], acc["refresh_token"], top=50)
            if not mails:
                print("Không có mail.")
                continue
            for m in mails:
                subj = m.get("subject", "")
                frm = m.get("from", {}).get("emailAddress", {}).get("address", "")
                dt = m.get("receivedDateTime", "")
                print(f"- [{dt}] {subj} | From: {frm}")
        except Exception as e:
            print("Lỗi:", e)

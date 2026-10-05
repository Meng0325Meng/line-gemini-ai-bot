import os
import sys
import json
import hmac
import hashlib
import base64
import requests
from dotenv import load_dotenv

# 處理 Windows 終端編碼
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()

from gemini_service import gemini_service

def run_cli_chat():
    """本機終端機與 Gemini AI 互動測試"""
    print("\n" + "=" * 55)
    print("🤖【Gemini AI 本地對話測試終端】")
    print("=" * 55)

    if not gemini_service.is_configured():
        print("⚠️ 偵測到尚未設定 GEMINI_API_KEY！")
        print("請選擇：")
        print("1. 在 .env 檔案中填入 GEMINI_API_KEY (推薦)")
        print("2. 在下方直接輸入臨時 API Key 進行測試\n")
        temp_key = input("請輸入 Gemini API Key（或按 Enter 放棄）: ").strip()
        if temp_key:
            os.environ["GEMINI_API_KEY"] = temp_key
            gemini_service._init_client()
        else:
            print("❌ 未輸入 API Key，無法進行對話測試。")
            return

    print("\n✅ AI 服務已就緒！")
    print("提示：")
    print(" - 輸入任何問題即可開始對話")
    print(" - 輸入 /clear 可清除歷史對話記憶")
    print(" - 輸入 exit 或 quit 即可退出測試\n")

    user_id = "local_test_user"
    while True:
        try:
            prompt = input("👤 您: ").strip()
            if not prompt:
                continue
            if prompt.lower() in ["exit", "quit", "q"]:
                print("👋 測試結束，再見！")
                break
            if prompt.lower() in ["/clear", "clear", "清除"]:
                gemini_service.clear_chat(user_id)
                print("🧹 [系統] 對話歷史記憶已清除！\n")
                continue

            print("🤖 思考中...", end="\r")
            reply = gemini_service.generate_reply(user_id, prompt)
            print(f"🤖 AI: {reply}\n")

        except (KeyboardInterrupt, EOFError):
            print("\n👋 測試結束！")
            break

def run_webhook_test():
    """向本地運行的 Flask 伺服器發送模擬 Webhook 請求"""
    port = os.getenv("PORT", "5000")
    channel_secret = os.getenv("LINE_CHANNEL_SECRET", "").strip()
    if not channel_secret or channel_secret == "your_line_channel_secret_here":
        channel_secret = "dummy_secret"

    url = f"http://127.0.0.1:{port}/callback"
    print(f"\n📡 正在向本地 Webhook 發送測試請求: {url}")

    # 模擬 LINE Webhook 負載 (空事件列表，類似 LINE 後台的 Verify 請求)
    payload = json.dumps({"destination": "U1234567890", "events": []})
    
    # 計算 X-Line-Signature
    hash_val = hmac.new(
        channel_secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).digest()
    signature = base64.b64encode(hash_val).decode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "X-Line-Signature": signature
    }

    try:
        resp = requests.post(url, data=payload, headers=headers, timeout=5)
        print(f"狀態碼: {resp.status_code}")
        print(f"伺服器回應: {resp.text}")
        if resp.status_code == 200:
            print("✅ Webhook 簽章與路徑測試成功！")
        else:
            print(f"⚠️ 收到非 200 回應，請確認 LINE_CHANNEL_SECRET 是否與伺服端一致。")
    except requests.exceptions.ConnectionError:
        print(f"❌ 連線失敗！請確認 app.py 是否已在另一終端機執行 (http://127.0.0.1:{port})")
    except Exception as e:
        print(f"❌ 測試過程發生例外: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--webhook":
        run_webhook_test()
    else:
        run_cli_chat()

import os
import sys
import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from flask import Flask, request, abort, jsonify
from dotenv import load_dotenv

# 解決 Windows 終端編碼問題
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()

# 設定日誌記錄格式
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("line_bot")

# 讀取環境變數
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "").strip()
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
PORT = int(os.getenv("PORT", 5000))

# 匯入 LINE SDK 與 Gemini 服務
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    PushMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)
from gemini_service import gemini_service

# 初始化 Flask App
app = Flask(__name__)

# 檢查 LINE 設定
is_line_configured = bool(
    LINE_CHANNEL_SECRET and 
    LINE_CHANNEL_SECRET != "your_line_channel_secret_here" and
    LINE_CHANNEL_ACCESS_TOKEN and 
    LINE_CHANNEL_ACCESS_TOKEN != "your_line_channel_access_token_here"
)

if not is_line_configured:
    logger.warning("=" * 60)
    logger.warning("【提醒】尚未設定完整的 LINE_CHANNEL_SECRET 與 LINE_CHANNEL_ACCESS_TOKEN！")
    logger.warning("請編輯專案中的 .env 檔案填入金鑰，LINE 訊息回覆功能才能正常使用。")
    logger.warning("=" * 60)

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN or "dummy_token")
handler = WebhookHandler(LINE_CHANNEL_SECRET or "dummy_secret")
background_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="line-ai")
_user_locks_guard = Lock()
_user_locks = {}

@app.route("/", methods=["GET"])
def index():
    """健康檢查與系統狀態頁面"""
    status_gemini = "已設定 ✅" if gemini_service.is_configured() else "未設定 ⚠️ (請至 .env 設定 GEMINI_API_KEY)"
    status_line_secret = "已設定 ✅" if (LINE_CHANNEL_SECRET and LINE_CHANNEL_SECRET != "your_line_channel_secret_here") else "未設定 ⚠️"
    status_line_token = "已設定 ✅" if (LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_ACCESS_TOKEN != "your_line_channel_access_token_here") else "未設定 ⚠️"

    html = f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>LINE AI Bot 服務狀態</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background: #f4f6f9; color: #333; margin: 0; padding: 40px 20px; }}
            .card {{ max-width: 600px; margin: 0 auto; background: #fff; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); padding: 30px; }}
            h1 {{ color: #06c755; margin-top: 0; display: flex; align-items: center; gap: 10px; font-size: 24px; }}
            .status-item {{ display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #eee; }}
            .label {{ font-weight: 600; color: #555; }}
            .badge {{ font-weight: 500; }}
            .webhook-box {{ background: #f8fafc; border-left: 4px solid #06c755; padding: 12px 16px; margin: 20px 0; border-radius: 4px; }}
            code {{ background: #edf2f7; padding: 2px 6px; border-radius: 4px; font-size: 14px; }}
            .footer {{ margin-top: 25px; font-size: 13px; color: #777; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🤖 LINE AI 智慧對話機器人</h1>
            <p>伺服器運作狀態：<strong>正常連線中 (Running)</strong></p>
            
            <div class="webhook-box">
                <strong>Webhook 路徑：</strong> <code>/callback</code><br>
                <strong>請求方式：</strong> <code>POST</code>
            </div>

            <h3>系統設定檢測：</h3>
            <div class="status-item">
                <span class="label">Google Gemini API:</span>
                <span class="badge">{status_gemini}</span>
            </div>
            <div class="status-item">
                <span class="label">LINE Channel Secret:</span>
                <span class="badge">{status_line_secret}</span>
            </div>
            <div class="status-item">
                <span class="label">LINE Channel Access Token:</span>
                <span class="badge">{status_line_token}</span>
            </div>

            <div class="footer">
                提示：若要讓 LINE 伺服器連線至本機，請使用 ngrok：<code>ngrok http {PORT}</code><br>
                並在 LINE Developers Console 設定 Webhook URL 為 <code>https://&lt;your-domain&gt;/callback</code>
            </div>
        </div>
    </body>
    </html>
    """
    return html

@app.route("/callback", methods=["POST"])
def callback():
    """接收 LINE Messaging API 的 Webhook 請求"""
    signature = request.headers.get("X-Line-Signature")
    if not signature:
        logger.warning("收到沒有 X-Line-Signature 標頭的請求")
        abort(400)

    body = request.get_data(as_text=True)
    logger.debug(f"收到 Webhook 請求內容: {body}")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.error("X-Line-Signature 簽章驗證失敗，請檢查 LINE_CHANNEL_SECRET 是否正確！")
        abort(400)
    except Exception as e:
        logger.error(f"處理 Webhook 事件時發生錯誤: {e}", exc_info=True)
        # LINE 規定只要收到請求就應返回 200，避免 LINE 伺服器因伺服端邏輯錯誤而不斷重試
        return "Internal Error Handled", 200

    return "OK"

@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    """處理文字訊息事件"""
    source = event.source
    push_target = (
        getattr(source, "user_id", None)
        or getattr(source, "group_id", None)
        or getattr(source, "room_id", None)
    )
    user_id = push_target or "default_user"
    user_text = event.message.text.strip()
    logger.info(f"收到來自 [{user_id}] 的文字訊息: {user_text}")

    # 特殊指令判斷
    if user_text.lower() in ["/help", "說明", "幫助", "help", "功能"]:
        reply_content = (
            "🤖【AI 智慧助理功能指引】\n\n"
            "您可以直接傳送任何問題或聊天內容，我會使用 Gemini AI 為您解答！\n\n"
            "📌 常用指令：\n"
            "• /help 或「說明」：查看此功能選單\n"
            "• /clear 或「清除」：清除歷史對話記憶，重新開啟新對話\n"
            "• /ping：測試連線狀態"
        )
    elif user_text.lower() in ["/clear", "清除", "重設", "clear"]:
        gemini_service.clear_chat(user_id)
        reply_content = "🧹 已成功清除歷史記憶！我們可以聊聊新的話題囉 😊"
    elif user_text.lower() in ["/ping", "ping"]:
        reply_content = "🏓 Pong! LINE AI 機器人連線與服務運作正常！"
    else:
        # 先在 reply token 有效期間內確認收到，再背景查詢並以 push message 傳回答案。
        reply_content = "收到，我正在查詢資料，稍後會把答案傳給你。"

    # 回覆使用者訊息
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_content)]
                )
            )
        logger.info(f"已成功回覆使用者 [{user_id}]")
    except Exception as e:
        logger.error(f"發送 LINE 回覆訊息失敗: {e}", exc_info=True)

    # AI 查詢可能超過 LINE reply token 的有效時間，因此答案改用 push message 發送。
    if user_text.lower() not in ["/help", "說明", "幫助", "help", "功能",
                                 "/clear", "清除", "重設", "clear", "/ping", "ping"]:
        if not push_target:
            logger.error("Webhook 事件沒有可用的 LINE user/group/room ID，無法傳送後續答案")
            return
        background_executor.submit(_generate_and_push, user_id, push_target, user_text)


def _generate_and_push(user_id: str, push_target: str, prompt: str):
    """在背景產生答案，避免等待 Gemini 時耗盡 LINE reply token。"""
    try:
        # 同一位使用者共用 Gemini 對話記憶，避免多個背景請求同時操作同一個 session。
        with _user_locks_guard:
            user_lock = _user_locks.setdefault(user_id, Lock())
        with user_lock:
            reply_content = gemini_service.generate_reply(user_id=user_id, prompt=prompt)
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.push_message(
                    PushMessageRequest(
                        to=push_target,
                        messages=[TextMessage(text=reply_content)],
                    )
                )
        logger.info(f"已透過 push message 傳送 AI 回覆給 [{user_id}]")
    except Exception as e:
        logger.error(f"背景產生或傳送 AI 回覆失敗 [{user_id}]: {e}", exc_info=True)

if __name__ == "__main__":
    logger.info(f"啟動 LINE AI Bot 伺服器，監聽連接埠: {PORT} ...")
    logger.info(f"本機狀態頁面: http://127.0.0.1:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)

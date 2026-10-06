import os
import sys
import logging
from typing import Dict, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types

# 處理 Windows 終端編碼
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()
logger = logging.getLogger(__name__)

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
AVAILABLE_MODELS = [DEFAULT_MODEL]

SYSTEM_INSTRUCTION = (
    "你是一位親切、樂於助人的繁體中文 AI 智慧助理。"
    "請一律使用台灣繁體中文（zh-TW）回答。"
    "回答風格請保持清晰、精準且排版易讀（適當使用分段或條列說明）。"
    "考量手機 LINE 聊天室的閱讀體驗，回覆請保持簡明扼要，避免過多無意義的廢話。"
    "若未使用網路搜尋，遇到最新或需要查證的資訊時，請明確說明無法確認，不要捏造具體姓名、職稱或資料。"
)

class GeminiService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.web_search_enabled = os.getenv(
            "GEMINI_WEB_SEARCH", "false"
        ).strip().lower() not in {"0", "false", "no", "off"}
        self.client: Optional[genai.Client] = None
        self._user_chats: Dict[str, any] = {}
        self.current_model = DEFAULT_MODEL
        self._init_client()

    def _init_client(self):
        """初始化 Gemini Client"""
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if self.api_key and self.api_key != "your_gemini_api_key_here":
            try:
                self.client = genai.Client(
                    api_key=self.api_key,
                    http_options=types.HttpOptions(
                        timeout=35000,
                        retry_options=types.HttpRetryOptions(attempts=1),
                    ),
                )
                logger.info(f"Google Gemini Client 初始化成功！預設模型: {self.current_model}")
            except Exception as e:
                logger.error(f"Gemini Client 初始化失敗: {e}")
                self.client = None
        else:
            self.client = None

    def is_configured(self) -> bool:
        """檢查是否已正確設定 GEMINI_API_KEY"""
        return self.client is not None

    def clear_chat(self, user_id: str) -> bool:
        """清除指定使用者的歷史對話記憶"""
        # Chat cache keys also contain the model name (user_id_model_name).
        keys = [key for key in self._user_chats if key.startswith(f"{user_id}_")]
        for key in keys:
            del self._user_chats[key]
        return bool(keys)

    def get_or_create_chat(
        self, user_id: str, model_name: str = None, enable_search: bool = True
    ):
        """取得或建立使用者的對話 Session"""
        model = model_name or self.current_model
        search_suffix = "search" if enable_search else "no_search"
        cache_key = f"{user_id}_{model}_{search_suffix}"
        if cache_key not in self._user_chats:
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.7,
                tools=(
                    [types.Tool(google_search=types.GoogleSearch())]
                    if enable_search
                    else None
                ),
            )
            chat = self.client.chats.create(
                model=model,
                config=config
            )
            self._user_chats[cache_key] = chat
        return self._user_chats[cache_key]

    def generate_reply(self, user_id: str, prompt: str) -> str:
        """接收使用者訊息並在有限時間內生成 AI 回覆"""
        if not self.is_configured():
            self._init_client()

        if not self.is_configured():
            return (
                "⚠️ 尚未設定 Gemini API 金鑰！\n\n"
                "請在專案目錄下的 .env 檔案中填入有效的 GEMINI_API_KEY。"
            )

        prompt_clean = prompt.strip()
        if not prompt_clean:
            return "請問有什麼我可以協助您的嗎？😊"

        # 只嘗試一個模型，並由 HTTP timeout 限制等待時間，盡量在 LINE reply token
        # 的有效時間內完成回覆。
        last_error = None
        for model in AVAILABLE_MODELS:
            try:
                chat = self.get_or_create_chat(
                    user_id,
                    model_name=model,
                    enable_search=self.web_search_enabled,
                )
                response = chat.send_message(prompt_clean)
                reply_text = response.text or "（AI 未回傳任何文字）"

                # 把 Gemini 搜尋 grounding metadata 中的網頁來源一起回給使用者。
                sources = []
                candidates = getattr(response, "candidates", None) or []
                if candidates:
                    metadata = getattr(candidates[0], "grounding_metadata", None)
                    for chunk in getattr(metadata, "grounding_chunks", None) or []:
                        web_source = getattr(chunk, "web", None)
                        url = getattr(web_source, "uri", None)
                        if url and url not in [source[1] for source in sources]:
                            title = getattr(web_source, "title", None) or "資料來源"
                            sources.append((title, url))
                        if len(sources) >= 3:
                            break
                if sources:
                    reply_text += "\n\n參考來源：\n" + "\n".join(
                        f"{title}：{url}" for title, url in sources
                    )

                # LINE 限制單則文字上限 5000 字元
                if len(reply_text) > 4500:
                    reply_text = reply_text[:4500] + "\n\n...（內容過長，已自動截斷）"

                return reply_text.strip()

            except Exception as e:
                last_error = e
                logger.warning(f"模型 {model} 呼叫異常: {e}")
                # 清理異常 session
                self.clear_chat(user_id)

        # 若啟用的網路搜尋因 API 方案或服務問題無法使用，再嘗試一般回答。
        # 預設關閉搜尋以避免意外產生搜尋 grounding 費用。
        if self.web_search_enabled:
            try:
                chat = self.get_or_create_chat(
                    user_id, model_name=self.current_model, enable_search=False
                )
                response = chat.send_message(prompt_clean)
                reply_text = response.text or "（AI 未回傳任何文字）"
                reply_text = "⚠️ 即時搜尋目前無法使用，以下回答可能不是最新資訊。\n\n" + reply_text
                return reply_text[:4400].strip()
            except Exception as e:
                last_error = e

        logger.error(f"所有模型嘗試均失敗，最後錯誤: {last_error}", exc_info=True)
        return "抱歉，目前 AI 伺服器忙線中，請稍後片刻再試一次！"

# 全域單例
gemini_service = GeminiService()

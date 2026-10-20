# 🤖 LINE AI 智慧對話機器人（Apps Script + Gemini）

這是課堂專題用的 LINE AI 機器人，整合 **Google Apps Script、Gemini API** 和 **LINE Messaging API**。目前 LINE Webhook 指向 Apps Script Web App；Python/Flask 版保留為替代轉接站。預設使用 Gemini 一般文字 API，不啟用可能產生額外費用的網路搜尋 grounding。

## 專題修改內容

- 以 Apps Script 接收 LINE Webhook，使用 Gemini API 產生繁體中文回答。
- 加入東華大學陳文盛老師的公開資料查詢，回答附上東華官方來源；取不到網頁時提供標示過的備援介紹。
- 修正 Apps Script 使用 `ContentService` 回覆時造成的 HTTP 302，改用 `HtmlService.createHtmlOutput()`。LINE Developers Console Webhook Verify 與 `/ping` 已實測成功。
- 加入 `/help`、`/clear`、`/ping`，並為教師查詢保留不含使用者 ID 的 Apps Script 執行紀錄，供課堂實測截圖。

---

## 📁 專案檔案結構

```
line-gemini-ai-bot/
├── apps-script/
│   ├── Code.gs             # 目前使用的 Apps Script LINE Webhook 與 Gemini 程式
│   └── 部署說明.md          # Apps Script 指令碼屬性、部署與驗證步驟
├── app.py                  # Flask 替代轉接站，接收及驗證 LINE Webhook
├── gemini_service.py       # Gemini API、多輪對話及教師資料上下文
├── ndhu_teacher_data.py    # 東華公開教師頁面擷取與來源處理
├── test_local.py           # 本地測試工具
├── requirements.txt        # Python 套件清單
├── render.yaml             # Render 替代部署設定
├── .env.example            # 環境變數範本（不含金鑰）
└── README.md               # 安裝、執行、部署與修改紀錄
```

---

## 🚀 快速上手教學

### 步驟 1：取得 Google Gemini API Key（免費）

1. 前往 [Google AI Studio](https://aistudio.google.com/)。
2. 使用您的 Google 帳號登入。
3. 點選左上角或右上角的 **「Get API key」** -> **「Create API key」**。
4. 複製產生的金鑰字串（稍後填入 `.env`）。

---

### 步驟 2：取得 LINE Developers 金鑰與設定

1. 前往 [LINE Developers Console](https://developers.line.biz/console/)。
2. 登入後，建立一個 **Provider**（若已有可略過）。
3. 點擊 **Create a new channel**，選擇 **Messaging API**。
4. 填寫機器人基本資料（名稱、頭像、類別等），完成建立。
5. 進入該 Channel，取得兩項重要金鑰：
   - **Basic settings 分頁**：找到 **Channel secret** 並複製。
   - **Messaging API 分頁**：拉到最下方找到 **Channel access token (long-lived)**，點擊 **Issue** 產生並複製。
6. ⚠️ **關鍵防踩坑設定（關閉 LINE 內建自動回應）**：
   - 前往 [LINE Official Account Manager (官方帳號管理後台)](https://manager.line.biz/)。
   - 點擊右上角 **「設定」** -> 左側選單 **「回應設定」**。
   - 將 **「回應模式」** 設為 **「聊天機器人 (Bot)」**。
   - 將 **「自動回應訊息」** 設為 **「停用」**（避免官方預設罐頭訊息重複打架）。
   - 將 **「Webhook」** 設為 **「啟用」**。

---

### 步驟 3：設定專案環境變數 (.env)

開啟專案根目錄下的 `.env` 檔案，填入剛剛取得的金鑰：

```ini
# LINE 相關設定
LINE_CHANNEL_SECRET=你的_LINE_CHANNEL_SECRET
LINE_CHANNEL_ACCESS_TOKEN=你的_LINE_CHANNEL_ACCESS_TOKEN

# Gemini API Key
GEMINI_API_KEY=你的_GEMINI_API_KEY

# 網路搜尋 grounding 預設關閉，避免搜尋費用
GEMINI_WEB_SEARCH=false

# 伺服器通訊埠 (預設 5000)
PORT=5000
```

維持 `GEMINI_WEB_SEARCH=false` 時，Gemini 不會查網路；遇到最新或需要查證的資訊時，回答可能無法確認。Google 搜尋 grounding 需要支援的 API 方案，可能產生費用，不建議課堂作業開啟。

AI 問題會在 Gemini 回覆後以 LINE Reply API 傳送；Reply API 不計入 LINE 官方帳號的訊息額度。Gemini API 有自己的免費層級與使用限制，且與個人 Gemini 會員分開計費。

---

### 步驟 4：安裝依賴套件

在終端機中執行：
```powershell
python -m pip install -r requirements.txt
```

---

### 步驟 5：本地快速測試（免開伺服器）

在正式串接 LINE 之前，您可以直接透過終端機與 Gemini AI 聊天，驗證 API Key 是否正常：

```powershell
python test_local.py
```
> 您可以在終端中直接輸入問題，AI 會即時回覆。輸入 `/clear` 可清除對話記憶，輸入 `exit` 可退出。

---

### 步驟 6：啟動伺服器與串接 LINE Webhook

#### 1. 啟動本機伺服器
```powershell
python app.py
```
啟動後可在瀏覽器開啟 [http://127.0.0.1:5000](http://127.0.0.1:5000) 查看伺服器健康狀態檢查頁面。

#### 2. 使用 ngrok 產生公開 HTTPS 網址
LINE 規定 Webhook 必須是具備 SSL 的公開網址。請開啟另一個終端機視窗，執行：
```powershell
ngrok http 5000
```
ngrok 會產生一組 Forwarding 網址，例如：`https://abc1234.ngrok-free.app`。

#### 3. 至 LINE Developers 後台填入 Webhook
1. 回到 [LINE Developers Console](https://developers.line.biz/console/) 的 **Messaging API** 分頁。
2. 找到 **Webhook URL**，填入：
   ```
   https://你的ngrok網址/callback
   ```
   *(例如：`https://abc1234.ngrok-free.app/callback`)*
3. 點擊 **Update**，並點選 **Verify** 進行驗證（顯示 Success 即代表連線成功）。
4. 將下方的 **Use Webhook** 開關切換為 **開啟 (Enabled)**。

現在，用手機掃描該頁面上的 **QR code** 加入您的 LINE Bot 好友，傳送訊息給它即可體驗 AI 對話！

---

## Apps Script 部署（目前使用）

Apps Script 程式位於 [`apps-script/Code.gs`](apps-script/Code.gs)，完整步驟見 [`apps-script/部署說明.md`](apps-script/%E9%83%A8%E7%BD%B2%E8%AA%AA%E6%98%8E.md)。

1. 在 [Google Apps Script](https://script.google.com/home) 建立專案，將 `Code.gs` 貼入並儲存。
2. 在「專案設定 → 指令碼屬性」設定 `LINE_CHANNEL_ACCESS_TOKEN`、`GEMINI_API_KEY`、`WEBHOOK_ACCESS_KEY`；金鑰不要放進 Repo。
3. 部署為網頁應用程式，執行身分選「我」，存取對象選「任何人」。
4. 將部署產生的 `/exec?k=你的存取金鑰` 設為 LINE Developers Console 的 Webhook URL，開啟 Use webhook。
5. 按 Verify，然後用 LINE 傳 `/ping`。成功時機器人會回覆 Pong 訊息。

目前 Apps Script Web App 已部署第 3 版；教師查詢的執行紀錄只記錄指定教師問題，不記錄 LINE 使用者 ID 或其他聊天內容。

### 課堂實測截圖

1. 在手機 LINE 對機器人傳送「東華大學陳文盛老師是誰？」；截圖需看得到回答與回答末尾的東華官方來源網址。
2. 在電腦 Apps Script 專案左側選「執行項目」，開啟同一時間最新的 `doPost` 執行項目，截圖 `收到東華教師查詢：東華大學陳文盛老師是誰？` 這筆紀錄。
3. 將手機回答與 Apps Script 執行紀錄畫面一併保留，避免截圖包含任何 API 金鑰或含有 `?k=` 的 Webhook URL。

---

## 💡 內建指令

| 指令 | 說明 |
| :--- | :--- |
| 直接輸入文字 | 與 Gemini AI 進行多輪對話與諮詢 |
| `/help` 或 `說明` | 顯示功能介紹與可用指令說明 |
| `/clear` 或 `清除` | 清空當前與 AI 的對話歷史記憶，重新開啟新話題 |
| `/ping` | 測試機器人伺服器連線與心跳反應 |

---

## ☁️ 雲端 24 小時上線部署建議（Render 免費方案）

若希望程式放在雲端，並在推送至 GitHub `main` 分支時自動更新，可使用 [Render](https://render.com/) 免費 Web Service。專案已附 `render.yaml`，建立 Blueprint 時會依照設定建置並啟用自動部署：

1. 在 Render 選擇 **New > Blueprint**，連結 GitHub 並選擇 `Meng0325Meng/line-gemini-ai-bot`。
2. Render 讀取根目錄的 `render.yaml` 後，選擇免費方案並建立服務。
3. 在 Render 提示的環境變數欄位填入 `LINE_CHANNEL_SECRET`、`LINE_CHANNEL_ACCESS_TOKEN`、`GEMINI_API_KEY`。金鑰只填在 Render，不要放進 GitHub 或 `render.yaml`。
4. 部署完成後，取得 Render 網址，例如 `https://line-gemini-ai-bot.onrender.com`，到 LINE Developers Console 將 Webhook URL 改成 `https://你的Render網址/callback`，按 **Update** 再按 **Verify**。
5. Render 連結 GitHub `main` 分支後，之後每次推送都會自動建置和部署。

免費 Web Service 閒置 15 分鐘後會休眠，收到下一個請求時才喚醒，可能需要約一分鐘；因此適合課堂作業或展示，不保證第一則訊息即時回覆。Render 免費方案在用量超出時會停用服務，而不是在沒有付款方式時自動收費；請在建立服務時確認選的是 **Free**。Gemini API 的用量/費用仍與個人 Gemini 會員分開。

---

## 🧪 實測證明（2026-10-10）

### LINE Bot 收到訊息並處理 Gemini 暫時忙線

Render 服務日誌記錄到測試訊息「早安」及後續處理結果（使用者識別碼已省略）：

```text
14:12:33 INFO  line_bot: 收到文字訊息「早安」
14:12:50 INFO  Gemini API: HTTP 503 Service Unavailable
14:12:50 ERROR gemini_service: 503 UNAVAILABLE — Gemini 目前需求量高
14:12:51 INFO  line_bot: 已成功回覆使用者
14:12:51 INFO  POST /callback HTTP/1.1 200
```

**結果：** LINE Webhook 有收到訊息。當 Gemini 回傳 503 時，程式改回傳忙線提示；日誌顯示 LINE 回覆 API 呼叫成功，Webhook 也以 HTTP 200 結束。這筆紀錄同時呈現正常接收與 Gemini 暫時忙線的處理情形。

> 實際日誌由 Render Dashboard 擷取；為保護使用者隱私，公開紀錄省略 LINE 使用者識別碼。Render 原始日誌需要登入才能檢視。

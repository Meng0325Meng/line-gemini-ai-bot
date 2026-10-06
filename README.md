# 🤖 LINE AI 智慧對話機器人 (Python + Gemini + Flask)

這是一個輕量、易擴充的 LINE 智慧對話機器人，整合 **Google Gemini API** 與 **LINE Messaging API (SDK v3)**。預設使用 Gemini 一般文字 API，不啟用可能產生費用的網路搜尋 grounding。

---

## 📁 專案檔案結構

```
1005/
├── app.py              # Flask Web 應用主程式，負責接收與驗證 LINE Webhook 事件
├── gemini_service.py   # Gemini AI 服務封裝（支援 System Prompt、多輪對話記憶）
├── test_local.py       # 本地免部署測試腳本（CLI 對話測試 & Webhook 模擬）
├── requirements.txt    # 專案依賴套件清單
├── .env.example        # 環境變數範本檔
├── .env                # 實際環境變數設定檔（放置金鑰）
├── .gitignore          # Git 忽略清單（避免金鑰上傳）
└── README.md           # 完整使用與部署教學
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

## 💡 內建指令

| 指令 | 說明 |
| :--- | :--- |
| 直接輸入文字 | 與 Gemini AI 進行多輪對話與諮詢 |
| `/help` 或 `說明` | 顯示功能介紹與可用指令說明 |
| `/clear` 或 `清除` | 清空當前與 AI 的對話歷史記憶，重新開啟新話題 |
| `/ping` | 測試機器人伺服器連線與心跳反應 |

---

## ☁️ 雲端 24 小時上線部署建議（Render 免費方案）

若希望關閉電腦後機器人依然能 24 小時自動回覆，可免費部署至 [Render](https://render.com/)：

1. 將專案上傳至您的 **GitHub**（記得確認 `.env` 沒有被推上去）。
2. 在 Render 選擇 **New Web Service**，連接您的 GitHub Repository。
3. 填入設定：
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python app.py`
4. 在 **Environment Variables** 分頁新增：
   - `LINE_CHANNEL_SECRET`
   - `LINE_CHANNEL_ACCESS_TOKEN`
   - `GEMINI_API_KEY`
   - `GEMINI_WEB_SEARCH`（選填，預設 `false`；開啟可能產生 API 費用）
   - `PORT`: `5000`
5. 部署完成後，取得 Render 給予的網址（如 `https://my-line-bot.onrender.com`），將 LINE Developers 後台的 Webhook URL 修改為 `https://my-line-bot.onrender.com/callback` 即可！

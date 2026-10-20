/**
 * LINE + Gemini bot for Google Apps Script.
 * Configure credentials in Project Settings > Script properties. Never put keys here.
 */
const CONFIG = {
  geminiModel: 'gemini-3.8-flash',
  historyTurns: 8,
  maxReplyChars: 4500,
  teacherProfileUrl: 'https://sys.ndhu.edu.tw/RD/TeacherTreasury/tlist.aspx?nav=0&tcher=10787',
  teacherFallbackUrl: 'https://genedu.ndhu.edu.tw/p/412-1076-18517.php?Lang=zh-tw',
  teacherFallback: '陳文盛為國立東華大學通識教育中心教學型助理教授。公開介紹列有資訊工程學系學歷、程式設計相關課程，以及 RFID 資料管理等研究與著作。'
};

const SYSTEM_INSTRUCTION = '你是一位親切、樂於助人的繁體中文 AI 智慧助理。請一律使用台灣繁體中文（zh-TW）回答，內容清晰、精準、適合 LINE 閱讀。遇到最新或需要查證的資訊，若沒有可靠來源，請明確說明無法確認，不要捏造姓名、職稱或資料。';

function doGet() {
  // ContentService responses redirect to script.googleusercontent.com. LINE's
  // webhook verifier expects a direct HTTP 200, so use HtmlService output.
  return htmlOutput_('LINE AI Bot is running. Webhook endpoint: POST /exec');
}

function doPost(e) {
  try {
    const props = PropertiesService.getScriptProperties();
    const configuredGuard = (props.getProperty('WEBHOOK_ACCESS_KEY') || '').trim();
    // Apps Script web app events do not expose request headers, so LINE's
    // X-Line-Signature cannot be verified here. An optional URL key is a
    // lightweight guard, not a replacement for LINE signature verification.
    if (!configuredGuard || !e || !e.parameter || e.parameter.k !== configuredGuard) {
      return textOutput_('Forbidden');
    }

    const body = e && e.postData ? e.postData.contents : '';
    const payload = body ? JSON.parse(body) : {};
    (payload.events || []).forEach(function (event) {
      try {
        handleEvent_(event);
      } catch (eventError) {
        console.error('Event processing failed: ' + eventError);
      }
    });
  } catch (error) {
    console.error('Webhook processing failed: ' + error);
  }
  // Processing is synchronous: the request waits for Gemini and LINE's reply API.
  // Slow Gemini responses may exceed LINE's webhook response window.
  return textOutput_('OK');
}

function handleEvent_(event) {
  if (!event || event.type !== 'message' || !event.message || event.message.type !== 'text') return;
  const text = String(event.message.text || '').trim();
  // Keep a minimal, sourceable execution trace for the NDHU teacher lookup
  // assignment demo. Do not log LINE user IDs or unrelated chat messages.
  if (text.indexOf('陳文盛') !== -1 || text.indexOf('文盛') !== -1) {
    console.log('收到東華教師查詢：' + text);
  }
  const userId = event.source && event.source.userId ? event.source.userId : 'default';
  let reply;

  if (/^(\/help|help|說明|幫助|功能)$/i.test(text)) {
    reply = '🤖【AI 智慧助理功能】\n直接傳送問題即可使用 Gemini AI。\n\n• /help 或「說明」：查看功能\n• /clear 或「清除」：清除對話記憶\n• /ping：測試連線';
  } else if (/^(\/clear|clear|清除|重設)$/i.test(text)) {
    CacheService.getScriptCache().remove(historyKey_(userId));
    reply = '🧹 已清除歷史記憶！我們可以聊聊新的話題囉 😊';
  } else if (/^(\/ping|ping)$/i.test(text)) {
    reply = '🏓 Pong! LINE AI 機器人連線與服務運作正常！';
  } else if (/^(早安|早安呀|早安您好|早)$/i.test(text)) {
    reply = '早安！祝你今天順利 😊';
  } else {
    reply = generateGeminiReply_(userId, text);
  }
  sendLineReply_(event.replyToken, reply);
}

function generateGeminiReply_(userId, prompt) {
  const props = PropertiesService.getScriptProperties();
  const apiKey = (props.getProperty('GEMINI_API_KEY') || '').trim();
  if (!apiKey) return '⚠️ 尚未設定 Gemini API 金鑰，請管理員在 Apps Script 的指令碼屬性中設定。';

  let userPrompt = prompt;
  const teacherContext = getTeacherContext_(prompt);
  if (teacherContext) {
    userPrompt += '\n\n以下為東華大學公開教師頁面資料。回答教師身分、職稱、學經歷或課程時優先依據資料，未提到的部分請說明資料不足，不要推測。\n來源：' + teacherContext.url + '\n資料：' + teacherContext.text;
  }

  const cache = CacheService.getScriptCache();
  const key = historyKey_(userId);
  let history = [];
  try { history = JSON.parse(cache.get(key) || '[]'); } catch (_) { history = []; }
  const contents = history.concat([{ role: 'user', parts: [{ text: userPrompt }] }]);
  const model = (props.getProperty('GEMINI_MODEL') || CONFIG.geminiModel).trim();
  const url = 'https://generativelanguage.googleapis.com/v1beta/models/' + encodeURIComponent(model) + ':generateContent';
  const payload = {
    systemInstruction: { parts: [{ text: SYSTEM_INSTRUCTION }] },
    contents: contents,
    generationConfig: { temperature: 0.7, maxOutputTokens: 900 }
  };

  try {
    const response = UrlFetchApp.fetch(url, {
      method: 'post', contentType: 'application/json',
      headers: { 'x-goog-api-key': apiKey },
      payload: JSON.stringify(payload), muteHttpExceptions: true
    });
    const status = response.getResponseCode();
    const result = JSON.parse(response.getContentText() || '{}');
    if (status < 200 || status >= 300) {
      console.error('Gemini returned HTTP ' + status + ': ' + response.getContentText().slice(0, 800));
      return '抱歉，AI 服務目前無法使用，請稍後再試。';
    }
    let answer = (((result.candidates || [])[0] || {}).content || {}).parts || [];
    answer = answer.map(function (part) { return part.text || ''; }).join('').trim();
    if (!answer) answer = '（AI 目前沒有產生文字，請換個方式再問一次。）';
    if (teacherContext && answer.indexOf(teacherContext.url) === -1) answer += '\n\n東華官方資料：' + teacherContext.url;
    if (answer.length > CONFIG.maxReplyChars) answer = answer.slice(0, CONFIG.maxReplyChars) + '\n\n…（內容過長，已截斷）';

    const newHistory = contents.concat([{ role: 'model', parts: [{ text: answer }] }]);
    cache.put(key, JSON.stringify(newHistory.slice(-CONFIG.historyTurns * 2)), 21600);
    return answer;
  } catch (error) {
    console.error('Gemini request failed: ' + error);
    return '抱歉，目前 AI 服務忙線中，請稍後片刻再試一次！';
  }
}

function sendLineReply_(replyToken, text) {
  const token = (PropertiesService.getScriptProperties().getProperty('LINE_CHANNEL_ACCESS_TOKEN') || '').trim();
  if (!token || !replyToken) {
    console.error('Missing LINE_CHANNEL_ACCESS_TOKEN or replyToken.');
    return;
  }
  const response = UrlFetchApp.fetch('https://api.line.me/v2/bot/message/reply', {
    method: 'post', contentType: 'application/json',
    headers: { Authorization: 'Bearer ' + token },
    payload: JSON.stringify({ replyToken: replyToken, messages: [{ type: 'text', text: String(text).slice(0, 5000) }] }),
    muteHttpExceptions: true
  });
  if (response.getResponseCode() < 200 || response.getResponseCode() >= 300) {
    console.error('LINE reply failed: HTTP ' + response.getResponseCode() + ' ' + response.getContentText().slice(0, 800));
  }
}

function getTeacherContext_(question) {
  if (question.indexOf('陳文盛') === -1 && question.indexOf('文盛') === -1) return null;
  const cache = CacheService.getScriptCache();
  const cached = cache.get('ndhu_teacher_chen_wensheng');
  if (cached) { try { return JSON.parse(cached); } catch (_) {} }

  const candidates = [CONFIG.teacherProfileUrl, CONFIG.teacherFallbackUrl];
  for (let i = 0; i < candidates.length; i++) {
    try {
      const response = UrlFetchApp.fetch(candidates[i], { muteHttpExceptions: true, followRedirects: true });
      if (response.getResponseCode() < 200 || response.getResponseCode() >= 300) continue;
      const html = response.getContentText();
      const visible = html.replace(/<script[\s\S]*?<\/script>|<style[\s\S]*?<\/style>/gi, ' ')
        .replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&')
        .replace(/&#(\d+);/g, function (_, n) { return String.fromCharCode(Number(n)); })
        .replace(/\s+/g, ' ').trim().slice(0, 5000);
      if (visible.indexOf('陳文盛') !== -1) {
        const found = { url: candidates[i], text: visible };
        cache.put('ndhu_teacher_chen_wensheng', JSON.stringify(found), 21600);
        return found;
      }
    } catch (error) { console.warn('NDHU public profile fetch failed: ' + error); }
  }
  const fallback = { url: CONFIG.teacherFallbackUrl, text: CONFIG.teacherFallback };
  cache.put('ndhu_teacher_chen_wensheng', JSON.stringify(fallback), 21600);
  return fallback;
}

function historyKey_(userId) {
  // Keep cache keys short and avoid exposing raw LINE user IDs in cache names.
  const digest = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, String(userId));
  return 'chat_' + Utilities.base64EncodeWebSafe(digest).slice(0, 32);
}

function textOutput_(text) {
  // ContentService always redirects its response; use HtmlOutput for LINE's
  // required direct 200 response.
  return htmlOutput_(text);
}

function htmlOutput_(text) {
  return HtmlService.createHtmlOutput(String(text));
}

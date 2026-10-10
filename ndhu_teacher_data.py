"""Small, source-backed lookup for publicly available NDHU teacher profiles.

This deliberately reads only public NDHU pages. It does not access campus SSO
or any student, grade, or other restricted system.
"""

from html.parser import HTMLParser
from time import monotonic
from urllib.request import Request, urlopen


_PROFILES = {
    "陳文盛": {
        "title": "陳文盛老師（東華教師人才資料庫）",
        "url": "https://sys.ndhu.edu.tw/RD/TeacherTreasury/tlist.aspx?nav=0&tcher=10787",
        "fallback_url": "https://genedu.ndhu.edu.tw/p/412-1076-18517.php?Lang=zh-tw",
        "fallback": (
            "陳文盛為國立東華大學通識教育中心教學型助理教授。公開介紹列有"
            "資訊工程學系學歷、程式設計相關課程，以及 RFID 資料管理等研究與著作。"
        ),
    },
}

_CACHE = {}
_CACHE_TTL_SECONDS = 6 * 60 * 60


class _VisibleText(HTMLParser):
    """Extract readable text while ignoring scripts and page chrome."""

    _SKIP = {"script", "style", "noscript", "svg"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skip_depth += 1
        elif not self._skip_depth and tag in {"br", "p", "div", "li", "tr", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._skip_depth:
            self._skip_depth -= 1
        elif not self._skip_depth and tag in {"p", "div", "li", "tr", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip_depth and data.strip():
            self.parts.append(data.strip())


def _fetch_profile(url):
    request = Request(
        url,
        headers={"User-Agent": "NDHU-Class-Project-LineBot/1.0"},
    )
    with urlopen(request, timeout=4) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        html = response.read(1_000_000).decode(charset, errors="replace")
    parser = _VisibleText()
    parser.feed(html)
    return " ".join(" ".join(parser.parts).split())[:5000]


def get_public_teacher_context(question):
    """Return verified public profile context for a matched teacher, if any."""
    if "陳文盛" not in question and "文盛" not in question:
        return None

    profile = _PROFILES["陳文盛"]
    cached = _CACHE.get("陳文盛")
    if cached and monotonic() - cached[0] < _CACHE_TTL_SECONDS:
        text, url = cached[1], cached[2]
    else:
        text = ""
        url = profile["url"]
        for candidate_url in (profile["url"], profile["fallback_url"]):
            try:
                candidate_text = _fetch_profile(candidate_url)
                if "陳文盛" in candidate_text:
                    text, url = candidate_text, candidate_url
                    break
            except Exception:
                continue
        if not text:
            text, url = profile["fallback"], profile["fallback_url"]
        _CACHE["陳文盛"] = (monotonic(), text, url)

    return {
        "title": profile["title"],
        "url": url,
        "text": text,
    }

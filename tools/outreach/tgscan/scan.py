# Поиск контактов владельцев/управляющих в публичных Telegram-каналах ресторанов
import re, sys, json, html, urllib.request

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")

def text(s):
    s = re.sub(r"<br\s*/?>", "\n", s)
    return html.unescape(re.sub(r"<[^>]+>", " ", s))

KEY = re.compile(r"управля|владел|основател|сотруднич|партн|реклам|по вопрос|менеджер|директор|шеф|брон|админ|связ|пишите|hr|вакан", re.I)
PH = re.compile(r"(?:\+7|8)[\s(-]*\d{3}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}")

def scan(ch, pages=5):
    res = {"channel": ch, "title": "", "desc": "", "mentions": {}, "phones": {}, "lines": []}
    url = "https://t.me/s/" + ch
    seen = set()
    for _ in range(pages):
        try:
            h = get(url)
        except Exception as e:
            res["error"] = str(e); break
        if not res["title"]:
            m = re.search(r'<div class="tgme_channel_info_header_title"[^>]*>(.*?)</div>', h, re.S)
            res["title"] = text(m.group(1)).strip() if m else ""
            m = re.search(r'<div class="tgme_channel_info_description"[^>]*>(.*?)</div>', h, re.S)
            res["desc"] = text(m.group(1)).strip() if m else ""
        posts = re.findall(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', h, re.S)
        for p in posts:
            t = text(p)
            for u in re.findall(r"@([A-Za-z0-9_]{4,})", t + " " + p):
                res["mentions"][u] = res["mentions"].get(u, 0) + 1
            for u in re.findall(r"t\.me/([A-Za-z0-9_+]{4,})", p):
                res["mentions"][u] = res["mentions"].get(u, 0) + 1
            for ph in PH.findall(t):
                d = re.sub(r"\D", "", ph); d = "7" + d[1:] if d[0] == "8" else d
                res["phones"][d] = res["phones"].get(d, 0) + 1
            for line in t.split("\n"):
                line = line.strip()
                if KEY.search(line) and (PH.search(line) or "@" in line) and line not in seen:
                    seen.add(line); res["lines"].append(line[:200])
        m = re.search(r'<link rel="prev" href="([^"]+)"', h)
        if not m: break
        url = "https://t.me" + m.group(1)
    for u in re.findall(r"@([A-Za-z0-9_]{4,})", res["desc"]):
        res["mentions"][u] = res["mentions"].get(u, 0) + 5
    return res

if __name__ == "__main__":
    out = [scan(c) for c in sys.argv[1:]]
    print(json.dumps(out, ensure_ascii=False, indent=1))

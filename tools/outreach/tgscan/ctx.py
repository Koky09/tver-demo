import re, sys, html, urllib.request
def get(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(r, timeout=20).read().decode("utf-8", "ignore")
ch, words = sys.argv[1], sys.argv[2:]
url = "https://t.me/s/" + ch
for _ in range(8):
    h = get(url)
    for p in re.findall(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', h, re.S):
        t = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<br\s*/?>", " | ", p)))
        t = re.sub(r"\s+", " ", t)
        for w in words:
            i = t.find(w)
            if i >= 0:
                print(f"[{ch}] ...{t[max(0,i-220):i+120]}...")
    m = re.search(r'<link rel="prev" href="([^"]+)"', h)
    if not m: break
    url = "https://t.me" + m.group(1)

# Что за ссылкой t.me/<имя или +номер>: личный аккаунт, канал, группа или бот
import re, sys, html, urllib.request
def get(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(r, timeout=20).read().decode("utf-8", "ignore")
def who(x):
    try:
        h = get("https://t.me/" + x)
    except Exception as e:
        return "ошибка " + str(e)
    t = re.search(r'<div class="tgme_page_title"[^>]*>(.*?)</div>', h, re.S)
    title = html.unescape(re.sub(r"<[^>]+>", "", t.group(1))).strip() if t else ""
    extra = re.search(r'<div class="tgme_page_extra"[^>]*>(.*?)</div>', h, re.S)
    extra = html.unescape(re.sub(r"<[^>]+>", "", extra.group(1))).strip() if extra else ""
    desc = re.search(r'<div class="tgme_page_description[^"]*"[^>]*>(.*?)</div>', h, re.S)
    desc = html.unescape(re.sub(r"<br\s*/?>", " ", re.sub(r"<(?!br)[^>]+>", "", desc.group(1)))).strip() if desc else ""
    btn = re.search(r'class="tgme_action_button_new[^"]*"[^>]*>(.*?)</a>', h, re.S)
    btn = re.sub(r"<[^>]+>", "", btn.group(1)).strip() if btn else ""
    if not title:
        return "нет такого / номер не в Telegram"
    kind = ("бот" if "Start Bot" in btn else "канал" if "subscriber" in extra else
            "группа" if "member" in extra else "ЛИЧНЫЙ" if "Send Message" in btn or "@" in extra else btn)
    return f"{kind} | {title} | {extra} | {desc[:160]}"
for x in sys.argv[1:]:
    print(f"{x:24} -> {who(x)}")

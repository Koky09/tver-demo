# Глубокий поиск личных Telegram владельцев/управляющих для всех ресторанов из CLIENTS.md
#   python tgscan/deep.py            -> tgscan/deep.json (+ краткий вывод)
# 1) ссылки t.me из 2ГИС и из уже известных каналов (TG в mkrest.py)
# 2) каждый канал читается до PAGES страниц, собираются @упоминания с текстом вокруг
# 3) каждое упоминание проверяется: личный аккаунт / канал / группа / бот
import json, re, sys, html, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
ROOT = Path(r"D:\AI\sites-restaurants")
PAGES = 30
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept-Language": "ru"}
ROLE = re.compile(r"владел|основател|совладел|управля|директор|менеджер|шеф|бренд|сотруднич|партн|реклам|по вопрос|связ|пишите|админ|арт-дир|hr|вакан|организ|собственн|founder|owner|manager", re.I)
SKIP = {"boost", "share", "joinchat", "addstickers", "proxy", "socks", "iv", "s", "c", "setlanguage", "addemoji"}


def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25).read().decode("utf-8", "ignore")


def plain(s):
    s = re.sub(r"<br\s*/?>", " | ", s)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


_who = {}
def who(x):
    if x in _who:
        return _who[x]
    import time
    h = ""
    for wait in (1, 4, 10, 25):
        time.sleep(wait)
        try:
            h = get("https://t.me/" + x)
        except Exception as e:
            _who[x] = ("ошибка", "", "", str(e)); return _who[x]
        if "tgme_page_title" in h or x.startswith("+") or x.isdigit():
            break
    g = lambda pat: (lambda m: plain(m.group(1)) if m else "")(re.search(pat, h, re.S))
    title = g(r'<div class="tgme_page_title"[^>]*>(.*?)</div>')
    extra = g(r'<div class="tgme_page_extra"[^>]*>(.*?)</div>')
    desc = g(r'<div class="tgme_page_description[^"]*"[^>]*>(.*?)</div>')
    btn = g(r'class="tgme_action_button_new[^"]*"[^>]*>(.*?)</a>')
    if not title:
        kind = "нет"
    elif "Start Bot" in btn:
        kind = "бот"
    elif "subscriber" in extra:
        kind = "канал"
    elif "member" in extra:
        kind = "группа"
    elif "Send Message" in btn or extra.startswith("@"):
        kind = "личный"
    else:
        kind = btn or "?"
    _who[x] = (kind, title, extra, desc[:300])
    return _who[x]


def channel(ch):
    """Описание и посты канала: упоминания @имя с текстом вокруг"""
    res = {"desc": "", "ment": {}}
    url = "https://t.me/s/" + ch
    for _ in range(PAGES):
        try:
            h = get(url)
        except Exception:
            break
        if not res["desc"]:
            m = re.search(r'<div class="tgme_channel_info_description"[^>]*>(.*?)</div>', h, re.S)
            res["desc"] = plain(m.group(1)) if m else ""
            for u in re.findall(r"@([A-Za-z0-9_]{4,32})", res["desc"]) + re.findall(r"t\.me/([A-Za-z0-9_]{4,32})", m.group(1) if m else ""):
                res["ment"].setdefault(u, []).insert(0, "ОПИСАНИЕ: " + res["desc"][:250])
        for p in re.findall(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', h, re.S):
            t = plain(p)
            names = set(re.findall(r"@([A-Za-z0-9_]{4,32})", t)) | set(re.findall(r"t\.me/([A-Za-z0-9_]{4,32})", p))
            for u in names:
                i = max(t.find("@" + u), t.find(u))
                ctx = t[max(0, i - 160): i + 80]
                lst = res["ment"].setdefault(u, [])
                if len(lst) < 4 and ctx not in lst:
                    lst.append(ctx)
        m = re.search(r'<link rel="prev" href="([^"]+)"', h)
        if not m:
            break
        url = "https://t.me" + m.group(1)
    return res


def gis(name, addr):
    try:
        h = get("https://2gis.ru/moscow/search/" + urllib.parse.quote(name + " " + addr))
    except Exception:
        return set()
    h = h.replace("\\/", "/")
    out = set()
    for u in re.findall(r"t\.me/([A-Za-z0-9_+]{4,40})", h):
        out.add(u)
    return out


def yandex(url):
    """ссылки t.me и vk из блока соцсетей карточки Яндекс Карт (не со всей страницы)"""
    try:
        h = get(url)
    except Exception:
        return set(), set()
    seg = "".join(h[m.start():m.start() + 3000] for m in re.finditer("business-contacts-view__social", h))
    tg = {u for u in re.findall(r"t\.me/([A-Za-z0-9_+]{4,40})", seg) if u.lower() != "mapsyandex"}
    vk = set(re.findall(r"vk\.com/([A-Za-z0-9_.]{3,40})", seg))
    return tg, vk


def known():
    t = (HERE.parent / "mkrest.py").read_text(encoding="utf-8")
    d = {}
    for key, body in re.findall(r'^\s+"([a-z0-9_]+)": \((.*)\),$', t, re.M):
        d[key] = set(re.findall(r"@([A-Za-z0-9_]{4,})", body))
        first = re.match(r'"([^"]*)"', body)
        if first and first.group(1) and not first.group(1).startswith("+"):
            d[key].add(first.group(1))
    return d


def rows():
    out = []
    for line in (ROOT / "sites" / "CLIENTS.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\| ([a-z0-9_]+) \| ([^|]+) \| [^|]+ \| ([^|]+) \| [^|]+ \| ([^|]+) \|", line)
        if m and m[1] != "Папка":
            out.append((m[1], m[2].strip(), m[3].strip(), m[4].strip()))
    return out


def one(r):
    key, name, addr, ya = r
    ytg, yvk = yandex(ya)
    handles = set(K.get(key, set())) | gis(name, addr) | ytg
    handles = {h for h in handles if h.lower() not in SKIP and not h.startswith("+")}
    found = {"key": key, "name": name, "links": {}, "people": {}, "vk": sorted(yvk)}
    for hnd in sorted(handles):
        kind, title, extra, desc = who(hnd)
        found["links"][hnd] = [kind, title, extra, desc]
        if kind in ("канал", "группа"):
            c = channel(hnd)
            for u, ctx in c["ment"].items():
                if u.lower() in SKIP or u.lower() in {x.lower() for x in handles}:
                    continue
                found["people"].setdefault(u, {"from": hnd, "ctx": ctx})
        elif kind == "личный" and desc:
            for u in re.findall(r"@([A-Za-z0-9_]{4,32})", desc):
                found["people"].setdefault(u, {"from": hnd, "ctx": ["описание: " + desc]})
    for u in list(found["people"]):
        k = who(u)
        found["people"][u]["who"] = list(k)
    print(key, len(found["links"]), "ссылок,", sum(1 for p in found["people"].values() if p["who"][0] == "личный"), "личных", flush=True)
    return found


if __name__ == "__main__":
    K = known()
    R = rows()
    if len(sys.argv) > 1:
        R = [r for r in R if r[0] in sys.argv[1:]]
    with ThreadPoolExecutor(int(__import__('os').environ.get('TH','3'))) as ex:
        res = list(ex.map(one, R))
    out = HERE / __import__('os').environ.get('OUT', 'deep.json')
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("готово:", len(res))

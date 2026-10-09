"""Telegram для партии: проверяет кандидатов (_tg_cand) — личный аккаунт / канал / бот; заполняет tg и tgn. Чистит хвосты «ст3» в названиях.
    python tools/newclient/tg_batch.py batches/<партия>.json"""
import html, json, re, sys, time, urllib.request
def who(x):
    h = ""
    for w in (1, 4, 10):
        time.sleep(w)
        h = urllib.request.urlopen(urllib.request.Request("https://t.me/" + x, headers={"User-Agent": "Mozilla/5.0"}), timeout=20).read().decode("utf-8", "ignore")
        if "tgme_page_title" in h:
            break
    g = lambda pat: (lambda m: html.unescape(re.sub(r"<[^>]+>", " ", m.group(1))).strip() if m else "")(re.search(pat, h, re.S))
    title, extra = g(r'<div class="tgme_page_title"[^>]*>(.*?)</div>'), g(r'<div class="tgme_page_extra"[^>]*>(.*?)</div>')
    btn = g(r'class="tgme_action_button_new[^"]*"[^>]*>(.*?)</a>')
    if not title:
        return "нет", ""
    return ("бот" if "Start Bot" in btn else "канал" if "subscriber" in extra else "группа" if "member" in extra else "личный"), title
p = sys.argv[1]
B = json.load(open(p, encoding="utf-8"))
for b in B:
    b["name"] = re.sub(r"\s+(ст|к|корп|стр)\.?\s?\d+\w*$", "", b["name"])
    if b.get("tg") or b.get("tgn"):
        continue
    tg, tgn = "", ""
    nums = [c for c in b["_tg_cand"] if c.startswith("+")]
    for u in [c for c in b["_tg_cand"] if not c.startswith("+")]:
        k, t = who(u)
        if k == "личный":
            tg, tgn = u, f"аккаунт @{u} ({t})"; break
        if k in ("канал", "группа"):
            tgn = f"только {k} @{u}"
        elif k == "бот" and not tgn:
            tgn = f"бот @{u}"
    if not tg and nums:
        tg = nums[0]; tgn = (tgn + "; " if tgn else "") + f"номер {nums[0]} указан как Telegram"
    b["tg"], b["tgn"] = tg, tgn or "Telegram не нашёлся"
    print(b["slug"], b["tg"], b["tgn"])
json.dump(B, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

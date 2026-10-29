"""Вторая перепроверка через настоящий браузер (Playwright): Taplink, ВК, мини-сайты 2ГИС не отдают страницу простому запросу.
    python tools/newclient/booking_links_br.py   (берёт ссылки из salons2-links.json, дописывает туда br_hit)"""
import json, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from find_nails_city import BOOKING
WORDS = re.compile(r"онлайн[- ]?запис|записаться онлайн|запись онлайн|Записаться|online booking", re.I)

f = HERE / "salons2-links.json"
res = json.loads(f.read_text(encoding="utf-8"))
with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(locale="ru-RU")
    for slug, v in res.items():
        hits = []
        for u in v["ok"] + [h.split(": ")[0] for h in v["hit"]]:
            u = u.replace(" (не открылась)", "")
            if not re.search(r"taplink|vk\.com|2gis\.biz|obiz\.ru|hipolink|mssg|linktr", u):
                continue
            try:
                pg.goto(u, timeout=30000, wait_until="domcontentloaded")
                pg.wait_for_timeout(2500)
                # в коде любой группы ВК есть служебные поля is_yclients_tooltip_active, yclients_repeat_records — это не запись
                html = re.sub(r"\w*yclients_\w+|\w+_yclients\w*", "", pg.content())
                text = pg.inner_text("body")
            except Exception as e:
                hits.append(f"{u}: не открылась"); continue
            m = BOOKING.search(html)
            # слово «Записаться» считаем, только если это короткая строка — кнопка, а не текст поста
            w = next((l for l in text.splitlines() if WORDS.search(l) and len(l.strip()) <= 30), None)
            if m:
                hits.append(f"{u}: {m.group(0)}")
            elif w:
                hits.append(f"{u}: кнопка «{w.strip()}»")
        v["br_hit"] = hits
        if hits:
            print(f"{slug:34} {v['name'][:22]:22} " + "; ".join(hits), flush=True)
    br.close()
f.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print("готово")

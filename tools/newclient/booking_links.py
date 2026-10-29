"""Перепроверка партии: нет ли онлайн-записи внутри ссылок из карточки (Taplink, ВК, Instagram и т.п. — они не считаются сайтом).
    python tools/newclient/booking_links.py batches/<партия>.json <found.json>   -> печатает, у кого нашлась запись
Урок 29.10.2026: Fabrika9 (Владивосток) — запись была внутри taplink, первое сообщение «только по телефону» оказалось неправдой."""
import json, re, sys, time, urllib.request
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from find_nails_city import BOOKING

WORDS = re.compile(r"онлайн[- ]?запис|записаться онлайн|запись онлайн|online booking", re.I)


def get(u):
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36", "Accept-Language": "ru"})
    return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")


batch = json.loads((ROOT / sys.argv[1]).read_text(encoding="utf-8"))
found = {x["id"]: x for x in json.loads((HERE / sys.argv[2]).read_text(encoding="utf-8"))}
res = {}
for b in batch:
    x = found.get(b["_gis"], {})
    links = [w for k, vs in x.get("contacts", {}).items() if k not in ("phone", "whatsapp", "telegram", "email") for w in vs]
    links += x.get("ya_sites") or []
    hit, seen = [], []
    for u in dict.fromkeys(links):
        try:
            h = get(u if u.startswith("http") else "https://" + u)
        except Exception as e:
            seen.append(f"{u} (не открылась)"); continue
        h = h.replace("\/", "/")
        m = BOOKING.search(h)
        if m:
            hit.append(f"{u}: {m.group(0)}")
        elif WORDS.search(h):
            hit.append(f"{u}: слова «онлайн-запись»")
        else:
            seen.append(u)
        time.sleep(0.5)
    res[b["slug"]] = {"name": b["name"], "hit": hit, "ok": seen}
    print(("ЗАПИСЬ " if hit else "чисто  ") + f'{b["slug"]:34} {b["name"][:24]:24} ' + "; ".join(hit or seen), flush=True)
(HERE / "salons2-links.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print("с записью:", sum(1 for v in res.values() if v["hit"]), "без ссылок:", sum(1 for v in res.values() if not v["hit"] and not v["ok"]))

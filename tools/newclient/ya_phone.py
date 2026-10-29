"""Карточка Яндекса по номеру телефона для тех, кого не нашли по названию (ya_none): ищем номер на Яндекс Картах,
берём организацию, на странице которой есть этот номер. Своя запись в карточке -> ya_booking.
    python tools/newclient/ya_phone.py salons2-found.json"""
import json, re, sys, time, urllib.parse
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from mk_tire_batch import get
from find_nails_city import BOOKING

f = HERE / sys.argv[1]
data = json.loads(f.read_text(encoding="utf-8"))
for x in data:
    if not x.get("ya_none"):
        continue
    res = None
    for p in x["contacts"].get("phone", [])[:2]:
        d = re.sub(r"\D", "", p)[-10:]
        h = get("https://yandex.ru/maps/?text=" + urllib.parse.quote(f"+7{d}"))
        if "showcaptcha" in h:
            print("капча, стоп"); res = "stop"; break
        for slug, oid in list(dict.fromkeys(re.findall(r"/maps/org/([a-z0-9_]+)/(\d+)", h)))[:3]:
            o = get(f"https://yandex.ru/maps/org/{slug}/{oid}/")
            if d[-7:] in re.sub(r"\D", "", o):
                res = "booking" if ("Записаться онлайн" in o or "Забронировать" in o or BOOKING.search(o)) else f"https://yandex.ru/maps/org/{slug}/{oid}/"
                break
            time.sleep(0.4)
        if res:
            break
        time.sleep(0.6)
    if res == "stop":
        break
    if res == "booking":
        x["ya_booking"] = True
    elif res:
        x["ya_url"], x["ya_phone"] = res, True
        x.pop("ya_none", None)
    print(f'{x["city"][:10]:10} {x["name"][:34]:34} -> {res}', flush=True)
f.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

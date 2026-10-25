"""Карточка Яндекса для фирм, у которых телефон в 2ГИС и на Яндексе не совпал: ищем по названию и адресу,
берём организацию с тем же номером дома и словом из названия. Без своей записи в карточке.
    python tools/newclient/ya_loose.py sauna-found.json      (дописывает ya_url и ya_loose: true)"""
import json, re, sys, time, urllib.parse
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from mk_tire_batch import get
from find_nails_city import BOOKING

f = HERE / sys.argv[1]
data = json.loads(f.read_text(encoding="utf-8"))
for x in data:
    if x.get("ya_url") or x.get("ya_none"):
        continue
    brand = re.split(r",", x["name"])[0].strip()
    house = re.findall(r"\d+[а-яa-z]?", x["address"])
    h = get("https://yandex.ru/maps/?text=" + urllib.parse.quote(f'{brand} {x["address"]} {x["city"]}'))
    if "showcaptcha" in h:
        print("капча, стоп"); break
    ok = None
    for slug, oid in list(dict.fromkeys(re.findall(r"/maps/org/([a-z0-9_]+)/(\d+)", h)))[:3]:
        o = get(f"https://yandex.ru/maps/org/{slug}/{oid}/")
        t = re.search(r"<title>([^<]*)", o)
        title = t.group(1) if t else ""
        word = next((w for w in re.findall(r"[А-Яа-яЁёA-Za-z]{4,}", brand)), brand).lower()[:5]
        if word in title.lower() and house and house[-1] in title:
            if "Записаться онлайн" in o or "Забронировать" in o or BOOKING.search(o):
                ok = "booking"
            else:
                ok = f"https://yandex.ru/maps/org/{slug}/{oid}/"
            break
        time.sleep(0.4)
    if ok == "booking":
        x["ya_booking"] = True
    elif ok:
        x["ya_url"], x["ya_loose"] = ok, True
    else:
        x["ya_none"] = True
    print(f'{x["city"][:10]:10} {brand[:30]:30} -> {ok}', flush=True)
    time.sleep(0.6)
f.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

"""Поиск студий маникюра в городах-миллионниках (кроме Москвы), сразу без онлайн-записи на Яндекс Картах.
    python tools/newclient/find_nails_city.py [город ...]      -> tools/newclient/nailc-found.json
(сделан из find_salons.py; онлайн-запись в карточке Яндекса = кнопка «Записаться онлайн» / ссылки YCLIENTS, DIKIDI ...)
Берём: салон красоты / парикмахерская, одна точка (не сеть), без своего сайта и без своей онлайн-записи
(YClients, DIKIDI, Sonline и т.п. считаем сайтом), рейтинг от 4,6, отзывов от MIN (max из 2ГИС и Яндекса),
последний отзыв не старше полугода. Барбершопы не берём."""
import json, re, sys, time, datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from gis import search, firm, reviews
from find_tires import SITE_OK, done_phones
import find_tires2

MIN = 50
CITIES = {"spb": "Санкт-Петербург", "novosibirsk": "Новосибирск", "ekaterinburg": "Екатеринбург", "kazan": "Казань",
          "n_novgorod": "Нижний Новгород", "krasnoyarsk": "Красноярск", "chelyabinsk": "Челябинск", "samara": "Самара",
          "ufa": "Уфа", "rostov": "Ростов-на-Дону", "krasnodar": "Краснодар", "omsk": "Омск", "voronezh": "Воронеж",
          "perm": "Пермь", "volgograd": "Волгоград"}
WORDS = ("маникюр", "ногтевая студия", "студия маникюра")
PAGES = 6
RUBRIC = re.compile(r"ногт|маникюр", re.I)
NOT_NAME = re.compile(r"барбер|barber|школа|академи|обучен|магазин|оптов|клиник|медицин|подолог|парикмах|hair", re.I)
BOOKING = re.compile(r"yclients|dikidi|sonline|booksy|easyweek|arnica|beautypro|clients\.site|1c-?beauty|universe-?soft|altegio", re.I)


def ids(city):
    found = {}
    def one(q):
        res = []
        for pg in range(1, PAGES + 1):
            try:
                r = search(city, q, pg)
            except Exception:
                break
            if not r:
                break
            res += r
            time.sleep(0.3)
        return res
    with ThreadPoolExecutor(4) as ex:
        for res in ex.map(one, WORDS):
            for f in res:
                if not NOT_NAME.search(f["name"]):
                    found[f["id"]] = f
    return found


def d10(p):
    return re.sub(r"\D", "", p)[-10:]


def check(args):
    city, f = args
    cname = CITIES[city]
    try:
        rv = reviews(f["id"])
        if (rv["count"] or 0) < 10 or (rv["rating"] or 0) < 4.5:
            return None
        last = datetime.datetime.fromisoformat(rv["last"][:19]) if rv["last"] else None
        if not last or (datetime.datetime.now() - last).days > 183:
            return None
        d = firm(city, f["id"])
    except Exception as e:
        return {"id": f["id"], "city": cname, "error": str(e)}
    if not any(cname in (a or "") for a in d["adm"]) or (d["branches"] or 1) > 1:
        return None
    if not any(RUBRIC.search(r or "") for r in d["rubrics"]) or NOT_NAME.search(d["name"]):
        return None
    web = d["contacts"].get("website", [])
    if [w for w in web if not SITE_OK.search(w)] or [w for w in web if BOOKING.search(w)]:
        return None
    phones = d["contacts"].get("phone", [])
    if not phones or any(d10(p) in DONE for p in phones):
        return None
    time.sleep(0.5)
    try:
        y = find_tires2.yandex(d["name"], d["address"], phones, cname)
    except Exception as e:
        y = {"ya": None, "yerr": str(e)}
    if y.get("ya_sites"):
        return None
    if y.get("ya_url"):   # своя онлайн-запись в карточке Яндекса — им наш сайт с записью не нужен
        from mk_tire_batch import get as yget
        h = yget(y["ya_url"])
        if "Записаться онлайн" in h or BOOKING.search(h):
            return None
    d.update({"city": cname, "city_slug": city, "gis_rating": rv["rating"], "gis_reviews": rv["count"] or 0, "gis_last": rv["last"]})
    d.update(y)
    d["reviews"] = max(d["gis_reviews"], d.get("ya_reviews") or 0)
    d["rating"] = d.get("ya_rating") if (d.get("ya_reviews") or 0) >= d["gis_reviews"] and d.get("ya_rating") else d["gis_rating"]
    print(f'{cname[:12]:12} {d["reviews"]:4} {d["rating"]} {d["name"][:40]:40} {d["address"]}', flush=True)
    return d


if __name__ == "__main__":
    DONE = done_phones()
    cities = sys.argv[1:] or list(CITIES)
    ids_path = HERE / "nailc-ids.json"
    allc = json.loads(ids_path.read_text(encoding="utf-8")) if ids_path.exists() else {}
    for c in cities:
        if c not in allc:
            allc[c] = ids(c)
            ids_path.write_text(json.dumps(allc, ensure_ascii=False), encoding="utf-8")
            print("кандидатов", CITIES[c], len(allc[c]), flush=True)
    jobs = [(c, f) for c in cities for f in allc[c].values()]
    with ThreadPoolExecutor(4) as ex:
        res = [r for r in ex.map(check, jobs) if r]
    (HERE / "nailc-checked.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    good = [r for r in res if "error" not in r and r["reviews"] >= MIN and (r["rating"] or 0) >= 4.6]
    good.sort(key=lambda r: -r["reviews"])
    (HERE / "nailc-found.json").write_text(json.dumps(good, ensure_ascii=False, indent=1), encoding="utf-8")
    by = {}
    for r in good:
        by[r["city"]] = by.get(r["city"], 0) + 1
    print("проверено:", len(res), "подходят:", len(good), by, "ошибок:", sum(1 for r in res if "error" in r),
          "капча:", sum(1 for r in res if r.get("captcha")))

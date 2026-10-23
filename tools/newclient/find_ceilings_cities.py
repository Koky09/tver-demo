"""Поиск фирм натяжных потолков в городах-миллионниках (кроме Москвы).
    python tools/newclient/find_ceilings_cities.py [город ...]      -> tools/newclient/ceilc-found.json
(сделан из find_salons.py: другие запросы, рубрика и пороги — у потолочников мало отзывов в 2ГИС)
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

MIN = 0
CITIES = {"spb": "Санкт-Петербург", "novosibirsk": "Новосибирск", "ekaterinburg": "Екатеринбург", "kazan": "Казань",
          "n_novgorod": "Нижний Новгород", "krasnoyarsk": "Красноярск", "chelyabinsk": "Челябинск", "samara": "Самара",
          "ufa": "Уфа", "rostov": "Ростов-на-Дону", "krasnodar": "Краснодар", "omsk": "Омск", "voronezh": "Воронеж",
          "perm": "Пермь", "volgograd": "Волгоград"}
WORDS = ("натяжные потолки", "натяжные потолки под ключ")
PAGES = 10
RUBRIC = re.compile(r"натяжн", re.I)
NOT_NAME = re.compile(r"оптов|склад|плитк|обои|гипермаркет|леруа|строительный рынок", re.I)
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
        if rv["count"] and (rv["rating"] or 0) < 4.4:
            return None
        last = datetime.datetime.fromisoformat(rv["last"][:19]) if rv["last"] else None
        if last and (datetime.datetime.now() - last).days > 540:
            return None
        d = firm(city, f["id"])
    except Exception as e:
        return {"id": f["id"], "city": cname, "error": str(e)}
    if not any(cname in (a or "") for a in d["adm"]) or (d["branches"] or 1) > 3:
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
    d.update({"city": cname, "city_slug": city, "gis_rating": rv["rating"], "gis_reviews": rv["count"] or 0, "gis_last": rv["last"]})
    d.update(y)
    d["reviews"] = max(d["gis_reviews"], d.get("ya_reviews") or 0)
    d["rating"] = d.get("ya_rating") if (d.get("ya_reviews") or 0) >= d["gis_reviews"] and d.get("ya_rating") else d["gis_rating"]
    print(f'{cname[:12]:12} {d["reviews"]:4} {d["rating"]} {d["name"][:40]:40} {d["address"]}', flush=True)
    return d


if __name__ == "__main__":
    DONE = done_phones()
    cities = sys.argv[1:] or list(CITIES)
    ids_path = HERE / "ceilc-ids.json"
    allc = json.loads(ids_path.read_text(encoding="utf-8")) if ids_path.exists() else {}
    for c in cities:
        if c not in allc:
            allc[c] = ids(c)
            ids_path.write_text(json.dumps(allc, ensure_ascii=False), encoding="utf-8")
            print("кандидатов", CITIES[c], len(allc[c]), flush=True)
    jobs = [(c, f) for c in cities for f in allc[c].values()]
    with ThreadPoolExecutor(4) as ex:
        res = [r for r in ex.map(check, jobs) if r]
    (HERE / "ceilc-checked.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    good = [r for r in res if "error" not in r and r["reviews"] >= MIN and ((r["rating"] or 5) >= 4.5 or not r["reviews"])]
    good.sort(key=lambda r: -r["reviews"])
    (HERE / "ceilc-found.json").write_text(json.dumps(good, ensure_ascii=False, indent=1), encoding="utf-8")
    by = {}
    for r in good:
        by[r["city"]] = by.get(r["city"], 0) + 1
    print("проверено:", len(res), "подходят:", len(good), by, "ошибок:", sum(1 for r in res if "error" in r),
          "капча:", sum(1 for r in res if r.get("captcha")))

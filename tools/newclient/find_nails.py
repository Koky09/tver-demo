"""Поиск маникюрных студий в Москве для новой партии.
    python tools/newclient/find_nails.py        -> tools/newclient/nails-found.json
Берём: ногтевая студия / маникюр, одна точка (не сеть), без своего сайта и без своей онлайн-записи
(YClients, DIKIDI, Sonline и т.п. считаем сайтом — им наш продукт не нужен), рейтинг от 4,6,
отзывов от MIN (max из 2ГИС и Яндекса), последний отзыв не старше полугода."""
import json, re, sys, time, datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from gis import search, firm, reviews
from find_tires import AREAS, SITE_OK, done_phones
import find_tires2

MIN = 50
CITY = "moscow"
QUERIES = [f"{w} {a}" for a in AREAS for w in ("маникюр", "ногтевая студия")]
NAME = re.compile(r"nail|нейл|маник|ногт|ноготк|педик|beauty|бьюти|студия|салон|мастер", re.I)
RUBRIC = re.compile(r"ногт|маникюр", re.I)
BOOKING = re.compile(r"yclients|dikidi|sonline|booksy|easyweek|arnica|beautypro|n\d+\.yclients|clients\.site", re.I)


def ids():
    found = {}
    def one(q):
        res = []
        for pg in range(1, 3):
            try:
                r = search(CITY, q, pg)
            except Exception:
                break
            if not r:
                break
            res += r
            time.sleep(0.3)
        return res
    with ThreadPoolExecutor(4) as ex:
        for res in ex.map(one, QUERIES):
            for f in res:
                if NAME.search(f["name"]):
                    found[f["id"]] = f
    return found


def d10(p):
    return re.sub(r"\D", "", p)[-10:]


def check(f):
    try:
        rv = reviews(f["id"])
        if (rv["count"] or 0) < 5 or (rv["rating"] or 0) < 4.5:
            return None
        last = datetime.datetime.fromisoformat(rv["last"][:19]) if rv["last"] else None
        if not last or (datetime.datetime.now() - last).days > 183:
            return None
        d = firm(CITY, f["id"])
    except Exception as e:
        return {"id": f["id"], "error": str(e)}
    if not any("Москва" in (a or "") for a in d["adm"]) or (d["branches"] or 1) > 1:
        return None
    if not any(RUBRIC.search(r or "") for r in d["rubrics"]):
        return None
    web = d["contacts"].get("website", [])
    if [w for w in web if not SITE_OK.search(w)] or [w for w in web if BOOKING.search(w)]:
        return None
    phones = d["contacts"].get("phone", [])
    if not phones or any(d10(p) in DONE for p in phones):
        return None
    time.sleep(0.5)
    try:
        y = find_tires2.yandex(d["name"], d["address"], phones)
    except Exception as e:
        y = {"ya": None, "yerr": str(e)}
    if y.get("ya_sites"):
        return None
    d.update({"gis_rating": rv["rating"], "gis_reviews": rv["count"] or 0, "gis_last": rv["last"]})
    d.update(y)
    d["reviews"] = max(d["gis_reviews"], d.get("ya_reviews") or 0)
    d["rating"] = d.get("ya_rating") if (d.get("ya_reviews") or 0) >= d["gis_reviews"] and d.get("ya_rating") else d["gis_rating"]
    print(f'{d["reviews"]:4} {d["rating"]} {d["name"][:40]:40} {d["address"]}', flush=True)
    return d


if __name__ == "__main__":
    DONE = done_phones()
    ids_path = HERE / "nails-ids.json"
    if ids_path.exists():
        cand = json.loads(ids_path.read_text(encoding="utf-8"))
    else:
        cand = ids()
        ids_path.write_text(json.dumps(cand, ensure_ascii=False), encoding="utf-8")
    print("кандидатов:", len(cand), flush=True)
    with ThreadPoolExecutor(3) as ex:
        res = [r for r in ex.map(check, cand.values()) if r]
    (HERE / "nails-checked.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    good = [r for r in res if "error" not in r and r["reviews"] >= MIN and (r["rating"] or 0) >= 4.6]
    good.sort(key=lambda r: -r["reviews"])
    (HERE / "nails-found.json").write_text(json.dumps(good, ensure_ascii=False, indent=1), encoding="utf-8")
    print("проверено:", len(res), "подходят:", len(good), "ошибок:", sum(1 for r in res if "error" in r),
          "капча:", sum(1 for r in res if r.get("captcha")))

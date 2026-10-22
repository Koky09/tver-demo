"""Поиск PlayStation- и компьютерных клубов в Москве для новой партии.
    python tools/newclient/find_clubs.py        -> tools/newclient/clubs-found.json
Берём: игровой / компьютерный клуб, одна точка или маленькая сеть (до MAX_BRANCHES), без своего сайта и без своей онлайн-брони
(Langame, Gizmo, SmartShell и т.п. считаем сайтом), рейтинг от 4,5, отзывов от MIN (max из 2ГИС и Яндекса),
последний отзыв не старше полугода."""
import json, re, sys, time, datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from gis import search, firm, reviews
from find_tires import AREAS, SITE_OK, done_phones
import find_tires2

MIN = 10
MAX_BRANCHES = 4  # маленькие сети (2–4 точки) тоже подходят: владелец один, сайт делаем на найденную точку
CITY = "moscow"
QUERIES = [f"{w} {a}" for a in AREAS for w in ("playstation клуб", "компьютерный клуб", "клуб видеоигр", "киберклуб")]
RUBRIC = re.compile(r"видеоигр|компьютерн\w* клуб|игров\w* клуб|киберспорт|игровых приставок|виртуальн|playstation", re.I)
BOOKING = re.compile(r"langame|gizmo|smartshell|cybershell|senet|icafecloud|yclients|dikidi|booking", re.I)


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
                found[f["id"]] = f
    return found


def d10(p):
    return re.sub(r"\D", "", p)[-10:]


def check(f):
    try:
        rv = reviews(f["id"])
        if (rv["count"] or 0) < 3 or (rv["rating"] or 0) < 4.4:
            return None
        last = datetime.datetime.fromisoformat(rv["last"][:19]) if rv["last"] else None
        if not last or (datetime.datetime.now() - last).days > 183:
            return None
        d = firm(CITY, f["id"])
    except Exception as e:
        return {"id": f["id"], "error": str(e)}
    if not any("Москва" in (a or "") for a in d["adm"]) or (d["branches"] or 1) > MAX_BRANCHES:
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
    print(f'{d["reviews"]:4} {d["rating"]} {d["name"][:40]:40} {d["address"]} | {", ".join(d["rubrics"])[:60]}', flush=True)
    return d


if __name__ == "__main__":
    DONE = done_phones()
    ids_path = HERE / "clubs-ids.json"
    if ids_path.exists():
        cand = json.loads(ids_path.read_text(encoding="utf-8"))
    else:
        cand = ids()
        ids_path.write_text(json.dumps(cand, ensure_ascii=False), encoding="utf-8")
    print("кандидатов:", len(cand), flush=True)
    with ThreadPoolExecutor(3) as ex:
        res = [r for r in ex.map(check, cand.values()) if r]
    (HERE / "clubs-checked.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    good = [r for r in res if "error" not in r and r["reviews"] >= MIN and (r["rating"] or 0) >= 4.5]
    good.sort(key=lambda r: -r["reviews"])
    (HERE / "clubs-found.json").write_text(json.dumps(good, ensure_ascii=False, indent=1), encoding="utf-8")
    print("проверено:", len(res), "подходят:", len(good), "ошибок:", sum(1 for r in res if "error" in r),
          "капча:", sum(1 for r in res if r.get("captcha")))

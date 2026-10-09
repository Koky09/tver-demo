"""Второй этап отбора шиномонтажей: независимые без сайта + отзывы с Яндекс Карт.
    python tools/newclient/find_tires2.py   (нужны tires-ids.json и tires-reviews.json из find_tires.py)
В 2ГИС у маленьких мастерских мало отзывов, на Яндексе больше, поэтому «отзывов» = max(2ГИС, Яндекс).
Карточку Яндекса сверяем с 2ГИС по телефону. Город — только Москва (поиск 2ГИС подмешивает другие города)."""
import json, re, sys, time, urllib.parse, urllib.request, datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from gis import firm
from find_tires import SITE_OK, done_phones

MIN = 50
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36", "Accept-Language": "ru"}


def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read().decode("utf-8", "ignore")


def d10(p):
    return re.sub(r"\D", "", p)[-10:]


def yandex(name, addr, phones):
    """Карточка Яндекса с тем же телефоном: рейтинг, отзывы, сайты, соцсети"""
    q = f"{re.split(r',', name)[0]} {addr or ''} Москва"
    h = get("https://yandex.ru/maps/213/moscow/?text=" + urllib.parse.quote(q))
    if "showcaptcha" in h:
        return {"captcha": True}
    orgs = list(dict.fromkeys(re.findall(r"/maps/org/([a-z0-9_]+)/(\d+)", h)))[:4]
    for slug, oid in orgs:
        o = get(f"https://yandex.ru/maps/org/{slug}/{oid}/")
        i = o.find('"fullAddress"')
        seg = o[max(0, i - 4000): i + 6000] if i >= 0 else ""
        yph = {d10(x) for x in re.findall(r'"value":"(\+7\d{10})"', seg)}
        if not yph & {d10(p) for p in phones}:
            continue
        rd = re.search(r'"ratingData":\{"ratingCount":(\d+),"ratingValue":([\d.]+),"reviewCount":(\d+)\}', seg)
        urls = re.findall(r'"urls":\[([^\]]*)\]', seg)
        sites = [u for u in re.findall(r'"(https?://[^"]+)"', urls[0] if urls else "") if not SITE_OK.search(u)]
        soc = "".join(o[m.start():m.start() + 3000] for m in re.finditer("business-contacts-view__social", o))
        return {"ya": f"{slug}/{oid}", "ya_url": f"https://yandex.ru/maps/org/{slug}/{oid}/",
                "ya_rating": round(float(rd[2]), 1) if rd else None, "ya_reviews": int(rd[3]) if rd else 0, "ya_ratings": int(rd[1]) if rd else 0,
                "ya_sites": sites, "ya_tg": sorted(set(u for u in re.findall(r"t\.me/([A-Za-z0-9_+]{4,40})", soc) if u.lower() != "mapsyandex")),
                "ya_wa": sorted(set(re.findall(r"wa\.me/(\d+)", soc))), "ya_vk": sorted(set(re.findall(r"vk\.com/([A-Za-z0-9_.]+)", soc)))}
    return {"ya": None}


def one(fid):
    r = REV[fid]
    try:
        d = firm("moscow", fid)
    except Exception as e:
        return {"id": fid, "error": "2gis " + str(e)}
    if not any("Москва" in (a or "") for a in d["adm"]) or (d["branches"] or 1) > 1 or "Шиномонтаж" not in d["rubrics"]:
        return None
    if [w for w in d["contacts"].get("website", []) if not SITE_OK.search(w)]:
        return None
    phones = d["contacts"].get("phone", [])
    if not phones or any(d10(p) in DONE for p in phones):
        return None
    time.sleep(0.5)
    try:
        y = yandex(d["name"], d["address"], phones)
    except Exception as e:
        y = {"ya": None, "yerr": str(e)}
    d.update({"gis_rating": r.get("rating"), "gis_reviews": r.get("count") or 0, "gis_last": r.get("last")})
    d.update(y)
    if y.get("ya_sites"):
        return None
    d["reviews"] = max(d["gis_reviews"], d.get("ya_reviews") or 0)
    d["rating"] = d.get("ya_rating") if (d.get("ya_reviews") or 0) >= d["gis_reviews"] and d.get("ya_rating") else d["gis_rating"]
    print(f'{d["reviews"]:4} {d["rating"]} {d["name"][:40]:40} ya={d.get("ya")} {"CAPTCHA" if y.get("captcha") else ""}', flush=True)
    return d


if __name__ == "__main__":
    IDS = json.loads((HERE / "tires-ids.json").read_text(encoding="utf-8"))
    REV = json.loads((HERE / "tires-reviews.json").read_text(encoding="utf-8"))
    DONE = done_phones()
    old = {x["id"]: x for x in json.loads((HERE / "tires-checked.json").read_text(encoding="utf-8"))} if (HERE / "tires-checked.json").exists() else {}
    pre = [i for i, r in REV.items() if i not in old and "err" not in r and ((r.get("count") or 0) < 5 or (r.get("rating") or 5) >= 4.4)]
    print("на проверку:", len(pre), flush=True)
    with ThreadPoolExecutor(3) as ex:
        res = [x for x in ex.map(one, pre) if x] + list(old.values())
    (HERE / "tires-checked.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    good = [x for x in res if "error" not in x and x["reviews"] >= MIN and (x["rating"] or 0) >= 4.5]
    good.sort(key=lambda x: -x["reviews"])
    (HERE / "tires-found.json").write_text(json.dumps(good, ensure_ascii=False, indent=1), encoding="utf-8")
    print("проверено:", len(res), "подходят:", len(good), "капча:", sum(1 for x in res if x.get("captcha")))

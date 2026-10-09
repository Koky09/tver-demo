"""2ГИС из Python (без браузера): поиск, карточка, прайс, отзывы.
    from gis import search, firm, prices, reviews"""
import json, re, urllib.parse, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36", "Accept-Language": "ru"}
KEY = "6e7e1929-4ea9-4a5d-8c05-d601860389bd"  # публичный ключ виджета отзывов 2ГИС (из browser-helpers.js)


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode("utf-8", "ignore")


def state(url):
    h = get(url)
    a = h.find("initialState = JSON.parse('")
    if a < 0:
        return None
    st = a + 27
    e = h.find("')", st)
    s = h[st:e]
    s = s.encode("utf-8").decode("unicode_escape").encode("latin-1").decode("utf-8")
    return json.loads(s)


def search(city, q, page=1):
    url = f"https://2gis.ru/{city}/search/{urllib.parse.quote(q)}" + (f"/page/{page}" if page > 1 else "")
    s = state(url)
    p = (s or {}).get("data", {}).get("entity", {}).get("profile", {}) or {}
    return [{"id": k, "name": v["data"]["name"], "address": v["data"].get("address_name")}
            for k, v in p.items() if k.isdigit() and v.get("data") and v["data"].get("name")]


def contacts(d):
    out = {}
    for g in d.get("contact_groups") or []:
        for c in g.get("contacts") or []:
            out.setdefault(c["type"], []).append(re.sub(r"\?text=.*", "", c.get("url") or c.get("value") or c.get("text") or ""))
    return out


def firm(city, fid):
    s = state(f"https://2gis.ru/{city}/firm/{fid}")
    d = s["data"]["entity"]["profile"][fid]["data"]
    return {"id": fid, "name": d["name"], "address": d.get("address_name"), "contacts": contacts(d), "schedule": d.get("schedule"),
            "branches": (d.get("org") or {}).get("branch_count"), "rubrics": [r.get("name") for r in d.get("rubrics") or []],
            "attrs": [a["name"] for g in d.get("attribute_groups") or [] for a in g.get("attributes") or []],
            "point": d.get("point"), "adm": [x.get("name") for x in d.get("adm_div") or []]}


def prices(city, fid):
    s = state(f"https://2gis.ru/{city}/firm/{fid}/tab/prices")
    m = ((s or {}).get("data") or {}).get("market") or {}
    out = []
    for o in (m.get("offers") or {}).values():
        o = o.get("data")
        if not o:
            continue
        p = ((m.get("products") or {}).get(o.get("productId")) or {}).get("data") or {}
        pr = p.get("product") or {}
        r = (o.get("price_value") or {}).get("range") or {}
        if pr.get("name") and (o.get("price") or 0) > 1:
            cat = (pr.get("categories") or [{}])[0].get("label")
            out.append({"name": pr["name"], "cat": cat, "price": o["price"], "max": r.get("max"), "from": bool(r.get("min") and not r.get("max"))})
    return out


def reviews(fid):
    u = (f"https://public-api.reviews.2gis.com/2.0/branches/{fid}/reviews?limit=1&sort_by=date_created&key={KEY}"
         "&locale=ru_RU&fields=meta.branch_rating,meta.branch_reviews_count")
    r = json.loads(get(u))
    return {"rating": r["meta"].get("branch_rating"), "count": r["meta"].get("branch_reviews_count"),
            "last": r["reviews"][0]["date_created"] if r.get("reviews") else None}

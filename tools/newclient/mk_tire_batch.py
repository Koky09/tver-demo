"""Партия шиномонтажей из tires-found.json -> batches/<имя>.json (формат mkclients.py).
    python tools/newclient/mk_tire_batch.py moscow-tires-2026-10-09 [сколько]
Цены — с вкладки «Цены» Яндекс Карт (если есть), иначе примерные (demo). Часы — из 2ГИС."""
import json, re, sys, time, urllib.request
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36", "Accept-Language": "ru"}
DAYS = {"Sun": "0", "Mon": "1", "Tue": "2", "Wed": "3", "Thu": "4", "Fri": "5", "Sat": "6"}
THEMES = ["race", "protocol", "sticker", "lacquer", "atelier", "stitch"]  # aqua — вода и пузыри, это для моек
# акцент и цвет текста на нём (тёмные/яркие «гаражные» цвета)
COLORS = [("#f59e0b", "#1c1302"), ("#ef4444", "#ffffff"), ("#22c55e", "#04140a"), ("#3b82f6", "#ffffff"), ("#eab308", "#1a1500"),
          ("#f97316", "#1c0d02"), ("#14b8a6", "#03201c"), ("#a3e635", "#121a03"), ("#e11d48", "#ffffff"), ("#0ea5e9", "#03131c")]
DEMO = [["tire", "Сезонная переобувка R13–R15", 2000, 40, "4 колеса, с балансировкой"],
        ["tire", "Сезонная переобувка R16–R17", 2600, 45, "4 колеса, с балансировкой"],
        ["tire", "Переобувка R18+ и внедорожники", 3600, 60, "4 колеса, с балансировкой"],
        ["balance", "Балансировка колеса", 400, 15, "за 1 колесо"],
        ["repair", "Ремонт прокола", 600, 30, "жгут или заплатка"],
        ["storage", "Хранение шин на сезон", 4000, 10, "комплект 4 шины", "от"]]
TR = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя", "a b v g d e e zh z i y k l m n o p r s t u f h ts ch sh sch  y  e yu ya".split(" ")))


def get(u):
    for k in range(4):
        try:
            return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read().decode("utf-8", "ignore")
        except Exception:
            if k == 3:
                raise
            time.sleep(3 * (k + 1))


def translit(s):
    s = "".join(TR.get(ch, ch) for ch in s.lower())
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s)).strip("-")


def hours(sch):
    if not sch or sch.get("is_24x7"):
        return "24/7"
    out = {}
    for k, v in sch.items():
        if k in DAYS and v.get("working_hours"):
            w = v["working_hours"][0]
            f = lambda t: int(t[:2]) + (0.5 if t[3:5] >= "30" else 0)
            out[DAYS[k]] = [f(w["from"]), f(w["to"]) if w["to"] != "00:00" else 24]
    vals = list(out.values())
    base = max(vals, key=vals.count) if vals else [9, 21]
    h = {"default": base}
    for d in DAYS.values():
        if d not in out:
            h[d] = []          # выходной
        elif out[d] != base:
            h[d] = out[d]
    return h


def street_name(addr):
    a = re.split(r",", addr or "")[0].strip()
    m = re.match(r"(?:улица|ул\.)\s+(.+)", a) or re.match(r"(.+?)\s+улица$", a)
    if m:
        core = m.group(1)
        if re.search(r"(ая|яя)$", core):   # «Ташкентская улица» -> «на Ташкентской»
            core = re.sub(r"ая$", "ой", re.sub(r"яя$", "ей", core))
        return "на " + core
    return ", " + re.sub(r",\s*", " ", addr or "")      # «Шиномонтаж, Чечёрский проезд 31»


def ya_prices(url):
    try:
        h = get(url + "prices/")
    except Exception:
        return []
    out = []
    for m in re.finditer(r'\{"title":"((?:[^"\\]|\\.){3,90})"(?:,"description":"((?:[^"\\]|\\.)*)")?,"price":"([\d.]+)","currency":"₽"', h):
        t = json.loads('"' + m.group(1) + '"')
        out.append((t, float(m.group(3)), json.loads('"' + (m.group(2) or "") + '"')))
    return list(dict.fromkeys(out))


def pick(pr):
    """Не больше 7 услуг из прайса: переобувка (до 3 размеров), балансировка, прокол, хранение, правка дисков"""
    svc = []
    def first(rx, nrx=None):
        for t, p, d in pr:
            if re.search(rx, t, re.I) and not (nrx and re.search(nrx, t, re.I)) and p >= 100:
                return t, p, d
    seas = [(t, p, d) for t, p, d in pr if re.search(r"замен|переобув|сезон|комплекс|шиномонтаж", t, re.I) and p >= 200]
    def size(t):
        m = re.search(r"R?\s?(1[3-9]|2[0-4])\b", t)
        return int(m.group(1)) if m else None
    by = {}
    for t, p, d in seas:
        s = size(t)
        if s and s not in by:
            by[s] = (t, p, d)
    sizes = [s for s in (15, 16, 17, 18, 19, 20) if s in by]
    chosen = sizes[1:4] if len(sizes) > 3 else sizes
    for s in chosen:
        t, p, d = by[s]
        per = p < 2000 and not re.search(r"комплект|4 колес|4-х", t + d, re.I)
        svc.append(["tire", t[:60], int(p), 45 if s < 18 else 60, "за 1 колесо" if per else None])
    if not chosen and seas:
        t, p, d = seas[0]
        svc.append(["tire", t[:60], int(p), 45, None])
    for kind, rx, nrx, dur in (("balance", r"баланс", r"замен|сезон|комплекс", 15), ("repair", r"прокол|жгут|латк|заплат|ремонт ш", None, 30),
                               ("storage", r"хранен", None, 10), ("rims", r"правк|прокат", None, 60)):
        f = first(rx, nrx)
        if f:
            svc.append([kind, f[0][:60], int(f[1]), dur, None])
    return svc[:7]


def main():
    name = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 999
    found = json.loads((HERE / "tires-found.json").read_text(encoding="utf-8"))
    used = {p.stem for p in (ROOT / "clients").glob("*.json")}
    batch = []
    for x in found:
        if len(batch) >= limit:
            break
        if not x.get("address") or re.search(r"грузов", x["name"], re.I) or (re.search(r"детейлинг", x["name"], re.I) and not re.search(r"шиномонтаж", x["name"], re.I)):
            print("пропуск:", x["name"], x.get("address")); continue
        if x.get("ya_url"):
            o = get(x["ya_url"])
            st = re.search(r'"fullAddress"[^{}]{0,400}?"status":"([a-z-]+)"', o)
            if st and st.group(1) != "open":
                print("закрыт на Яндексе:", x["name"], x["address"], st.group(1)); continue
        i = len(batch)
        brand = re.split(r",", x["name"])[0].strip()
        generic = re.fullmatch(r"(шиномонтажная мастерская|шиномонтаж|шиномонтажная|центр шиномонтажа)", brand, re.I)
        title = ("Шиномонтаж" + ("" if street_name(x["address"]).startswith(",") else " ") + street_name(x["address"])) if generic else brand
        slug = "shina-" + translit(brand if not generic else re.split(r",", x["address"])[0])[:28].strip("-")
        k = 2
        while slug in used:
            slug = f"{slug}-{k}"; k += 1
        used.add(slug)
        phones = x["contacts"].get("phone", [])
        mob = [p for p in phones if re.sub(r"\D", "", p)[1:2] == "9"]
        phone = (mob or phones)[0]
        wa = [re.sub(r"\D", "", w) for w in x["contacts"].get("whatsapp", [])] + (x.get("ya_wa") or [])
        tgs = [re.sub(r"https?://t\.me/", "", t) for t in x["contacts"].get("telegram", [])] + (x.get("ya_tg") or [])
        msg = f"https://wa.me/{wa[0]}" if wa else (f"https://t.me/{tgs[0]}" if tgs else "")
        pr = ya_prices(x["ya_url"]) if x.get("ya_url") else []
        svc = pick(pr)
        demo = len(svc) < 3
        if demo:
            svc = DEMO
        time.sleep(0.4)
        acc, ink = COLORS[i % len(COLORS)]
        words = [w for w in re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", title) if w.lower() not in ("шиномонтаж", "на", "в") and len(w) > 1 and not w[0].isdigit()]
        short = ((words[0][:1] + (words[1][:1] if len(words) > 1 else "")) if words else "Ш").upper()
        batch.append({
            "slug": slug, "name": title, "short": short, "city": "Москва", "addr": x["address"], "phone": phone, "msg": msg,
            "theme": THEMES[i % len(THEMES)], "accent": acc, "ink": ink,
            "tag": "Шиномонтаж" + (" круглосуточно" if hours(x.get("schedule")) == "24/7" else "") + (" · " + x["adm"][-1] if x.get("adm") else ""),
            "hours": hours(x.get("schedule")), "boxes": 2, "kind": "tire", "demo": demo, "svc": svc,
            "rating": x["rating"], "reviews": x["reviews"], "source": "Яндекс Карты" if (x.get("ya_reviews") or 0) >= x["gis_reviews"] else "2ГИС",
            "tg": "", "tgn": "", "_tg_cand": sorted(set(tgs)), "_wa": sorted(set(wa)), "_gis": x["id"], "_ya": x.get("ya_url"), "_prices": len(pr),
        })
        print(f'{slug:32} {title[:36]:36} цены:{"примерные" if demo else len(svc)} {msg}', flush=True)
    (ROOT / "batches").mkdir(exist_ok=True)
    (ROOT / "batches" / f"{name}.json").write_text(json.dumps(batch, ensure_ascii=False, indent=1), encoding="utf-8")
    print("партия:", len(batch))


if __name__ == "__main__":
    main()

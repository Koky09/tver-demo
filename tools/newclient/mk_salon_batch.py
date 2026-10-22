"""Партия салонов красоты из salons-found.json (города-миллионники) -> batches/<имя>.json (формат mkclients.py) + фото в clients/photos.
    python tools/newclient/mk_salon_batch.py <имя-партии> [сколько]
Города — по очереди (каждому городу поровну), внутри города — по числу отзывов.
Цены — с вкладки «Цены» Яндекс Карт (если есть), иначе примерные (demo). Часы — из 2ГИС.
Стиль (marble|botanic|paris|swiss|silk|deco) — поровну, цвет у каждого салона свой, фото — своё (Unsplash, unsplash_salon/)."""
import hashlib, json, re, shutil, sys, time
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from mk_tire_batch import get, translit, hours, street_name, ya_prices
import mk_club_batch as cb

THEMES = ["marble", "botanic", "paris", "swiss", "silk", "deco"]
# тон, насыщенность, яркость акцента; внутри стиля цвета разносятся по кругу (cb.color)
cb.HUE.update({"marble": (30, .45, .5), "botanic": (120, .3, .45), "paris": (350, .6, .55), "swiss": (5, .85, .5), "silk": (300, .55, .68), "deco": (160, .45, .35)})
# фото по номеру в unsplash_salon/_order.txt, подобраны под настроение стиля (мужские и барберские убраны)
POOL = {
    "marble": [11, 19, 20, 21, 23, 46, 47, 59, 64, 95, 98, 148, 156, 157, 133, 82, 88, 103],
    "botanic": [3, 5, 13, 14, 25, 48, 60, 81, 104, 105, 106, 109, 125, 102, 143, 158],
    "paris": [12, 33, 44, 45, 50, 51, 74, 75, 77, 83, 87, 107, 142, 165, 86, 28],
    "swiss": [2, 17, 18, 26, 39, 43, 62, 69, 70, 91, 92, 120, 131, 132, 134, 140, 153],
    "silk": [0, 1, 4, 8, 10, 15, 22, 24, 32, 34, 36, 38, 94, 96, 100, 101, 112, 161, 117, 118, 119],
    "deco": [27, 29, 37, 58, 63, 72, 78, 84, 90, 93, 97, 99, 110, 111, 113, 121, 135, 136, 137, 138, 139, 146, 147, 159],
}
SWISS = ["#e2231a", "#1d4ed8", "#ff5a1f", "#111111", "#0f766e", "#be185d", "#7c3aed", "#b45309", "#0369a1", "#dc2626", "#4338ca",
         "#c2410c", "#15803d", "#9d174d", "#1e40af", "#a21caf", "#0e7490"]  # строгий стиль: без кислотных цветов
ORDER = (HERE / "unsplash_salon" / "_order.txt").read_text().split()
DEMO = [["hair", "Женская стрижка", 1200, 60, "мытьё и укладка включены", "от"],
        ["color", "Окрашивание", 3500, 150, "цена зависит от длины волос", "от"],
        ["style", "Укладка", 1200, 60, "локоны, объём, вечерняя", "от"],
        ["care", "Уход и восстановление волос", 2500, 90, "кератин, ботокс, глубокое увлажнение", "от"],
        ["gel", "Маникюр с покрытием гель-лак", 1600, 120, "с укреплением и снятием", "от"],
        ["brows", "Брови: коррекция и окрашивание", 900, 45, None, "от"]]
cb.NOT = (r"детск|мужск|абонем|сертификат|скидк|1 ногт|за ногот|ремонт|чёлк|челк|кончик|бород|машинк|школьн|усов|наголо|под 0|под ноль|"
          r"пенсион|девоч|мальч|парик|визаж|седин|пластин|татуаж|\bпм\b|перманент|новичок|ученик|студент|депиляц|воск|полировк")
cb.RULES = [  # тип, обязательно, нельзя
    ("hair", r"стрижк", r"окрашив|укладк|ресниц|бров"),
    ("color", r"^окрашив|окрашивание волос|тонирован|мелир|балаяж|airtouch|сложное окраш", r"бров|ресниц|корн|маникюр|педикюр"),
    ("style", r"укладк|причёск|прическ|локон", r"бров|ресниц|свадеб|стрижк"),
    ("care", r"кератин|ботокс|восстановлен|уход за волос|уход для волос", r"лиц|тел|рук|ног|ногт|ресниц|бров"),
    ("gel", r"(маникюр|руки).*(покрыт|гель|шеллак)|покрыт.*гель", r"без покрыт|педик|наращ|снят(?!ием)|ноги"),
    ("pedi", r"педикюр", r"маникюр|бров"),
    ("brows", r"бров", r"наращ|ресниц")]
PREFER = {"hair": "женск", "color": "окрашив", "style": "укладк", "care": "уход|восстанов", "gel": "гель", "pedi": "педикюр", "brows": "коррекц|оформлен"}


def pick(pr):
    """по одной услуге каждого вида: сначала с «правильным» словом (женская стрижка, укладка ...), потом самое короткое название"""
    svc = []
    for kind, need, nrx in cb.RULES:
        c = [(t.split(" | ")[0].strip(), p, d) for t, p, d in pr if cb.MINP[kind] <= p <= 30000 and re.search(need, t, re.I)
             and not re.search(nrx, t, re.I) and not re.search(cb.NOT, t, re.I)]
        if c:
            t, p, d = min(c, key=lambda x: (not re.search(PREFER[kind], x[0], re.I), len(x[0])))
            svc.append([kind, t[0].upper() + t[1:60], int(p), cb.DUR[kind], (d or None) and d[:60]])
    return svc
cb.MINP = {"hair": 400, "color": 1000, "style": 400, "care": 800, "gel": 600, "pedi": 800, "brows": 300}
cb.DUR = {"hair": 60, "color": 150, "style": 60, "care": 120, "gel": 120, "pedi": 90, "brows": 45}


def main():
    name = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    found = json.loads((HERE / "salons-found.json").read_text(encoding="utf-8"))
    by = {}
    for x in sorted(found, key=lambda x: -x["reviews"]):
        by.setdefault(x["city"], []).append(x)
    order = []  # по кругу: лучший салон каждого города, потом второй ...
    while any(by.values()):
        for c in list(by):
            if by[c]:
                order.append(by[c].pop(0))
    used = {p.stem for p in (ROOT / "clients").glob("*.json")}
    batch, used_ph = [], set()
    count = {t: 0 for t in THEMES}
    for x in order:
        if len(batch) >= limit:
            break
        if not x.get("address"):
            print("пропуск без адреса:", x["name"]); continue
        if x.get("ya_url"):
            o = get(x["ya_url"])
            st = re.search(r'"fullAddress"[^{}]{0,400}?"status":"([a-z-]+)"', o)
            if st and st.group(1) != "open":
                print("закрыт на Яндексе:", x["name"], x["address"], st.group(1)); continue
        i = len(batch)
        brand = re.split(r",", x["name"])[0].strip()
        generic = re.fullmatch(r"(салон красоты|парикмахерская|студия красоты|бьюти[- ]студия|салон|студия)", brand, re.I)
        sn = street_name(x["address"])
        title = ("Салон" + ("" if sn.startswith(",") else " ") + sn) if generic else brand
        slug = "salon-" + translit(brand if not generic else re.split(r",", x["address"])[0])[:26].strip("-")
        k = 2
        while slug in used:
            slug = f"{slug}-{k}"; k += 1
        used.add(slug)
        phones = x["contacts"].get("phone", [])
        mob = [p for p in phones if re.sub(r"\D", "", p)[1:2] == "9"]
        phone = (mob or phones)[0]
        wa = [re.sub(r"\D", "", w) for w in x["contacts"].get("whatsapp", [])] + (x.get("ya_wa") or [])
        tgs = [re.sub(r"https?://t\.me/", "", t) for t in x["contacts"].get("telegram", [])] + (x.get("ya_tg") or [])
        msg = f"https://t.me/{tgs[0]}" if tgs else (f"https://wa.me/{wa[0]}" if wa else "")
        pr = ya_prices(x["ya_url"]) if x.get("ya_url") else []
        svc = pick(pr)[:6]
        demo = len(svc) < 3
        if demo:
            svc = cb.jitter(DEMO, slug)
        time.sleep(0.4)
        theme = THEMES[i % len(THEMES)]
        acc, ink = (SWISS[count[theme] % len(SWISS)], "#ffffff") if theme == "swiss" else cb.color(theme, count[theme])
        count[theme] += 1
        pool = [n for n in POOL[theme] if n not in used_ph and n < len(ORDER)]
        if pool:
            n = pool[int(hashlib.md5(slug.encode()).hexdigest()[:6], 16) % len(pool)]
            used_ph.add(n)
            (ROOT / "clients" / "photos").mkdir(exist_ok=True)
            shutil.copy(HERE / "unsplash_salon" / f"{ORDER[n]}.jpg", ROOT / "clients" / "photos" / f"{slug}.jpg")
        words = [w for w in re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", title) if w.lower() not in ("салон", "на", "в", "studio", "beauty", "студия", "красоты") and len(w) > 1]
        short = ((words[0][:1] + (words[1][:1] if len(words) > 1 else "")) if words else "С").upper()
        district = next((a for a in reversed(x.get("adm") or []) if a and a != x["city"] and "район" in a.lower()), "")
        what = "Парикмахерская" if re.search(r"парикмахерск", x["name"], re.I) else "Салон красоты"
        batch.append({
            "slug": slug, "name": title, "short": short, "city": x["city"], "addr": x["address"], "phone": phone, "msg": msg,
            "theme": theme, "accent": acc, "ink": ink, "kicker": what.lower() if theme in ("botanic", "paris") else what,
            "tag": what + (" · " + district if district else ""),
            "hours": cb.fix_hours(hours(x.get("schedule"))), "boxes": 3, "kind": "salon", "demo": demo, "svc": svc,
            "rating": x["rating"], "reviews": x["reviews"], "source": "Яндекс Карты" if (x.get("ya_reviews") or 0) >= x["gis_reviews"] else "2ГИС",
            "tg": "", "tgn": "", "_tg_cand": sorted(set(tgs)), "_wa": sorted(set(wa)), "_gis": x["id"], "_city": x.get("city_slug"),
            "_ya": x.get("ya_url"), "_prices": len(pr),
        })
        print(f'{x["city"][:10]:10} {slug:30} {title[:28]:28} {theme:7} цены:{"примерные" if demo else len(svc)} {msg}', flush=True)
    (ROOT / "batches").mkdir(exist_ok=True)
    (ROOT / "batches" / f"{name}.json").write_text(json.dumps(batch, ensure_ascii=False, indent=1), encoding="utf-8")
    cities = {}
    for b in batch:
        cities[b["city"]] = cities.get(b["city"], 0) + 1
    print("партия:", len(batch), count, cities)


if __name__ == "__main__":
    main()

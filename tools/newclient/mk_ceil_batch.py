"""Партия фирм натяжных потолков (Москва + города-миллионники) -> batches/<имя>.json (формат mkclients.py) + фото в clients/photos.
    python tools/newclient/mk_ceil_batch.py <имя-партии> [сколько]
Источники: ceil-checked.json (Москва, find_ceilings.py) и ceilc-checked.json (города, find_ceilings_cities.py).
Берём всех без своего сайта; сначала с отзывами (по их числу), городам — по очереди.
Цены и калькулятор — примерные рыночные (у каждой фирмы немного свои), в сообщении сказано, что подставим их прайс.
Стиль (blueprint|nordic|loft|gloss|sky) — поровну, цвет и фото у каждой фирмы свои."""
import hashlib, json, re, shutil, sys, time
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from mk_tire_batch import get, translit, hours, street_name
import mk_club_batch as cb

THEMES = ["blueprint", "nordic", "loft", "gloss", "sky"]
cb.HUE.update({"blueprint": (195, .8, .55), "nordic": (25, .45, .45), "loft": (35, .95, .58), "gloss": (220, .8, .6), "sky": (200, .75, .55)})
POOL = {
    "blueprint": [2, 12, 26, 27, 40, 42, 45, 46, 47, 48, 49, 51, 56, 58, 62, 76, 77, 78, 81, 82, 95, 146, 170, 180, 187, 191, 196, 197, 198, 199, 200, 201, 202],
    "nordic": [1, 4, 5, 10, 22, 28, 37, 41, 63, 64, 65, 66, 70, 71, 73, 74, 84, 88, 138, 155, 161, 162, 177, 192, 193, 204, 208, 211],
    "loft": [7, 8, 9, 24, 30, 33, 38, 59, 61, 83, 89, 90, 91, 100, 104, 108, 109, 110, 111, 113, 116, 123, 124, 126, 129, 130, 154, 163, 175, 178, 181, 186, 189, 214],
    "gloss": [87, 103, 106, 118, 128, 158, 169, 173, 174, 176, 182, 209, 215, 25, 43, 67, 68, 69],
    "sky": [3, 14, 15, 19, 20, 29, 34, 35, 44, 80, 97, 99, 127, 147, 149, 166, 168, 207, 212],
}
WARM = ['#ffb020', '#ff8a3d', '#ffd166', '#f4a259', '#e9c46a', '#ffa94d', '#f6bd60', '#ff9f1c', '#ffc857', '#f7b267', '#fca311', '#ffbe0b', '#fb8b24', '#f9c74f', '#f8961e', '#ffd60a', '#ee9b00', '#ffb703', '#f4a261', '#e76f51']  # лофт: только тёплый свет ламп
ORDER = (HERE / "unsplash_ceil" / "_order.txt").read_text().split()
KICK = {"blueprint": "Натяжные потолки", "nordic": "Натяжные потолки", "loft": "Натяжные потолки и свет", "gloss": "Натяжные потолки", "sky": "Натяжные потолки"}
# цены за м² с материалом и монтажом — средние по рынку, у каждой фирмы ±15% (cb.jitter)
SVC = [["zamer", "Бесплатный замер", 0, 60, "приедем, измерим и посчитаем точно", "", None],
       ["matte", "Матовый потолок", 450, 60, "с материалом и монтажом", "от", "/м²"],
       ["gloss", "Глянцевый потолок", 500, 60, "визуально поднимает комнату", "от", "/м²"],
       ["satin", "Сатиновый потолок", 550, 60, "мягкий перламутровый блеск", "от", "/м²"],
       ["fabric", "Тканевый потолок", 1200, 60, "без нагрева, дышит", "от", "/м²"],
       ["float", "Парящий потолок с подсветкой", 1300, 60, "светодиодная лента по периметру", "от", "/м²"],
       ["lines", "Световые линии", 2500, 60, "встроенные светодиодные линии", "от", "/пог. м"],
       ["light", "Установка светильника", 400, 15, None, "от", "/шт."]]
CALC = {"types": [["Матовый", 450], ["Глянцевый", 500], ["Сатиновый", 550], ["Тканевый", 1200], ["Парящий", 1300]],
        "extras": [["Светильники", 400], ["Люстра", 600], ["Обход трубы", 300], ["Скрытый карниз, метров", 1500, "м"]],
        "area": 18, "min": 5000}


def k_of(slug):
    return 0.85 + int(hashlib.md5(slug.encode()).hexdigest()[:4], 16) % 31 / 100


def main():
    name = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    pool = []
    for f, city in (("ceil-checked.json", "Москва"), ("ceilc-checked.json", None)):
        p = HERE / f
        if p.exists():
            for x in json.loads(p.read_text(encoding="utf-8")):
                if "error" in x or not x.get("address"):
                    continue
                if x.get("reviews") and (x.get("rating") or 0) < 4.5:
                    continue
                x["city"] = x.get("city") or city
                pool.append(x)
    by = {}
    for x in sorted(pool, key=lambda x: -(x.get("reviews") or 0)):
        by.setdefault(x["city"], []).append(x)
    order = []
    while any(by.values()):
        for c in list(by):
            if by[c]:
                order.append(by[c].pop(0))
    used = {p.stem for p in (ROOT / "clients").glob("*.json")}
    seen_phones, batch, used_ph = set(), [], set()
    count = {t: 0 for t in THEMES}
    for x in order:
        if len(batch) >= limit:
            break
        if re.search(r"двер|door|керамик|плитк|электрик|окн|опт|строительная фирма|магазин|склад", x["name"], re.I):
            print("не про потолки, пропуск:", x["name"]); continue
        phones = x["contacts"].get("phone", [])
        if not phones:
            continue
        d10 = {re.sub(r"\D", "", p)[-10:] for p in phones}
        if d10 & seen_phones:
            print("тот же телефон, пропуск:", x["name"]); continue
        if x.get("ya_url"):
            o = get(x["ya_url"])
            st = re.search(r'"fullAddress"[^{}]{0,400}?"status":"([a-z-]+)"', o)
            if st and st.group(1) != "open":
                print("закрыт на Яндексе:", x["name"], st.group(1)); continue
            time.sleep(0.4)
        seen_phones |= d10
        i = len(batch)
        brand = re.split(r",", x["name"])[0].strip()
        generic = re.fullmatch(r"(натяжные потолки|натяжной потолок|потолки|компания по установке натяжных потолков)", brand, re.I)
        sn = street_name(x["address"])
        title = ("Потолки" + ("" if sn.startswith(",") else " ") + sn) if generic else brand
        slug = "ceil-" + translit(brand if not generic else re.split(r",", x["address"])[0])[:26].strip("-")
        k = 2
        while slug in used:
            slug = f"{slug}-{k}"; k += 1
        used.add(slug)
        mob = [p for p in phones if re.sub(r"\D", "", p)[1:2] == "9"]
        phone = (mob or phones)[0]
        wa = [re.sub(r"\D", "", w) for w in x["contacts"].get("whatsapp", [])] + (x.get("ya_wa") or [])
        tgs = [re.sub(r"https?://t\.me/", "", t) for t in x["contacts"].get("telegram", [])] + (x.get("ya_tg") or [])
        msg = f"https://t.me/{tgs[0]}" if tgs else (f"https://wa.me/{wa[0]}" if wa else "")
        kk = k_of(slug)
        svc = [[a, b, (round(c * kk / 10) * 10 if c else 0), *rest] for a, b, c, *rest in SVC]
        calc = {"types": [[n, round(p * kk / 10) * 10] for n, p in CALC["types"]],
                "extras": [[n, round(p * kk / 50) * 50, *u] for n, p, *u in CALC["extras"]], "area": CALC["area"], "min": CALC["min"]}
        theme = THEMES[i % len(THEMES)]
        acc, ink = (WARM[count[theme] % len(WARM)], "#1c1d1f") if theme == "loft" else cb.color(theme, count[theme])
        count[theme] += 1
        free = [n for n in POOL[theme] if n not in used_ph and n < len(ORDER)]
        if free:
            n = free[int(hashlib.md5(slug.encode()).hexdigest()[:6], 16) % len(free)]
            used_ph.add(n)
            (ROOT / "clients" / "photos").mkdir(exist_ok=True)
            shutil.copy(HERE / "unsplash_ceil" / f"{ORDER[n]}.jpg", ROOT / "clients" / "photos" / f"{slug}.jpg")
        words = [w for w in re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", title) if w.lower() not in ("потолки", "потолок", "на", "в") and len(w) > 1]
        short = ((words[0][:1] + (words[1][:1] if len(words) > 1 else "")) if words else "П").upper()
        district = next((a for a in reversed(x.get("adm") or []) if a and a != x["city"] and re.search(r"район|округ", a, re.I)), "")
        h = cb.fix_hours(hours(x.get("schedule")))
        batch.append({
            "slug": slug, "name": title, "short": short, "city": x["city"], "addr": x["address"], "phone": phone, "msg": msg,
            "theme": theme, "accent": acc, "ink": ink, "kicker": KICK[theme],
            "tag": "Натяжные потолки под ключ" + (" · " + district if district else ""),
            "hours": h if h != "24/7" else {"default": [9, 21]}, "boxes": 2, "kind": "ceiling", "demo": True, "svc": svc,
            "calc": calc, "bookSvc": "zamer",
            "rating": x.get("rating") if x.get("reviews") else None, "reviews": x.get("reviews") or 0,
            "source": "Яндекс Карты" if (x.get("ya_reviews") or 0) >= (x.get("gis_reviews") or 0) else "2ГИС",
            "tg": "", "tgn": "", "_tg_cand": sorted(set(tgs)), "_wa": sorted(set(wa)), "_gis": x["id"], "_ya": x.get("ya_url"),
            "_branches": x.get("branches"),
        })
        print(f'{x["city"][:10]:10} {slug:30} {title[:28]:28} {theme:9} отзывов {x.get("reviews") or 0}', flush=True)
    (ROOT / "batches").mkdir(exist_ok=True)
    (ROOT / "batches" / f"{name}.json").write_text(json.dumps(batch, ensure_ascii=False, indent=1), encoding="utf-8")
    cities = {}
    for b in batch:
        cities[b["city"]] = cities.get(b["city"], 0) + 1
    print("партия:", len(batch), count, cities)


if __name__ == "__main__":
    main()

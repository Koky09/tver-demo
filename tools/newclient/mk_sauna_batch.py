"""Партия бань и саун -> batches/<имя>.json (формат mkclients.py) + настоящие фото с карточки Яндекс Карт.
    python tools/newclient/mk_sauna_batch.py <имя-партии> [сколько]      собрать партию и скачать фото
    python tools/newclient/mk_sauna_batch.py --sheets <имя-партии>      листы с фото для просмотра (sauna_photos/_sheets)
    python tools/newclient/mk_sauna_batch.py --apply <имя-партии>       фото -> clients/photos (шапка) и clients/gallery (галерея)
Источник: sauna-found.json (find_saunas.py). Фото: tools/newclient/sauna_photos/<slug>/NN.jpg;
плохие (не то заведение, люди, тёмные) номера пишу в sauna_photos/_skip.json {"slug": [номера]}, шапка — первое не пропущенное.
Цены примерные рыночные по городу (±15% у каждой), в сообщении сказано, что подставим их прайс.
Стиль (timber|ember|pine|frost) — поровну, цвет у каждой свой."""
import hashlib, io, json, re, shutil, sys, time
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from mk_tire_batch import get, translit, hours, street_name
import mk_club_batch as cb

PH = HERE / "sauna_photos"
THEMES = ["timber", "ember", "pine", "frost"]
cb.HUE.update({"timber": (28, .7, .5), "ember": (18, .9, .55), "pine": (140, .45, .38), "frost": (12, .75, .52)})
# цена часа малого зала (до 4–6 гостей) по городу; большой зал — ×1,6
HOUR = {"Москва": 2500, "Санкт-Петербург": 2200}
NOT = r"ривьера|оттенков|гамильтон|теннис|терм|физкультурн|village|гостинич|отел|база отдыха|фитнес|бассейн$|спорт"


def k_of(slug):
    return 0.85 + int(hashlib.md5(slug.encode()).hexdigest()[:4], 16) % 31 / 100


def kick(name):
    """подпись над названием — только по самому названию (рубрика «Бани и сауны» есть у всех)"""
    return "Сауна" if re.search(r"саун", name, re.I) else "Русская баня" if re.search(r"бан", name, re.I) else "Баня и сауна"


def tag(name):
    if re.search(r"дров", name, re.I):
        return "Баня на дровах с онлайн-бронью"
    return {"Сауна": "Сауна", "Русская баня": "Баня"}.get(kick(name), "Баня и сауна") + " с онлайн-бронью"


def r50(x):
    return int(round(x / 50) * 50)


def ya_photos(url, n=14):
    """ID фото из галереи карточки Яндекс Карт (как на сайте карточки, по порядку)"""
    base = re.sub(r"[?#].*", "", url).rstrip("/")
    seen = []
    for u in (base + "/gallery/", base + "/"):
        try:
            h = get(u)
        except Exception:
            continue
        for m in re.findall(r"avatars\.mds\.yandex\.net/get-altay/(\d+/[0-9a-zA-Z_-]+)", h):
            if m not in seen:
                seen.append(m)
        if len(seen) >= n:
            break
        time.sleep(0.4)
    return seen[:n]


def download(slug, url):
    import urllib.request
    from PIL import Image
    d = PH / slug
    if d.is_dir() and any(d.glob("*.jpg")):
        return len(list(d.glob("*.jpg")))
    d.mkdir(parents=True, exist_ok=True)
    k = 0
    for pid in ya_photos(url):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(f"https://avatars.mds.yandex.net/get-altay/{pid}/XXL",
                                                                headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read()
            im = Image.open(io.BytesIO(raw)).convert("RGB")
        except Exception:
            continue
        if min(im.size) < 400:
            continue
        im.thumbnail((1600, 1600))
        k += 1
        im.save(d / f"{k:02d}.jpg", quality=84)
    return k


def build(name, limit):
    found = json.loads((HERE / "sauna-found.json").read_text(encoding="utf-8"))
    by = {}
    for x in sorted(found, key=lambda x: -(x.get("reviews") or 0)):
        by.setdefault(x["city"], []).append(x)
    order = []
    while any(by.values()):
        for c in list(by):
            if by[c]:
                order.append(by[c].pop(0))
    # сначала те, чьи фото я уже просмотрел (из прошлой сборки этой партии)
    prev = ROOT / "batches" / f"{name}.json"
    done = {b["_gis"] for b in json.loads(prev.read_text(encoding="utf-8"))} if prev.exists() else set()
    order = [x for x in order if x["id"] in done] + [x for x in order if x["id"] not in done]
    used = {p.stem for p in (ROOT / "clients").glob("*.json")}
    seen_phones, batch = set(), []
    count = {t: 0 for t in THEMES}
    for x in order:
        if len(batch) >= limit:
            break
        if re.search(NOT, x["name"], re.I):
            print("не баня, пропуск:", x["name"]); continue
        if x.get("ya_booking"):
            print("своя бронь на Яндексе, пропуск:", x["name"]); continue
        if not x.get("ya_url"):
            print("нет карточки Яндекса (нет фото), пропуск:", x["name"]); continue
        phones = x["contacts"].get("phone", [])
        d10 = {re.sub(r"\D", "", p)[-10:] for p in phones}
        if not phones or d10 & seen_phones:
            continue
        o = get(x["ya_url"])
        st = re.search(r'"fullAddress"[^{}]{0,400}?"status":"([a-z-]+)"', o)
        if st and st.group(1) != "open":
            print("закрыт на Яндексе:", x["name"], st.group(1)); continue
        brand = re.split(r",", x["name"])[0].strip()
        generic = re.fullmatch(r"(сауна|баня|бани|банный комплекс|русская баня)", brand, re.I)
        sn = street_name(x["address"])
        brand = re.sub(r"[\s&+\-–]+$", "", brand)
        title = (brand.capitalize() + ("" if sn.startswith(",") else " ") + sn) if generic else brand
        if not generic and len(brand) <= 3 and not re.search(r"\d", brand):   # «Цк» -> «Баня «Цк»»
            title = ("Баня" if re.search(r"бан", x["name"], re.I) else "Сауна") + f" «{brand.upper()}»"
        slug = "sauna-" + translit(brand if not generic else brand + " " + re.split(r",", x["address"])[0])[:26].strip("-")
        k = 2
        while slug in used:
            slug = f"{slug}-{k}"; k += 1
        n = download(slug, x["ya_url"])
        if n < 3:
            print("мало фото на Яндексе:", x["name"], n); continue
        used.add(slug)
        seen_phones |= d10
        i = len(batch)
        mob = [p for p in phones if re.sub(r"\D", "", p)[1:2] == "9"]
        phone = (mob or phones)[0]
        wa = [re.sub(r"\D", "", w) for w in x["contacts"].get("whatsapp", [])] + (x.get("ya_wa") or [])
        tgs = [re.sub(r"https?://t\.me/", "", t) for t in x["contacts"].get("telegram", [])] + (x.get("ya_tg") or [])
        msg = f"https://t.me/{tgs[0]}" if tgs else (f"https://wa.me/{wa[0]}" if wa else "")
        kk = k_of(slug)
        hr = HOUR.get(x["city"], 1500) * kk
        big = hr * 1.6
        place = "сауна" if kick(x["name"]) == "Сауна" else "баня"
        svc = [["bath2", f"{place.capitalize()} на 2 часа", r50(hr * 2), 120, "до 4–6 гостей: парная, отдых, чай", "", None],
               ["bath3", f"{place.capitalize()} на 3 часа", r50(hr * 3), 180, "больше времени — дешевле час", "", None],
               ["bigroom", "Большой зал на 3 часа", r50(big * 3), 180, "для компании до 10–12 гостей", "", None],
               ["parmaster", "Парение с пармастером", r50(1800 * kk), 60, "веники, травы, контраст", "от", None]]
        calc = {"title": "Сколько будет стоить", "hint": "Примерная цена. Точную подтвердит администратор.",
                "qtyLabel": "Сколько часов", "unit": "ч", "area": 3, "minArea": 2, "maxArea": 12, "typesLabel": "Зал",
                "types": [["Малый зал", r50(hr)], ["Большой зал", r50(big)]],
                "extras": [["Веник", r50(400 * kk)], ["Полотенце и простыня", r50(250 * kk), "комплект"], ["Пармастер", r50(1800 * kk), "сеанс"]],
                "min": r50(hr * 2), "cta": "Забронировать"}
        theme = THEMES[i % len(THEMES)]
        acc, ink = cb.color(theme, count[theme])
        count[theme] += 1
        words = [w for w in re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", title) if w.lower() not in ("сауна", "баня", "бани", "на", "в", "у") and len(w) > 1]
        short = ((words[0][:1] + (words[1][:1] if len(words) > 1 else "")) if words else "Б").upper()
        district = next((a for a in reversed(x.get("adm") or []) if a and a != x["city"] and re.search(r"район|округ", a, re.I)), "")
        h = hours(x.get("schedule"))
        h = {"default": [10, 24]} if h == "24/7" else cb.fix_hours(h)
        batch.append({
            "slug": slug, "name": title, "short": short, "city": x["city"], "addr": x["address"], "phone": phone, "msg": msg,
            "theme": theme, "accent": acc, "ink": ink,
            "kicker": kick(x["name"]), "tag": tag(x["name"]) + (" · " + district if district else ""),
            "hours": h, "boxes": 2, "kind": "sauna", "demo": True, "svc": svc, "calc": calc,
            "rating": x.get("rating"), "reviews": x.get("reviews") or 0,
            "source": "Яндекс Карты" if (x.get("ya_reviews") or 0) >= (x.get("gis_reviews") or 0) else "2ГИС",
            "tg": "", "tgn": "", "_tg_cand": sorted(set(tgs)), "_wa": sorted(set(wa)), "_gis": x["id"], "_ya": x.get("ya_url"),
        })
        print(f'{x["city"][:10]:10} {slug:32} {title[:28]:28} {theme:7} фото {n:2} отзывов {x.get("reviews") or 0}', flush=True)
        time.sleep(0.4)
    (ROOT / "batches").mkdir(exist_ok=True)
    (ROOT / "batches" / f"{name}.json").write_text(json.dumps(batch, ensure_ascii=False, indent=1), encoding="utf-8")
    cities = {}
    for b in batch:
        cities[b["city"]] = cities.get(b["city"], 0) + 1
    print("партия:", len(batch), count, cities)


def skips():
    """номера фото, которые не берём: мои пометки (_skip.json) + одинаковые у разных бань (_dupes.json, sauna_dedupe.py)"""
    out = {}
    for fn in ("_skip.json", "_dupes.json"):
        f = PH / fn
        if f.exists():
            for k, v in json.loads(f.read_text(encoding="utf-8")).items():
                out.setdefault(k, set()).update(v)
    return out


def sheets(name):
    from PIL import Image, ImageDraw
    batch = json.loads((ROOT / "batches" / f"{name}.json").read_text(encoding="utf-8"))
    out = PH / "_sheets"
    out.mkdir(exist_ok=True)
    sk = skips()
    for j in range(0, len(batch), 6):   # 6 бань на лист, до 14 фото в ряд
        rows = batch[j:j + 6]
        sh = Image.new("RGB", (14 * 170, len(rows) * 150), "white")
        dr = ImageDraw.Draw(sh)
        for r, b in enumerate(rows):
            for c, f in enumerate([f for f in sorted((PH / b["slug"]).glob("*.jpg")) if int(f.stem) not in sk.get(b["slug"], ())][:14]):
                im = Image.open(f); im.thumbnail((165, 120))
                sh.paste(im, (c * 170, r * 150 + 22))
                dr.text((c * 170 + 4, r * 150 + 24), f.stem, fill="yellow")
            dr.text((4, r * 150 + 4), f'{b["slug"]}  {b["name"]}', fill="black")
        sh.save(out / f"{name}-{j // 6 + 1:02d}.jpg", quality=80)
    print("листов:", (len(batch) + 5) // 6, "->", out)


def apply(name):
    batch = json.loads((ROOT / "batches" / f"{name}.json").read_text(encoding="utf-8"))
    from PIL import Image
    skip = skips()
    hero = json.loads((PH / "_hero.json").read_text(encoding="utf-8")) if (PH / "_hero.json").exists() else {}
    for b in batch:
        fs = [f for f in sorted((PH / b["slug"]).glob("*.jpg")) if int(f.stem) not in skip.get(b["slug"], ())]
        if not fs:
            print("нет фото:", b["slug"]); continue
        # шапка: выбранная мной, иначе первая горизонтальная
        h = next((f for f in fs if int(f.stem) == hero.get(b["slug"])), None) or next((f for f in fs if Image.open(f).size[0] > Image.open(f).size[1]), fs[0])
        fs.remove(h); fs.insert(0, h)
        (ROOT / "clients" / "photos").mkdir(exist_ok=True)
        shutil.copy(fs[0], ROOT / "clients" / "photos" / f'{b["slug"]}.jpg')
        g = ROOT / "clients" / "gallery" / b["slug"]
        if g.exists():
            shutil.rmtree(g)
        g.mkdir(parents=True)
        for k, f in enumerate(fs[1:9], 1):
            shutil.copy(f, g / f"{k:02d}.jpg")
        print(f'{b["slug"]:32} шапка {fs[0].stem}, галерея {min(8, len(fs) - 1)}')


if __name__ == "__main__":
    if sys.argv[1] == "--sheets":
        sheets(sys.argv[2])
    elif sys.argv[1] == "--apply":
        apply(sys.argv[2])
    else:
        build(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 100)

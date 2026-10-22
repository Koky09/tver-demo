"""Партия игровых клубов из clubs-found.json -> batches/<имя>.json (формат mkclients.py) + фото шапки в clients/photos.
    python tools/newclient/mk_club_batch.py moscow-clubs-2026-10-22 [сколько]
Цены — с вкладки «Цены» Яндекс Карт (если есть), иначе примерные (demo). Часы — из 2ГИС.
Стиль (neon|arcade|console|hud|synth|versus) — поровну, цвет у каждого клуба свой, фото — своё (Unsplash, unsplash_games/)."""
import colorsys, hashlib, json, re, shutil, sys, time
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from mk_tire_batch import get, translit, hours, street_name, ya_prices

THEMES = ["neon", "console", "hud", "versus", "arcade", "synth"]
# тон (H), насыщенность, яркость акцента для каждого стиля; цвета внутри стиля разносятся по кругу
HUE = {"neon": (300, .95, .58), "console": (215, .85, .55), "hud": (95, .9, .55), "versus": (0, .85, .52), "arcade": (340, .9, .62), "synth": (275, .85, .56)}
KICK = {"neon": "Игровой клуб", "console": "Игровой клуб", "hud": "Компьютерный клуб", "versus": "Выбери бойца", "arcade": "Press start", "synth": "Игровой клуб"}
# фото по номеру в unsplash_games/_order.txt (подобраны под настроение стиля); synth без фото
POOL = {
    "neon": [3, 9, 14, 20, 21, 35, 41, 46, 52, 63, 64, 67, 68, 76, 80, 83, 86, 96, 104, 110, 121],
    "arcade": [4, 7, 8, 10, 16, 24, 26, 33, 37, 84, 89, 93, 111, 112, 113, 114, 115, 125, 137, 140, 141, 142],
    "console": [1, 5, 6, 27, 38, 40, 43, 44, 45, 50, 51, 55, 58, 65, 66, 77, 79, 100, 101, 103, 124, 126, 127, 128, 133],
    "hud": [0, 15, 18, 22, 23, 28, 31, 32, 53, 54, 56, 60, 61, 69, 74, 75, 78, 81, 85, 90, 91, 92, 95, 105, 106, 108, 109, 135, 138, 139],
    "versus": [82, 87, 97, 98, 99, 120, 129, 130, 131, 132, 36, 2, 29, 30, 57, 102, 116],
    "synth": [],
}
ORDER = (HERE / "unsplash_games" / "_order.txt").read_text().split()
DEMO_PS = [["ps", "PS5 — 1 час", 350, 60, "до 4 игроков, геймпады и игры включены", ""],
           ["ps", "PS5 — 3 часа", 900, 180, "выгоднее, чем по часу", ""],
           ["vip", "VIP-комната с PS5", 600, 60, "диван, большой телевизор, до 6 человек", "от"],
           ["night", "Ночь на PS5", 1500, 600, "с 22:00 до 8:00", ""],
           ["party", "День рождения", 4000, 180, "отдельная комната, можно со своим тортом", "от"]]
DEMO_PC = [["pc", "ПК — 1 час", 150, 60, "мощные ПК, мониторы 240 Гц", "от"],
           ["pc", "ПК — 3 часа", 400, 180, "выгоднее, чем по часу", "от"],
           ["vip", "VIP-зал — 1 час", 250, 60, "топовые ПК, отдельный зал", "от"],
           ["ps", "PS5 — 1 час", 350, 60, "до 4 игроков", ""],
           ["night", "Ночной пакет", 600, 600, "с 22:00 до 8:00", "от"],
           ["party", "Аренда зала для команды", 3000, 180, "день рождения или турнир", "от"]]
NOT = r"абонем|сертификат|напит|еда|пицц|снек|кальян|скидк|продаж|ремонт|аксессуар"
RULES = [  # тип, обязательно, нельзя
    ("ps", r"ps ?[45]|playstation|плейстейш|приставк|консол|xbox|sony", r"ноч|vip|вип|рожден|праздн|аренд"),
    ("pc", r"\bпк\b|компьют|\bpc\b|стандарт|общ\w* зал|буткемп|bootcamp", r"ноч|vip|вип|рожден|праздн|аренд|ps|playstation"),
    ("vip", r"vip|вип|приват|кабин", r"ноч|рожден|праздн"),
    ("night", r"ночь|ночн", r"рожден|праздн"),
    ("party", r"рожден|праздн|аренд\w* (зала|клуба)|весь клуб", r""),
    ("vr", r"\bvr\b|виртуал", r"")]
MINP = {"ps": 100, "pc": 50, "vip": 100, "night": 200, "party": 1000, "vr": 200}
DUR = {"ps": 60, "pc": 60, "vip": 60, "night": 600, "party": 180, "vr": 30}


def pick(pr):
    svc = []
    for kind, need, nrx in RULES:
        c = [(t, p, d) for t, p, d in pr if MINP[kind] <= p <= 30000 and re.search(need, t, re.I)
             and not (nrx and re.search(nrx, t, re.I)) and not re.search(NOT, t, re.I)]
        if c:
            t, p, d = min(c, key=lambda x: len(x[0]))
            svc.append([kind, t[:60], int(p), DUR[kind], (d or None) and d[:60]])
    return svc


def jitter(svc, slug):
    """примерные цены немного разные у каждого клуба (±15%, кратно 50)"""
    k = 0.85 + int(hashlib.md5(slug.encode()).hexdigest()[:4], 16) % 31 / 100
    return [[a, b, max(50, round(c * k / 50) * 50), *rest] for a, b, c, *rest in svc]


def color(theme, j):
    h, s, l = HUE[theme]
    r, g, b = colorsys.hls_to_rgb(((h + j * 23) % 360) / 360, l, s)
    lum = 0.2126 * r ** 2.2 + 0.7152 * g ** 2.2 + 0.0722 * b ** 2.2
    return "#%02x%02x%02x" % tuple(int(v * 255) for v in (r, g, b)), ("#0b0b10" if lum > 0.35 else "#ffffff")


def fix_hours(h):
    """клубы часто работают за полночь (12:00–03:00): в записи закрываем день в 24:00"""
    if h == "24/7":
        return h
    return {k: ([v[0], 24] if v and v[1] <= v[0] else v) for k, v in h.items()}


def main():
    name = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 999
    found = json.loads((HERE / "clubs-found.json").read_text(encoding="utf-8"))
    found.sort(key=lambda x: -x["reviews"])
    used = {p.stem for p in (ROOT / "clients").glob("*.json")}
    brands, batch, used_ph = set(), [], set()
    count = {t: 0 for t in THEMES}
    for x in found:
        if len(batch) >= limit:
            break
        if not x.get("address"):
            print("пропуск без адреса:", x["name"]); continue
        brand = re.split(r",", x["name"])[0].strip()
        if brand.lower() in brands:
            print("та же сеть, пропуск:", x["name"], x["address"]); continue
        if x.get("ya_url"):
            o = get(x["ya_url"])
            st = re.search(r'"fullAddress"[^{}]{0,400}?"status":"([a-z-]+)"', o)
            if st and st.group(1) != "open":
                print("закрыт на Яндексе:", x["name"], x["address"], st.group(1)); continue
        brands.add(brand.lower())
        i = len(batch)
        generic = re.fullmatch(r"(компьютерный клуб|игровой клуб|клуб видеоигр|киберклуб|playstation ?клуб|ps ?клуб|клуб)", brand, re.I)
        sn = street_name(x["address"])
        title = ("Клуб" + ("" if sn.startswith(",") else " ") + sn) if generic else brand
        slug = "club-" + translit(brand if not generic else re.split(r",", x["address"])[0])[:28].strip("-")
        k = 2
        while slug in used:
            slug = f"{slug}-{k}"; k += 1
        used.add(slug)
        rub = " ".join(x.get("rubrics") or []) + " " + x["name"]
        ps_club = bool(re.search(r"видеоигр|приставок|playstation|ps ?\d|плейстейш", rub, re.I)) and not re.search(r"компьютерн", rub, re.I)
        phones = x["contacts"].get("phone", [])
        mob = [p for p in phones if re.sub(r"\D", "", p)[1:2] == "9"]
        phone = (mob or phones)[0]
        wa = [re.sub(r"\D", "", w) for w in x["contacts"].get("whatsapp", [])] + (x.get("ya_wa") or [])
        tgs = [re.sub(r"https?://t\.me/", "", t) for t in x["contacts"].get("telegram", [])] + (x.get("ya_tg") or [])
        msg = f"https://t.me/{tgs[0]}" if tgs else (f"https://wa.me/{wa[0]}" if wa else "")
        pr = ya_prices(x["ya_url"]) if x.get("ya_url") else []
        svc = pick(pr)
        demo = len(svc) < 3
        if demo:
            svc = jitter(DEMO_PS if ps_club else DEMO_PC, slug)
        time.sleep(0.4)
        theme = THEMES[i % len(THEMES)]
        acc, ink = color(theme, count[theme])
        count[theme] += 1
        pool = [n for n in POOL[theme] if n not in used_ph]
        if pool:
            n = pool[int(hashlib.md5(slug.encode()).hexdigest()[:6], 16) % len(pool)]
            used_ph.add(n)
            (ROOT / "clients" / "photos").mkdir(exist_ok=True)
            shutil.copy(HERE / "unsplash_games" / f"{ORDER[n]}.jpg", ROOT / "clients" / "photos" / f"{slug}.jpg")
        words = [w for w in re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", title) if w.lower() not in ("клуб", "на", "в", "club", "game", "games") and len(w) > 1]
        short = ((words[0][:1] + (words[1][:1] if len(words) > 1 else "")) if words else "К").upper()
        district = x["adm"][-1] if x.get("adm") else ""
        kind_txt = "PlayStation 5" if ps_club else "Компьютерный клуб"
        batch.append({
            "slug": slug, "name": title, "short": short, "city": "Москва", "addr": x["address"], "phone": phone, "msg": msg,
            "theme": theme, "accent": acc, "ink": ink, "kicker": KICK[theme] if theme != "hud" or not ps_club else "Игровой клуб",
            "tag": kind_txt + (" · " + district if district else ""),
            "hours": fix_hours(hours(x.get("schedule"))), "boxes": 4 if ps_club else 8, "boxLabel": "Зона" if ps_club else "Место",
            "kind": "club", "demo": demo, "svc": svc,
            "rating": x["rating"], "reviews": x["reviews"], "source": "Яндекс Карты" if (x.get("ya_reviews") or 0) >= x["gis_reviews"] else "2ГИС",
            "tg": "", "tgn": "", "_tg_cand": sorted(set(tgs)), "_wa": sorted(set(wa)), "_gis": x["id"], "_ya": x.get("ya_url"), "_prices": len(pr),
            "_branches": x.get("branches"),
        })
        print(f'{slug:32} {title[:30]:30} {theme:8} {"PS" if ps_club else "PC"} цены:{"примерные" if demo else len(svc)} {msg}', flush=True)
    (ROOT / "batches").mkdir(exist_ok=True)
    (ROOT / "batches" / f"{name}.json").write_text(json.dumps(batch, ensure_ascii=False, indent=1), encoding="utf-8")
    print("партия:", len(batch), {t: count[t] for t in THEMES})


if __name__ == "__main__":
    main()

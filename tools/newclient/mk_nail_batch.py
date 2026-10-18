"""Партия маникюрных студий из nails-found.json -> batches/<имя>.json (формат mkclients.py).
    python tools/newclient/mk_nail_batch.py moscow-nails-2026-10-18 [сколько]
Цены — с вкладки «Цены» Яндекс Карт (если есть), иначе примерные (demo). Часы — из 2ГИС."""
import json, re, sys, time
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from mk_tire_batch import get, translit, hours, street_name, ya_prices

THEMES = ["atelier", "lacquer", "sticker", "stitch", "protocol"]  # race и aqua — «гаражные» и «водные», не для салона
COLORS = [("#e11d74", "#ffffff"), ("#c084fc", "#1d0b2e"), ("#f472b6", "#2a0616"), ("#b45309", "#ffffff"), ("#be123c", "#ffffff"),
          ("#d4a373", "#1f1408"), ("#7c3aed", "#ffffff"), ("#fb7185", "#2a0710"), ("#0d9488", "#ffffff"), ("#a16207", "#ffffff")]
DEMO = [["mani", "Маникюр без покрытия", 1300, 60, "классический или аппаратный"],
        ["gel", "Маникюр с покрытием гель-лак", 2300, 120, "с укреплением и снятием"],
        ["pedi", "Педикюр с покрытием гель-лак", 2900, 120, None],
        ["ext", "Наращивание ногтей", 3500, 150, "любая длина и форма", "от"],
        ["design", "Дизайн", 100, 15, "за 1 ноготь", "от"],
        ["remove", "Снятие покрытия", 400, 20, None]]
NOT = r"детск|мужск|ресниц|бров|дополнит|1 ногт|1 ногот|за ногт|ремонт|в 4 руки|в 6 рук|скидк|абонем|зал|\d+ лет"
RULES = [  # тип, обязательно, нельзя
    ("mani", r"маникюр", r"(?<!без )покрыт|гель|шеллак|лак|педик|наращ|дизайн|снят|спа"),
    ("gel", r"(маникюр|руки).*(покрыт|гель|шеллак)|покрыт.*гель", r"без покрыт|педик|наращ|снят(?!ием)|\(ноги\)|для ног"),
    ("pedi", r"педикюр", r"маникюр|пальчик|слайдер"),
    ("ext", r"наращ", r"снят|коррекц|дизайн"),
    ("design", r"дизайн|френч|втирк", r"наращ|маникюр|педик|сложн"),
    ("remove", r"снят.*(лак|гел|покрыт)", r"наращ|маникюр|педик|без снят|скульпт"),
    ("spa", r"парафин|спа", r"пилинг|лиц|педик|маникюр")]
MINP = {"mani": 600, "gel": 800, "pedi": 1000, "ext": 1500}
DUR = {"mani": 60, "gel": 120, "pedi": 120, "ext": 150, "design": 15, "remove": 20, "spa": 30}


def pick(pr):
    svc = []
    for kind, need, nrx in RULES:
        c = [(t, p, d) for t, p, d in pr if max(100, MINP.get(kind, 0)) <= p <= 15000 and re.search(need, t, re.I)
             and not re.search(nrx, t, re.I) and not re.search(NOT, t, re.I)]
        if c:
            t, p, d = min(c, key=lambda x: len(x[0]))
            svc.append([kind, t[:60], int(p), DUR[kind], (d or None) and d[:60]])
    return svc


def main():
    name = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 999
    found = json.loads((HERE / "nails-found.json").read_text(encoding="utf-8"))
    found = [x for x in found if not re.search(r"парикмах|hair|барбер|подолог", x["name"], re.I)]
    rank = lambda x: (0 if re.search(r"nail|нейл|маник|ногт|педик", x["name"], re.I) else 1 if re.search(r"студи", x["name"], re.I) else 2, -x["reviews"])
    found.sort(key=rank)
    used = {p.stem for p in (ROOT / "clients").glob("*.json")}
    batch = []
    for x in found:
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
        generic = re.fullmatch(r"(студия маникюра|маникюрный салон|ногтевая студия|салон красоты|студия красоты|маникюр|кабинет маникюра)", brand, re.I)
        sn = street_name(x["address"])
        title = ("Маникюр" + ("" if sn.startswith(",") else " ") + sn) if generic else brand
        slug = "nail-" + translit(brand if not generic else re.split(r",", x["address"])[0])[:28].strip("-")
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
        words = [w for w in re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", title) if w.lower() not in ("маникюр", "на", "в", "студия", "nail", "nails") and len(w) > 1 and not w[0].isdigit()]
        short = ((words[0][:1] + (words[1][:1] if len(words) > 1 else "")) if words else "М").upper()
        batch.append({
            "slug": slug, "name": title, "short": short, "city": "Москва", "addr": x["address"], "phone": phone, "msg": msg,
            "theme": THEMES[i % len(THEMES)], "accent": acc, "ink": ink,
            "tag": "Маникюр и педикюр" + (" · " + x["adm"][-1] if x.get("adm") else ""),
            "hours": hours(x.get("schedule")), "boxes": 2, "kind": "nail", "demo": demo, "svc": svc,
            "rating": x["rating"], "reviews": x["reviews"], "source": "Яндекс Карты" if (x.get("ya_reviews") or 0) >= x["gis_reviews"] else "2ГИС",
            "tg": "", "tgn": "", "_tg_cand": sorted(set(tgs)), "_wa": sorted(set(wa)), "_gis": x["id"], "_ya": x.get("ya_url"), "_prices": len(pr),
        })
        print(f'{slug:32} {title[:36]:36} цены:{"примерные" if demo else len(svc)} {msg}', flush=True)
    (ROOT / "batches").mkdir(exist_ok=True)
    (ROOT / "batches" / f"{name}.json").write_text(json.dumps(batch, ensure_ascii=False, indent=1), encoding="utf-8")
    print("партия:", len(batch))


if __name__ == "__main__":
    main()

"""Страница рассылки: 4 уточнения в Тверь + 10 Москва (первая партия) + 50 новых. Данные из clients/*.json и outreach-50.md."""
import json
import sys
import re
from pathlib import Path

ROOT = Path(r"D:\AI\tver-demo")
OUT = Path(__file__).parent / "out" / "outreach.html"  # out/ не идёт в git: там телефоны
PRICE = "Стоимость — 5 000 ₽ один раз, без абонентской платы. Если интересно, подключу за день."
BASE = "https://koky09.github.io/tver-demo/"


def digits(s):
    d = re.sub(r"\D", "", s)
    return "7" + d[1:] if d.startswith("8") and len(d) == 11 else d


items = []
# --- Тверь: полные сообщения с правильной ценой ---
TVER = [
    ("morrus", "МОРРУС", "+7 930 165-12-73", "https://t.me/morrus_official", "детейлингов", "студии",
     "На вашем сайте записаться можно только по звонку или через заявку.",
     "детейлинг-мойку, полировку, керамику или плёнку", "Часть цен там примерная, подправлю под ваш прайс."),
    ("nazar", "Nazar Detailing", "+7 996 135-63-35", "", "детейлингов", "студии",
     "У вас 5,0 на картах, но своего сайта нет и записаться можно только по телефону.",
     "мойку, тонировку или керамику", "Цены там примерные, подправлю под ваши."),
    ("expertavto", "ЭкспертАвтоТверь", "+7 905 128-57-62", "", "детейлингов", "студии",
     "У вас 4,97 на картах (88 отзывов), а записаться можно только по телефону.",
     "предпродажную подготовку, полировку или химчистку", "Цены там примерные, подправлю под ваш прайс."),
    ("oazis", "Оазис", "+7 920 053-51-08", "", "автомоек", "мойки",
     "Своего сайта у вас нет, и записаться заранее можно только по телефону.",
     "мойку, полировку или химчистку", "Цены там примерные, подправлю под ваши."),
]
for slug, name, phone, tg, kind, place, hook, what, prices in TVER:
    NL = "\n"
    text = (f"Здравствуйте! Меня зовут [Имя], я делаю онлайн-запись для {kind} Твери.{NL}{NL}"
            f"{hook} Я сделал приложение записи для вашей {place} «{name}», посмотрите:{NL}{BASE}{slug}/{NL}{NL}"
            f"Клиент сам выбирает {what} и свободное время, а программа следит, чтобы боксы не пересекались. "
            f"Новая запись сразу приходит вам в Telegram. Ссылку можно поставить в ВК, на Яндекс Карты и в 2ГИС.{NL}{NL}"
            f"{prices} {PRICE}")
    items.append(dict(group="Тверь", name=name, phone=phone, tg=tg, text=text))

# --- Москва, первая партия (сообщения были в чате) ---
first = [
    ("aquamarin", "4,8 в 2ГИС (78 оценок)", "+7 926 001-62-22", ""),
    ("ag-detail", "5,0 в 2ГИС (62 оценки)", "+7 980 435-00-01", "https://t.me/agdetail_borovka"),
    ("sammoy", "5,0 в 2ГИС (65 оценок)", "+7 985 066-12-14", ""),
    ("first-class-wash", "4,6 в 2ГИС (56 оценок)", "+7 909 621-71-11", ""),
    ("a-klin", "4,9 в 2ГИС (27 оценок)", "+7 925 445-94-22", ""),
    ("moyka-777", "5,0 в 2ГИС (24 оценки)", "+7 999 963-97-39", ""),
    ("salvador", "4,9 в 2ГИС (23 оценки)", "+7 977 445-52-25", ""),
    ("mix-moyka", "4,9 в 2ГИС (22 оценки)", "+7 968 477-77-35", ""),
    ("garage-spa", "4,5 в 2ГИС (20 оценок)", "+7 980 214-91-93", ""),
    ("gas-detailing", "5,0 в 2ГИС (12 оценок)", "+7 985 855-55-52", ""),
]
for slug, rating, phone, tg in first:
    c = json.loads((ROOT / "clients" / f"{slug}.json").read_text(encoding="utf-8"))
    det = slug in ("ag-detail", "gas-detailing")
    h24 = all(v == [0, 24] for v in c["hours"].values())
    what = "; ".join(s["name"][0].lower() + s["name"][1:] for s in c["services"][:3])
    prices = "Часть цен там примерная, подправлю под ваш прайс." if c["demoPrices"] else "Цены взял из вашего прайса в 2ГИС, меняете их сами в кабинете."
    text = (f"Здравствуйте! Меня зовут [Имя], я делаю онлайн-запись для {'детейлингов' if det else 'автомоек'} Москвы.\n\n"
            f"У вас {rating}, а записаться заранее можно только по телефону. Я сделал приложение записи для вашей {'студии' if det else 'мойки'} «{c['name']}», посмотрите:\n{BASE}{slug}/\n\n"
            f"Клиент сам выбирает услугу ({what}) и свободное время{', даже ночью' if h24 else ''}. Новая запись сразу приходит вам в Telegram. "
            f"Ссылку можно поставить в карточку на Яндекс Картах и в 2ГИС.\n\n{prices} {PRICE}")
    items.append(dict(group="Москва — первая партия", name=c["name"], phone=phone, tg=tg, text=text))

# --- 50 новых: из outreach-50.md ---
md = (ROOT / "outreach-50.md").read_text(encoding="utf-8")
group = None
for block in re.split(r"\n(?=## |### )", md):
    if block.startswith("## "):
        group = block[3:].split("\n")[0].strip()
        continue
    if not block.startswith("### "):
        continue
    head, *rest = block.split("\n")
    name, contact = head[4:].split(" — ", 1)
    quote = [l[2:] if l.startswith("> ") else "" for l in rest if l.startswith(">")]
    text = "\n".join(quote).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    phone = re.search(r"\+7[\d\s()\-‒]+\d", contact)
    slug = re.search(r"tver-demo/([a-z0-9-]+)/", text).group(1)
    cfg = json.loads((ROOT / "clients" / f"{slug}.json").read_text(encoding="utf-8"))
    tg = cfg.get("socials", {}).get("tg", "")
    tg = tg if "t.me/" in tg else ""
    tg = {"vills-ditels": "https://t.me/Willi_Media"}.get(slug, tg)  # из Яндекс Карт, 06.10.2026
    items.append(dict(group=group, name=name, phone=phone.group(0).strip() if phone else "", tg=tg, text=text))

for i, it in enumerate(items):
    it["id"] = i
    it["wa"] = digits(it["phone"]) if it["phone"] else ""
assert len(items) == 64, len(items)

html = (Path(__file__).parent / "outreach_template.html").read_text(encoding="utf-8")
OUT.write_text(html.replace("/*DATA*/[]", json.dumps(items, ensure_ascii=False)), encoding="utf-8")
from check import check_page
check_page(OUT, 64)

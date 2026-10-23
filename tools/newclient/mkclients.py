"""Создаёт clients/<slug>.json для новой партии клиентов из короткого описания.

    python tools/newclient/mkclients.py batches/<партия>.json

Файл партии — список заведений (пример: tools/newclient/example-batch.json):
    slug, name, short (1–2 буквы для логотипа), city, addr (без города), phone, msg (ссылка wa.me / t.me, можно ""),
    theme (lacquer|atelier|race|protocol|aqua|stitch|sticker), accent (#rrggbb), ink (цвет текста на accent),
    tag (подзаголовок), hours ({"default": [9, 21], "0": [10, 20]} или "24/7"), boxes, kind (wash|detail|tint|tire|nail|club|salon),
    demo (true — цены примерные, в кабинете будет подсказка), svc: [[тип, название, цена, минуты, примечание?, "от"?], ...],
    а для рассылки: rating, reviews, source ("2ГИС" или "Яндекс Карты"), tg (личный Telegram, если нашли).
Типы услуг — ключи KW ниже (wash, body, express, interior, polish, ceramic, tint, ppf ...): от типа зависят иконка и подсказки чата.
Существующие файлы не перезаписываются."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "clients"

KW = {
    "wash": ["мойка", "помыть", "мыть", "мойку", "комплекс", "комплексная"], "body": ["кузов", "кузова", "коврики"],
    "express": ["экспресс", "быстро"], "touchless": ["бесконтактная", "бесконтакт"], "detail": ["детейлинг", "детейлинг-мойка", "нано", "фазная"],
    "interior": ["химчистка", "химчистку", "салон", "салона", "чистка", "уборка"], "seats": ["сиденье", "сидений", "кресло"],
    "polish": ["полировка", "полировку", "отполировать", "царапины"], "ceramic": ["керамика", "керамику", "керамическое", "покрытие", "стекло"],
    "wax": ["воск", "воском", "кварц", "полимер"], "rain": ["антидождь", "дождь"], "engine": ["двигатель", "двигателя", "мотор", "подкапотное"],
    "under": ["днище", "днища"], "headlights": ["фары", "фар", "оптика"], "ppf": ["плёнка", "пленка", "бронирование", "антигравийная", "оклейка", "зоны"],
    "tint": ["тонировка", "тонировку", "затонировать", "полусфера"], "noise": ["шумоизоляция", "шумка", "шум"], "presale": ["предпродажная", "продажа"],
    "dent": ["вмятина", "вмятины", "пдр"], "leather": ["кожа", "кожи", "кондиционер"], "ozone": ["озон", "озонирование", "запах"], "chrome": ["антихром", "хром"],
    "glass": ["лобовое", "стекло", "скол"], "vinyl": ["винил", "цвет", "крыша"],
    "tire": ["шиномонтаж", "переобуть", "переобувка", "резина", "резину", "шины", "колёса", "колеса", "сезонная"],
    "balance": ["балансировка", "балансировку", "бьёт", "вибрация"], "storage": ["хранение", "хранить", "сезонное"],
    "repair": ["прокол", "ремонт", "заплатка", "жгут", "спустило", "порез"], "rims": ["диск", "диски", "правка", "прокатка"],
    "mani": ["маникюр", "ногти", "ноготочки", "руки", "аппаратный", "комбинированный"], "gel": ["гель-лак", "гельлак", "покрытие", "шеллак", "гель"],
    "pedi": ["педикюр", "ноги", "стопы", "пальчики"], "ext": ["наращивание", "нарастить", "длина", "коррекция", "акрил", "акригель"],
    "design": ["дизайн", "френч", "стразы", "рисунок", "втирка", "слайдер"], "remove": ["снятие", "снять"],
    "spa": ["спа", "парафин", "уход", "массаж", "увлажнение"], "brows": ["брови", "бровей", "ресницы", "ламинирование"],
    "ps": ["playstation", "плойка", "плойку", "приставка", "ps5", "ps4", "консоль", "fifa", "фифа", "mortal", "геймпад"],
    "pc": ["пк", "компьютер", "компьютеры", "cs", "кс", "dota", "дота", "валорант", "место"],
    "vip": ["vip", "вип", "комната", "кабина", "отдельная", "приватная"], "night": ["ночь", "ночной", "ночью", "до утра"],
    "party": ["день рождения", "др", "праздник", "компания", "вечеринка", "аренда зала", "весь клуб"],
    "vr": ["vr", "виртуальная", "очки", "шлем"],
    "hair": ["стрижка", "подстричь", "постричь", "стрижку", "волосы", "чёлка", "челка", "кончики"],
    "color": ["окрашивание", "покрасить", "краска", "цвет", "мелирование", "балаяж", "airtouch", "тонирование", "блонд", "седина"],
    "style": ["укладка", "причёска", "прическа", "локоны", "вечерняя", "свадебная", "плетение"],
    "care": ["уход", "кератин", "ботокс", "восстановление", "выпрямление", "ламинирование волос"],
    "face": ["косметолог", "чистка лица", "пилинг", "лицо", "массаж лица", "уход за лицом"],
}
ICON = {"wash": "bubbles", "body": "spray", "express": "drop", "touchless": "spray", "detail": "bucket", "interior": "seat", "seats": "seat",
        "polish": "spark", "ceramic": "diamond", "wax": "spark", "rain": "drop", "engine": "gear", "under": "spray", "headlights": "light",
        "ppf": "shield", "tint": "tint", "noise": "mute", "presale": "tag", "dent": "tag", "leather": "seat", "ozone": "spark", "chrome": "roller",
        "glass": "shield", "vinyl": "roller",
        "tire": "wheel", "balance": "wheel", "rims": "wheel", "repair": "gear", "storage": "stack",
        "mani": "polish", "gel": "polish", "pedi": "foot", "ext": "gem", "design": "brush", "remove": "spark", "spa": "drop", "brows": "eye",
        "ps": "pad", "pc": "monitor", "vip": "crown", "night": "moon", "party": "cake", "vr": "vr",
        "zamer": "ruler", "matte": "layers", "gloss": "layers", "satin": "layers", "fabric": "layers", "float": "lamp", "light": "lamp", "lines": "lamp",
        "hair": "scissors", "color": "palette", "style": "dryer", "care": "drop", "face": "face"}
HINTS = {
    "wash": ["Помыть машину сегодня вечером", "Сколько стоит комплекс?", "Химчистка на выходных", "Где вы находитесь?"],
    "detail": ["Полировка на следующей неделе", "Сколько стоит керамика?", "Химчистка в субботу", "Где вы находитесь?"],
    "tint": ["Тонировка завтра", "Сколько стоит плёнка на фары?", "Оклейка зон риска", "Где вы находитесь?"],
    "tire": ["Переобуться в субботу", "Сколько стоит шиномонтаж R17?", "Хранение шин на зиму", "Где вы находитесь?"],
    "nail": ["Маникюр с покрытием завтра вечером", "Сколько стоит педикюр?", "Наращивание в субботу", "Где вы находитесь?"],
    "ceiling": ["Замер в субботу", "Сколько стоит потолок в комнату 18 м²?", "Парящий потолок с подсветкой", "Где вы работаете?"],
    "salon": ["Стрижка завтра вечером", "Сколько стоит окрашивание?", "Маникюр в субботу", "Где вы находитесь?"],
    "club": ["PS5 на двоих сегодня вечером", "Сколько стоит ночь?", "День рождения в субботу", "Где вы находитесь?"],
}
BOX = {"tire": "Пост", "nail": "Мастер", "club": "Зона", "salon": "Мастер", "ceiling": "Замерщик"}
COMMENT = {"nail": ["Комментарий", "Например: к мастеру Анне, снятие + френч"],
           "ceiling": ["Адрес и что нужно", "Например: ул. Ленина 5, две комнаты, глянец"],
           "salon": ["Комментарий", "Например: к мастеру Ольге, длина до плеч"],
           "club": ["Сколько вас и во что играете", "Например: нас 4, FIFA и Mortal Kombat"]}
THEMES = {"lacquer", "atelier", "race", "protocol", "aqua", "stitch", "sticker", "neon", "arcade", "console", "hud", "synth", "versus", "blueprint", "nordic", "loft", "gloss", "sky", "marble", "botanic", "paris", "swiss", "silk", "deco"}


def fmt_phone(p):
    d = re.sub(r"\D", "", p)
    d = "7" + d[1:] if len(d) == 11 and d[0] == "8" else d
    assert len(d) == 11 and d[0] == "7", f"странный номер: {p}"
    code = d[1:4]
    return f"+7 {code} {d[4:7]}-{d[7:9]}-{d[9:]}", "+" + d


def hours(h):
    if h == "24/7":
        return {str(d): [0, 24] for d in range(7)}
    base = h.get("default")
    out = {str(d): base for d in range(7)}
    out.update({k: v for k, v in h.items() if k != "default"})  # [] или null — выходной
    return {k: v for k, v in out.items() if v}


def make(c):
    assert re.fullmatch(r"[a-z0-9-]+", c["slug"]), c["slug"]
    assert c["theme"] in THEMES, c["theme"]
    seen, svcs = {}, []
    for row in c["svc"]:
        kind, name, price, dur = row[:4]
        note = row[4] if len(row) > 4 else None
        frm = (row[5] == "от") if len(row) > 5 else True
        seen[kind] = seen.get(kind, 0) + 1
        sid = kind if seen[kind] == 1 else f"{kind}{seen[kind]}"
        o = {"id": sid, "name": name, "price": price, "priceFrom": frm, "duration": dur, "keywords": KW.get(kind, []), "iconKey": ICON.get(kind, "spark")}
        if len(row) > 6 and row[6]:
            o["unit"] = row[6]  # «/м²», «за шт.»
        if note:
            o["note"] = note
        svcs.append(o)
    phone, href = fmt_phone(c["phone"])
    addr = f"{c['city']}, {c['addr']}"
    return {"slug": c["slug"], "theme": c["theme"], "demo": False, "city": c["city"], "name": c["name"], "short": c["short"], "tagline": c["tag"],
            "address": addr, "mapQuery": c.get("map") or addr, "phone": phone, "phoneHref": href, "hours": hours(c["hours"]),
            "boxes": c["boxes"], "boxLabel": c.get("boxLabel", BOX.get(c.get("kind"), "Бокс")), "kind": c.get("kind", "wash"), "accent": c["accent"], "accentInk": c["ink"],
            "socials": {"tg": c["msg"]} if c.get("msg") else {}, "demoPrices": bool(c.get("demo")),
            "chatHints": HINTS[c.get("kind", "wash")], "services": svcs, **{k: c[k] for k in ("kicker", "ringText", "calc", "bookSvc") if c.get(k)},
            **({"commentLabel": COMMENT[c["kind"]][0], "commentPlaceholder": COMMENT[c["kind"]][1]} if c.get("kind") in COMMENT else {})}


def main():
    batch = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    for c in batch:
        p = OUT / f"{c['slug']}.json"
        if p.exists():
            print("уже есть, пропускаю:", p.name)
            continue
        p.write_text(json.dumps(make(c), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("создан:", p.name)


if __name__ == "__main__":
    main()

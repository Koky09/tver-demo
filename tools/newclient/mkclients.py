"""Создаёт clients/<slug>.json для новой партии клиентов из короткого описания.

    python tools/newclient/mkclients.py batches/<партия>.json

Файл партии — список заведений (пример: tools/newclient/example-batch.json):
    slug, name, short (1–2 буквы для логотипа), city, addr (без города), phone, msg (ссылка wa.me / t.me, можно ""),
    theme (lacquer|atelier|race|protocol|aqua|stitch|sticker), accent (#rrggbb), ink (цвет текста на accent),
    tag (подзаголовок), hours ({"default": [9, 21], "0": [10, 20]} или "24/7"), boxes, kind (wash|detail|tint|tire),
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
}
ICON = {"wash": "bubbles", "body": "spray", "express": "drop", "touchless": "spray", "detail": "bucket", "interior": "seat", "seats": "seat",
        "polish": "spark", "ceramic": "diamond", "wax": "spark", "rain": "drop", "engine": "gear", "under": "spray", "headlights": "light",
        "ppf": "shield", "tint": "tint", "noise": "mute", "presale": "tag", "dent": "tag", "leather": "seat", "ozone": "spark", "chrome": "roller",
        "glass": "shield", "vinyl": "roller",
        "tire": "wheel", "balance": "wheel", "rims": "wheel", "repair": "gear", "storage": "stack"}
HINTS = {
    "wash": ["Помыть машину сегодня вечером", "Сколько стоит комплекс?", "Химчистка на выходных", "Где вы находитесь?"],
    "detail": ["Полировка на следующей неделе", "Сколько стоит керамика?", "Химчистка в субботу", "Где вы находитесь?"],
    "tint": ["Тонировка завтра", "Сколько стоит плёнка на фары?", "Оклейка зон риска", "Где вы находитесь?"],
    "tire": ["Переобуться в субботу", "Сколько стоит шиномонтаж R17?", "Хранение шин на зиму", "Где вы находитесь?"],
}
THEMES = {"lacquer", "atelier", "race", "protocol", "aqua", "stitch", "sticker"}


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
        if note:
            o["note"] = note
        svcs.append(o)
    phone, href = fmt_phone(c["phone"])
    addr = f"{c['city']}, {c['addr']}"
    return {"slug": c["slug"], "theme": c["theme"], "demo": False, "city": c["city"], "name": c["name"], "short": c["short"], "tagline": c["tag"],
            "address": addr, "mapQuery": c.get("map") or addr, "phone": phone, "phoneHref": href, "hours": hours(c["hours"]),
            "boxes": c["boxes"], "boxLabel": c.get("boxLabel", "Пост" if c.get("kind") == "tire" else "Бокс"), "accent": c["accent"], "accentInk": c["ink"],
            "socials": {"tg": c["msg"]} if c.get("msg") else {}, "demoPrices": bool(c.get("demo")),
            "chatHints": HINTS[c.get("kind", "wash")], "services": svcs}


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

"""Страница рассылки для новой партии клиентов (навык new-client).

    python tools/outreach/mkbatch.py batches/<партия>.json "Казань, мойки"

Берёт файл партии (см. tools/newclient/mkclients.py) и готовые clients/<slug>.json, пишет сообщения
и собирает out/<партия>.html со страницей как у «Рассылки владельцам»: кнопки WhatsApp и Telegram, копирование, галочки.
Галочки хранятся в браузере с префиксом партии, поэтому не путаются с другими страницами."""
import json
import re
import sys
from pathlib import Path

from check import check_page

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
BASE = "https://koky09.github.io/tver-demo/"
PRICE = "Стоимость — 3 500 ₽ один раз, без абонентской платы. Если интересно, подключу за день."
DET = {"detail", "polish", "ceramic", "ppf", "tint", "noise", "presale"}


def word(n):
    return "оценка" if n % 10 == 1 and n % 100 != 11 else "оценки" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else "оценок"


def city_gen(city):  # «для автомоек Казани»; для редких городов в партии можно указать "city_gen"
    special = {"Москва": "Москвы", "Тверь": "Твери", "Пермь": "Перми", "Казань": "Казани", "Рязань": "Рязани", "Тюмень": "Тюмени",
               "Нижний Новгород": "Нижнего Новгорода", "Великий Новгород": "Великого Новгорода", "Набережные Челны": "Набережных Челнов"}
    if city in special:
        return special[city]
    if city.endswith("а"):
        return city[:-1] + "ы"
    if city.endswith(("г", "к", "х")) or city.endswith("ск") or city[-1] in "бвдзжлмнпрстфш":
        return city + "а"
    return city


def text(c, b):
    kinds = {s["id"].rstrip("0123456789") for s in c["services"]}
    det = b.get("kind") in ("detail", "tint") or len(kinds & DET) >= 3
    h24 = all(v == [0, 24] for v in c["hours"].values()) and len(c["hours"]) == 7
    what = "; ".join(s["name"][0].lower() + s["name"][1:] for s in c["services"][:3])
    src = b.get("source", "2ГИС")
    where = "в 2ГИС" if src == "2ГИС" else "на Яндекс Картах"
    if b.get("rating"):
        n = int(b.get("reviews", 0))
        hook = f"У вас {str(b['rating']).replace('.', ',')} {where}" + (f" ({n} {word(n)})" if n else "") + ", а записаться заранее можно только по телефону."
    else:
        hook = "Своего сайта у вас нет, и записаться заранее можно только по телефону."
    night = ", даже ночью" if h24 else ", даже когда вы заняты и не берёте трубку"
    boxes = "программа следит, чтобы посты не пересекались" if c["boxes"] > 1 else "занятое время сразу закрывается"
    prices = ("Часть цен там примерная, подправлю под ваш прайс." if c["demoPrices"]
              else f"Цены взял из вашего прайса {where}, меняете их сами в кабинете.")
    place = "студии" if det else "мойки"
    return (f"Здравствуйте! Меня зовут [Имя], я делаю онлайн-запись для {'детейлингов' if det else 'автомоек'} {b.get('city_gen') or city_gen(c['city'])}.\n\n"
            f"{hook} Я сделал приложение записи для вашей {place} «{c['name']}», посмотрите:\n{BASE}{c['slug']}/\n\n"
            f"Клиент сам выбирает услугу ({what}) и свободное время{night}, а {boxes}. Новая запись сразу приходит вам в Telegram. "
            f"Ссылку можно поставить в карточку на Яндекс Картах и в 2ГИС.\n\n{prices} {PRICE}")


def main():
    src, title = Path(sys.argv[1]), sys.argv[2]
    batch = json.loads(src.read_text(encoding="utf-8"))
    items = []
    for i, b in enumerate(batch):
        c = json.loads((ROOT / "clients" / f"{b['slug']}.json").read_text(encoding="utf-8"))
        d = re.sub(r"\D", "", c["phoneHref"])
        tg = b.get("tg", "")
        tg = tg if tg.startswith("https://t.me/") else (f"https://t.me/{tg.lstrip('@')}" if tg else "")
        items.append(dict(id=i, group=c["city"], name=c["name"], phone=c["phone"], tg=tg, text=text(c, b),
                          wa=d if d[1] == "9" else "", tgn=b.get("tgn", "")))
    key = re.sub(r"[^a-z0-9-]", "", src.stem.lower()) or "batch"
    html = (HERE / "outreach_template.html").read_text(encoding="utf-8")
    html = html.replace("<title>Рассылка владельцам</title>", f"<title>Рассылка: {title}</title>").replace("<h1>Рассылка владельцам</h1>", f"<h1>Рассылка: {title}</h1>")
    html = html.replace("localStorage.getItem(k)", f"localStorage.getItem('{key}-' + k)").replace("localStorage.setItem(k,", f"localStorage.setItem('{key}-' + k,")
    html = html.replace('<span class="phone">${esc(it.phone)}</span></div>',
                        '<span class="phone">${esc(it.phone)}</span></div>${it.tgn ? `<div class="phone">Telegram: ${esc(it.tgn)}</div>` : ""}')
    out = HERE / "out" / f"{key}.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(html.replace("/*DATA*/[]", json.dumps(items, ensure_ascii=False)), encoding="utf-8")
    check_page(out, len(batch))
    print(out)


if __name__ == "__main__":
    main()

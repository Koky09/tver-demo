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
PRICE = "Стоимость — 5 000 ₽ один раз, без абонентской платы. Если интересно, подключу за день."
DET = {"detail", "polish", "ceramic", "ppf", "tint", "noise", "presale"}


def word(n):
    return "оценка" if n % 10 == 1 and n % 100 != 11 else "оценки" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else "оценок"


def city_gen(city):  # «для автомоек Казани»; для редких городов в партии можно указать "city_gen"
    special = {"Москва": "Москвы", "Тверь": "Твери", "Пермь": "Перми", "Казань": "Казани", "Рязань": "Рязани", "Тюмень": "Тюмени",
               "Нижний Новгород": "Нижнего Новгорода", "Ростов-на-Дону": "Ростова-на-Дону", "Санкт-Петербург": "Санкт-Петербурга", "Великий Новгород": "Великого Новгорода", "Набережные Челны": "Набережных Челнов"}
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
    if b.get("kind") == "tire":   # у шиномонтажа перечисляем виды работ, а не размеры колёс
        W = {"tire": "переобувка", "balance": "балансировка", "repair": "ремонт прокола", "storage": "хранение шин", "rims": "правка дисков"}
        what = ", ".join(dict.fromkeys(W[s["id"].rstrip("0123456789")] for s in c["services"] if s["id"].rstrip("0123456789") in W))
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
    if b.get("kind") == "nail":   # салон: коротко, про окошки и неявки, без «боксов»
        return (f"Здравствуйте! Меня зовут Роман, я делаю онлайн-запись для мастеров маникюра {b.get('city_gen') or city_gen(c['city'])}.\n\n"
                f"{hook.replace('по телефону', 'по телефону или в переписке')} Я сделал для «{c['name']}» страницу записи (видео на 25 секунд прикладываю), посмотрите:\n{BASE}{c['slug']}/\n\n"
                f"Клиентка сама выбирает услугу и свободное окошко у мастера в любое время, даже когда вы с клиентом и не можете ответить. "
                f"Запись сразу приходит вам в Telegram. Ссылку можно поставить в шапку ВК и Instagram, на Яндекс Карты и в 2ГИС.\n\n{prices} Фото на странице для примера — заменю на ваши работы. {PRICE}")
    if b.get("kind") == "sauna":   # бани и сауны: коротко, сайт с их настоящими фото и бронью
        n = int(b.get("reviews") or 0)
        h = (f"У вас {str(b['rating']).replace('.', ',')} {where} ({n} {word(n)}), а забронировать можно только по телефону."
             if b.get("rating") and n else "Своего сайта у вас нет, забронировать можно только по телефону.")
        return (f"Здравствуйте! Меня зовут Роман. {h}\n\n"
                f"Я сделал для «{c['name']}» сайт с онлайн-бронью и вашими фото (видео 30 секунд прикладываю):\n{BASE}{c['slug']}/\n\n"
                f"Гость сам выбирает зал и время в любой момент — бронь сразу приходит вам в Telegram. Цены там примерные, поставлю ваши.\n\n"
                f"Стоимость — 5 000 ₽ один раз, без абонентской платы.")
    if b.get("kind") == "ceiling":   # натяжные потолки: калькулятор и бесплатный замер, заявки в Telegram
        n = int(b.get("reviews") or 0)
        h = (f"У вас {str(b['rating']).replace('.', ',')} {where} ({n} {word(n)}), но своего сайта нет — клиент видит только телефон."
             if b.get("rating") and n else "Своего сайта у вас нет — клиент на картах видит только телефон.")
        return (f"Здравствуйте! Меня зовут Роман, я делаю сайты для мастеров натяжных потолков {b.get('city_gen') or city_gen(c['city'])}.\n\n"
                f"{h} Я сделал для «{c['name']}» сайт с калькулятором (видео на 30 секунд прикладываю), посмотрите:\n{BASE}{c['slug']}/\n\n"
                f"Клиент сам считает примерную цену своей комнаты и записывается на бесплатный замер в удобный день — заявка сразу приходит вам в Telegram. "
                f"Ссылку можно поставить на Авито, в ВК, на Яндекс Карты и в 2ГИС.\n\n"
                f"Цены там примерные — подставлю ваши. Фото для примера — заменю на ваши работы. {PRICE}")
    if b.get("kind") == "salon":   # салон красоты: как у маникюра, но про всех мастеров
        return (f"Здравствуйте! Меня зовут Роман, я делаю онлайн-запись для салонов красоты {b.get('city_gen') or city_gen(c['city'])}.\n\n"
                f"{hook.replace('по телефону', 'по телефону или в переписке')} Я сделал для «{c['name']}» страницу записи (видео на 25 секунд прикладываю), посмотрите:\n{BASE}{c['slug']}/\n\n"
                f"Клиентка сама выбирает услугу и свободное время у мастера — днём и ночью, даже когда все заняты и трубку взять некому. "
                f"Запись сразу приходит вам в Telegram. Ссылку можно поставить в шапку ВК и Instagram, на Яндекс Карты и в 2ГИС.\n\n{prices} Фото на странице для примера — заменю на ваши работы. {PRICE}")
    if b.get("kind") == "club":   # игровой клуб: бронь места/приставки на время, ребята пишут поздно вечером
        what = "приставку или место" if c.get("boxLabel") == "Зона" else "место"
        return (f"Здравствуйте! Меня зовут Роман, я делаю онлайн-бронь для игровых клубов {b.get('city_gen') or city_gen(c['city'])}.\n\n"
                f"{hook.replace('записаться заранее', 'забронировать заранее').replace('по телефону', 'по телефону или в переписке')} "
                f"Я сделал для «{c['name']}» страницу брони (видео на 25 секунд прикладываю), посмотрите:\n{BASE}{c['slug']}/\n\n"
                f"Гость сам выбирает {what}, время и сколько часов играть — даже ночью, когда админ занят или спит. "
                f"Бронь сразу приходит вам в Telegram, занятое время закрывается само. Ссылку можно поставить в ВК, Telegram-канал, на Яндекс Карты и в 2ГИС.\n\n"
                f"{prices} Фото на странице для примера — заменю на ваши. {PRICE}")
    tire = b.get("kind") == "tire"
    place ="вашего шиномонтажа" if tire else "вашей студии" if det else "вашей мойки"
    who = "шиномонтажей" if tire else "детейлингов" if det else "автомоек"
    season = (" Сейчас сезон переобувки: клиенты могут сами занять время, а мастерам не придётся отвлекаться на звонки."
              if tire else "")
    return (f"Здравствуйте! Меня зовут [Имя], я делаю онлайн-запись для {who} {b.get('city_gen') or city_gen(c['city'])}.\n\n"
            f"{hook}{season} Я сделал приложение записи для {place} «{c['name']}», посмотрите:\n{BASE}{c['slug']}/\n\n"
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
        tgn = b.get("tgn", "")
        if not tg and d[1] == "9":
            # чат по номеру: t.me/+79991234567 открывает Telegram, если номер там есть и не скрыт
            tg, tgn = f"https://t.me/+{d}", f"проверьте: чат по номеру +{d} (не открылся — значит Telegram нет)"
        items.append(dict(id=i, group=c["city"], name=c["name"], phone=c["phone"], tg=tg, text=text(c, b),
                          wa=d if d[1] == "9" else "", tgn=tgn, pre=bool(b.get("sent")),
                          video=f"{BASE}v/{b['slug']}.mp4" if (ROOT / "docs" / "v" / f"{b['slug']}.mp4").exists() else ""))
    key = re.sub(r"[^a-z0-9-]", "", src.stem.lower()) or "batch"
    html = (HERE / "outreach_template.html").read_text(encoding="utf-8")
    html = html.replace("<title>Рассылка владельцам</title>", f"<title>Рассылка: {title}</title>").replace("<h1>Рассылка владельцам</h1>", f"<h1>Рассылка: {title}</h1>")
    html = html.replace("localStorage.getItem(k)", f"localStorage.getItem('{key}-' + k)").replace("localStorage.setItem(k,", f"localStorage.setItem('{key}-' + k,")
    # "sent": true в партии — уже написали: отмечено «Отправил» по умолчанию; снятая галочка хранится как 0
    html = html.replace("let sent = LS.get('sent', {});", "let sent = LS.get('sent', {}); DATA.forEach((d) => { if (d.pre && !(d.id in sent)) sent[d.id] = 1; });")
    html = html.replace("else delete sent[d.dataset.done];", "else sent[d.dataset.done] = 0;")
    html = html.replace('<span class="phone">${esc(it.phone)}</span></div>',
                        '<span class="phone">${esc(it.phone)}</span></div>${it.tgn ? `<div class="phone">Telegram: ${esc(it.tgn)}</div>` : ""}')
    out = HERE / "out" / f"{key}.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(html.replace("/*DATA*/[]", json.dumps(items, ensure_ascii=False)), encoding="utf-8")
    check_page(out, len(batch))
    print(out)


if __name__ == "__main__":
    main()

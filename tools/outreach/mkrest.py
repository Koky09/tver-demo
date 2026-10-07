"""Страница рассылки 50 ресторанам: данные из sites-restaurants/sites/CLIENTS.md и самих сайтов."""
import json
import re
from pathlib import Path

ROOT = Path(r"D:\AI\sites-restaurants")
HERE = Path(__file__).parent
BASE = "https://koky09.github.io/sites-restaurants/sites/"
PRICE = "Стоимость — 3 500 ₽ один раз, без абонентской платы. Если интересно, подключу за день."
# Telegram из 2ГИС, Яндекс Карт и описаний каналов (06.10.2026). Ссылка tg — куда можно написать лично; tgn — подсказка.
TG = {
    "bali": ("made_in_bali07", "аккаунт заведения @made_in_bali07"),
    "zag": ("", "только канал @bar_zag_zag, пишите на номер"),
    "esterum": ("baresterum", "аккаунт @baresterum"),
    "chago": ("", "только канал @chagobar, пишите на номер"),
    "peys": ("+79850055969", "второй номер из их канала @pace_community: +7 985 005-59-69"),
    "arma": ("", "только канал @armacraftpub"),
    "evina": ("timofej0", "Тимофей @timofej0 — указан в их канале"),
    "rybi": ("nofishrest_ru", "аккаунт ресторана @nofishrest_ru; номер тоже есть в Telegram"),
    "max": ("maxbeefmsk", "аккаунт @maxbeefmsk"),
    "eks": ("", "Telegram не нашёлся"),
    "bebe": ("+79854357777", "номер есть в Telegram"),
    "shokunin": ("", "только канал @Shokunin_msk, пишите на номер"),
    "vova": ("AYNBAR_bot", "бот брони @AYNBAR_bot; канал @vova_s_bar"),
    "teburasi": ("+79691254000", "номер указан как Telegram"),
    "nashe": ("nashewine", "аккаунт @nashewine"),
    "uye_bar": ("yebronimsk", "аккаунт брони @yebronimsk"),
    "lado": ("ladohost", "хостес @ladohost"),
    "buddy_bar": ("", "только канал @buddybarrrrrr, пишите на номер"),
    "kokteylnaya": ("", "только канал @bar_cocktailnaya, пишите на номер"),
    "aksiom_pab": ("", "только канал @axiompub_msk, пишите на номер"),
    "volga": ("stanis_the_1st", "Станислав @stanis_the_1st — указан в их канале; номер тоже в Telegram"),
    "na_kovyor": ("bar_nakover", "аккаунт бара @bar_nakover; бот брони @koverkover_bot"),
    "zolotoy_kolos": ("", "только канал @zolotkolos"),
    "ya_won": ("", "только канал @yawonmsk"),
    "udacha": ("bk_udacha", "аккаунт @bk_udacha; номер тоже в Telegram"),
    "tak_sebe_lyudi": ("+79254310628", "номер из их канала @taksebebar: +7 925 431-06-28"),
    "perelyotny_kabak": ("flying_inn_pub", "только чат гостей @flying_inn_pub"),
    "kharddey": ("hdbmanage", "менеджер @hdbmanage — указан в канале, профиль скрыт"),
    "kamin": ("", "только канал @kaminkaminich, пишите на номер"),
    "ryumochnaya_kulturno_korotko": ("+79623473406", "второй номер из их канала: +7 962 347-34-06"),
    "hava_bar_kukhnya": ("daniel_h1lls", "Daniel @daniel_h1lls — указан в их канале"),
    "nuar": ("", "Telegram не нашёлся, есть ВК vk.com/tridrugabisness"),
    "yellowfin_by_bluefin": ("", "только канал @YellowfinZilArt"),
    "bravis": ("", "только канал @bravisrest, пишите на номер"),
    "son_krasnoy_pandy": ("", "Telegram не нашёлся; второй WhatsApp +7 925 780-77-37"),
    "zhasmin_belyayevo": ("", "только канал @jasminbelyaevo"),
    "pono_place": ("+79303333397", "номер есть в Telegram"),
    "pro_khinkali_by_novikov": ("", "Telegram не нашёлся; второй WhatsApp +7 968 693-13-33"),
    "makotse": ("+79688280909", "номер есть в Telegram"),
    "motyga": ("", "только канал @mo_yeti, пишите на номер"),
    "6_pm_bread_kitchen": ("sixpmbk", "аккаунт @sixpmbk"),
    "piu_piu": ("+79151499884", "номер есть в Telegram; второй +7 926 282-95-35"),
    "terra_mare": ("", "только канал @TerraMarreRestaurant, пишите на номер"),
    "portovino": ("", "только канал @portovinorestaurant"),
    "bokal": ("+79999890485", "второй номер в Telegram: +7 999 989-04-85"),
    "syrvin": ("sirvinrest_bot", "бот @sirvinrest_bot; WhatsApp +7 977 910-32-88"),
    "nyuans": ("", "только канал @nuance_oh_lala, пишите на номер"),
    "big_easy_bar": ("", "только канал @BigEasyMoscow"),
    "sadu": ("+79686375477", "второй номер в Telegram: +7 968 637-54-77"),
    "serb_ya": ("", "Telegram не нашёлся"),
}
NOTES = {"rybi": "может входить в ресторанную группу", "eks": "может входить в ресторанную группу", "teburasi": "может входить в ресторанную группу"}

items = []
group = None
for line in (ROOT / "sites" / "CLIENTS.md").read_text(encoding="utf-8").splitlines():
    if line.startswith("## Набор"):
        group = "Набор " + line.split("Набор", 1)[1].split("(")[0].strip()
        continue
    m = re.match(r"\| ([a-z0-9_]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| [^|]+ \|(?: ([^|]*) \|)?", line)
    if not m or m[1] == "Папка":
        continue
    key, name, kind, addr, phone, note = m[1], m[2].strip(), m[3].strip(), m[4].strip(), m[5].strip(), (m[6] or "").strip()
    page = (ROOT / "sites" / key / "index.html").read_text(encoding="utf-8")
    r = re.search(r"([\d],\d)\s*·\s*([\d\s ]+)\s*оцен", page)
    if r:
        n = int(re.sub(r"\D", "", r[2]))
        w = "оценка" if n % 10 == 1 and n % 100 != 11 else "оценки" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else "оценок"
    rating = f"{r[1]} на Яндекс Картах ({r[2].strip()} {w})" if r else ""
    kind_l = kind.split("(")[0].strip().lower()
    place = "бара" if "бар" in kind_l and "ресторан" not in kind_l else "ресторана" if "ресторан" in kind_l else "заведения"
    hook = (f"У «{name}» {rating}, но своего сайта нет и стол можно забронировать только звонком." if rating
            else f"У «{name}» нет своего сайта, и стол можно забронировать только звонком.")
    text = ("Здравствуйте! Меня зовут [Имя], я делаю сайты с онлайн-бронью для ресторанов и баров Москвы.\n\n"
            f"{hook} Я сделал для вашего {place} сайт-приложение с меню и онлайн-бронью, посмотрите:\n{BASE}{key}/\n\n"
            "Гость сам выбирает дату, время и число гостей, а заявка сразу приходит вам в Telegram. "
            "Сайт ставится на телефон как приложение — со своей иконкой в стиле заведения. "
            "А у вас есть кабинет, где видны все брони по дням, с телефонами гостей, и любую можно отменить.\n\n"
            "Меню, фото и часы работы я взял из вашей карточки на Яндекс Картах, заменю на ваши.\n\n" + PRICE)
    d = re.sub(r"\D", "", phone)
    wa = "7" + d[1:] if len(d) == 11 and d[1] == "9" else ""
    note = note or NOTES.get(key, "")
    tg, tgn = TG[key]
    tg = f"https://t.me/{tg}" if tg else ""
    items.append(dict(group=group, name=name + (f" — {note}" if note else ""), phone=phone, tg=tg, tgn=tgn, text=text, wa=wa))

for i, it in enumerate(items):
    it["id"] = i
assert len(items) == 50, len(items)
html = (HERE / "outreach_template.html").read_text(encoding="utf-8")
html = html.replace("<title>Рассылка владельцам</title>", "<title>Рассылка ресторанам</title>").replace("<h1>Рассылка владельцам</h1>", "<h1>Рассылка ресторанам</h1>")
html = html.replace('<span class="phone">${esc(it.phone)}</span></div>', '<span class="phone">${esc(it.phone)}</span></div>${it.tgn ? `<div class="phone">Telegram: ${esc(it.tgn)}</div>` : ""}')
html = html.replace("localStorage.getItem(k)", "localStorage.getItem('r-' + k)").replace("localStorage.setItem(k,", "localStorage.setItem('r-' + k,")
OUT = HERE / "out" / "outreach-rest.html"  # out/ не идёт в git: там телефоны
OUT.write_text(html.replace("/*DATA*/[]", json.dumps(items, ensure_ascii=False)), encoding="utf-8")
from check import check_page
check_page(OUT, 50)

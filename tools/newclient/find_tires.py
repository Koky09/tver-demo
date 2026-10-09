"""Поиск шиномонтажей в Москве для новой партии.
    python tools/newclient/find_tires.py            -> tools/newclient/tires-found.json
Берём: рубрика «Шиномонтаж», одна точка (не сеть), без своего сайта (соцсети и визитки 2ГИС можно),
рейтинг от 4,5, отзывов от MIN_REVIEWS, последний отзыв не старше полугода. Уже сделанные slug/телефоны пропускаем."""
import json, re, sys, time, datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gis import search, firm, reviews

ROOT = Path(__file__).resolve().parents[2]
MIN_REVIEWS = 50
CITY = "moscow"
AREAS = """Арбат Басманный Замоскворечье Красносельский Мещанский Пресненский Таганский Тверской Хамовники Якиманка
Аэропорт Беговой Бескудниковский Войковский Восточное Дегунино Головинский Дмитровский Западное Дегунино Коптево Левобережный
Молжаниновский Савёловский Сокол Тимирязевский Ховрино Хорошёвский Алексеевский Алтуфьевский Бабушкинский Бибирево Бутырский
Лианозово Лосиноостровский Марфино Марьина Роща Останкинский Отрадное Ростокино Свиблово Северное Медведково Южное Медведково Ярославский
Богородское Вешняки Восточное Измайлово Гольяново Ивановское Измайлово Косино-Ухтомский Метрогородок Новогиреево Новокосино Перово
Преображенское Северное Измайлово Соколиная Гора Сокольники Выхино-Жулебино Капотня Кузьминки Лефортово Люблино Марьино Некрасовка
Нижегородский Печатники Рязанский Текстильщики Южнопортовый Бирюлёво Восточное Бирюлёво Западное Братеево Даниловский Донской
Зябликово Москворечье-Сабурово Нагатино-Садовники Нагатинский Затон Нагорный Орехово-Борисово Царицыно Чертаново Академический
Гагаринский Зюзино Коньково Котловка Ломоносовский Обручевский Северное Бутово Тёплый Стан Черёмушки Южное Бутово Ясенево
Внуково Дорогомилово Крылатское Кунцево Можайский Ново-Переделкино Очаково-Матвеевское Проспект Вернадского Раменки Солнцево
Тропарёво-Никулино Филёвский Парк Фили-Давыдково Куркино Митино Покровское-Стрешнево Северное Тушино Строгино Хорошёво-Мнёвники
Щукино Южное Тушино Зеленоград Коммунарка Щербинка Новомосковский Троицк Мосрентген Сосенское Московский""".split()
QUERIES = ["шиномонтаж " + a for a in AREAS]
PAGES = 3
SITE_OK = re.compile(r"t\.me|vk\.com|vk\.cc|wa\.me|whatsapp|instagram|clients\.site|orgs\.biz|2gis|yandex|avito|ok\.ru|taplink|max\.ru", re.I)


def done_phones():
    out = set()
    for p in (ROOT / "clients").glob("*.json"):
        d = re.sub(r"\D", "", json.loads(p.read_text(encoding="utf-8")).get("phone", ""))[-10:]
        out.add(d)
    return out


def ids():
    found = {}
    def one(q):
        res = []
        for pg in range(1, PAGES + 1):
            try:
                r = search(CITY, q, pg)
            except Exception:
                break
            if not r:
                break
            res += r
            time.sleep(0.3)
        return res
    with ThreadPoolExecutor(4) as ex:
        for res in ex.map(one, QUERIES):
            for f in res:
                if re.search(r"шин|колёс|колес|tire|шиномонт", f["name"], re.I):
                    found[f["id"]] = f
    return found


def check(f):
    try:
        rv = reviews(f["id"])
        if not rv["count"] or rv["count"] < MIN_REVIEWS or (rv["rating"] or 0) < 4.5:
            return None
        last = datetime.datetime.fromisoformat(rv["last"][:19]) if rv["last"] else None
        if not last or (datetime.datetime.now() - last).days > 183:
            return None
        d = firm(CITY, f["id"])
    except Exception as e:
        return {"id": f["id"], "error": str(e)}
    if (d["branches"] or 1) > 1 or "Шиномонтаж" not in d["rubrics"]:
        return None
    sites = [w for w in d["contacts"].get("website", []) if not SITE_OK.search(w)]
    if sites:
        return None
    d.update(rv)
    return d


if __name__ == "__main__":
    cand = ids()
    print("в выдаче шиномонтажей:", len(cand), flush=True)
    phones = done_phones()
    with ThreadPoolExecutor(4) as ex:
        res = [r for r in ex.map(check, cand.values()) if r]
    good = [r for r in res if "error" not in r and not any(re.sub(r"\D", "", p)[-10:] in phones for p in r["contacts"].get("phone", []))]
    good.sort(key=lambda r: -r["count"])
    (Path(__file__).parent / "tires-found.json").write_text(json.dumps(good, ensure_ascii=False, indent=1), encoding="utf-8")
    print("подходят:", len(good), "| ошибок:", sum(1 for r in res if "error" in r))
    for r in good:
        print(f'{r["count"]:5} {r["rating"]} {r["name"][:45]:45} {r["address"]}')

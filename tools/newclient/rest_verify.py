"""Строгая проверка кандидатов из rest2-found.json: есть ли у ресторана свой сайт, о котором не знают карты.
    python tools/newclient/rest_verify.py   -> rest2-verified.json (поле own_site, сохраняется по ходу, можно продолжать)
Ищем название и город в DuckDuckGo, открываем результаты не из справочников и смотрим, есть ли на странице номер ресторана.
Номер на странице не из справочника и не из соцсети = свой сайт или страница заведения."""
import html, json, re, sys, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).parent
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36", "Accept-Language": "ru-RU,ru;q=0.9"}
SKIP = re.compile(r"2gis|yandex|google|bing\.|microsoft|vk\.|ok\.ru|t\.me|telegram|instagram|facebook|youtube|tiktok|dzen|rutube|wikipedia|tripadvisor|restoclub|zoon|afisha|"
                  r"komandirovka|putevka|otello|ostrovok|sutochno|tutu|flamp|yell\.|orgpage|spr\.ru|rusprofile|list-org|sbis|companies\.rbc|checko|cataloxy|gde\.ru|"
                  r"kudago|kuda|sobaka\.ru|the-village|tomesto|leclick|gastroguru|gorko|wedding|banket|restorate|kartarestoranov|prodoctor|nearby|mapcarta|foursquare|"
                  r"trip\.com|inyourpocket|travel|tour|journal|delivery-club|eda\.yandex|samokat|vkusvill|sber|pikabu|irecommend|otzov|tvil|booking|cian|avito|"
                  r"jsprav|ugosti|spravker|nashaspravka|guestcard|restoranivse|russiabase|cityrater|fanlife|restcafe|geometria|watsp|foodeon|vtyumeni24|chef\.ru|tur-stavropol|anovosibirsk|sochifinder|o-eda-dostavka|menuweb|didelivery_NO|"
                  r"restaurantguru|fooody|orgzz|rting|asktel|totadres|getgut|visit-|telemaps|afishi|spravkainform|dukl|kld-39|menunsk|make-eat|welcomekursk|clients\.site|orgs\.biz|onligo|"
                  r"gorodrabot|hh\.ru|superjob|rabota|menu\.|allcafe|gdeposhopit|recept|kp\.ru|mk\.ru|aif\.ru|rbc\.ru", re.I)


def get(u, timeout=20):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=timeout).read(600000).decode("utf-8", "ignore")


def d10(p):
    return re.sub(r"\D", "", p)[-10:]


def search(q):
    h = get("https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(q))
    urls = []
    for u in re.findall(r'class="result__a"[^>]*href="([^"]+)"', h):
        m = re.search(r"uddg=([^&]+)", u)
        urls.append(urllib.parse.unquote(m.group(1)) if m else html.unescape(u))
    for wait in (60, 180):   # DuckDuckGo при частых запросах отвечает пустой страницей: ждём и повторяем
        if urls:
            break
        time.sleep(wait)
        h = get("https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(q))
        urls = [urllib.parse.unquote(m) for m in re.findall(r'uddg=([^&"]+)', h)]
    return list(dict.fromkeys(urls))


def verify(x):
    time.sleep(20)   # темп для DuckDuckGo: один запрос в 20 секунд
    name = re.split(r",", x["name"])[0].strip()
    phones = [d10(p) for p in x["contacts"].get("phone", [])]
    res = {"own_site": None, "checked": [], "search_ok": False}
    try:
        urls = search(f'{name} {x["city"]} ресторан сайт')
        res["search_ok"] = bool(urls)
    except Exception as e:
        res["err"] = str(e)[:100]
        return x["id"], res
    seen = set()
    for u in urls:
        host = urllib.parse.urlparse(u).netloc.lower()
        if host in seen or SKIP.search(host):
            continue
        seen.add(host)
        res["checked"].append(host)
        if len(seen) > 6:
            break
        try:
            digits = re.sub(r"\D", "", get(u, 12))
        except Exception:
            continue
        if any(p[-7:] in digits for p in phones):
            res["own_site"] = u
            break
    return x["id"], res


if __name__ == "__main__":
    found = json.loads((HERE / "rest2-short.json").read_text(encoding="utf-8"))
    if len(sys.argv) > 1:  # проверить других: регулярка по названию в rest2-found.json
        found = [x for x in json.loads((HERE / "rest2-found.json").read_text(encoding="utf-8")) if re.search(sys.argv[1], x["name"])]
    out = HERE / "rest2-verified.json"
    done = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    # повтор: первая находка могла быть справочником или страницей-визиткой с карт, а настоящий сайт стоял ниже
    def inconclusive(v):
        return not v.get("search_ok") or (v.get("own_site") and SKIP.search(urllib.parse.urlparse(v["own_site"]).netloc)) or not v.get("own_site") and False
    todo = [x for x in found if x["id"] not in done or inconclusive(done[x["id"]])]
    print("проверить:", len(todo), flush=True)
    with ThreadPoolExecutor(1) as ex:
        for n, (i, r) in enumerate(ex.map(verify, todo), 1):
            done[i] = r
            nm = next(x["name"] for x in found if x["id"] == i)
            if r.get("own_site"):
                print("САЙТ:", nm[:34], r["own_site"][:70], flush=True)
            if n % 5 == 0:
                out.write_text(json.dumps(done, ensure_ascii=False, indent=0), encoding="utf-8")
                print(n, "из", len(todo), "сайтов:", sum(1 for v in done.values() if v.get("own_site")), "поиск не сработал:", sum(1 for v in done.values() if not v.get("search_ok")), flush=True)
    out.write_text(json.dumps(done, ensure_ascii=False, indent=0), encoding="utf-8")
    print("итого сайтов:", sum(1 for v in done.values() if v.get("own_site")), "поиск не сработал:", sum(1 for v in done.values() if not v.get("search_ok")), "из", len(done))

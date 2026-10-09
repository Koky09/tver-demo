# Контакты из карточки 2ГИС (поиск по названию в Москве)
import re, sys, json, urllib.request, urllib.parse
def get(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept-Language": "ru"})
    return urllib.request.urlopen(r, timeout=25).read().decode("utf-8", "ignore")
for q in sys.argv[1:]:
    h = get("https://2gis.ru/moscow/search/" + urllib.parse.quote(q))
    found = set(re.findall(r'"(?:type)":"(telegram|whatsapp|vkontakte|instagram|website|phone)","value":"([^"]+)"', h))
    urls = set(re.findall(r'(?:https?:)?\?/\?/(?:t\.me|wa\.me|vk\.com)\?/[A-Za-z0-9_+.\/-]+', h))
    print("==", q, "| размер", len(h))
    for f in sorted(found): print("   ", f)
    for u in sorted(urls)[:10]: print("   ", u.replace("\/", "/"))

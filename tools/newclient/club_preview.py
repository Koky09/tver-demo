"""Пробные сайты во всех 6 стилях ниши -> .preview/<ниша>test-<стиль>/ (в docs и clients ничего не остаётся).
    python tools/newclient/club_preview.py [club|salon]      снимки: club_shots.py"""
import json, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
U = ROOT / "tools" / "newclient" / "unsplash_games"
ORDER = (U / "_order.txt").read_text().split()
SVC = [["ps", "PS5 — 1 час", 300, 60, "до 4 игроков, FIFA, Mortal Kombat, GTA"], ["ps", "PS5 — 3 часа", 800, 180, "выгоднее на 100 ₽"],
       ["vip", "VIP-комната с PS5", 600, 60, "диван, телевизор 75 дюймов"], ["pc", "ПК — 1 час", 150, 60, "RTX 4070, 240 Гц"],
       ["night", "Ночной пакет", 900, 600, "с 22:00 до 8:00"], ["party", "День рождения", 3000, 180, "весь зал, до 10 человек"]]
THEMES = [("neon", "#ff2bd6", "#ffffff", 46, "Пиксель"), ("arcade", "#ff4d6d", "#ffffff", 29, "Арена Геймерс"),
          ("console", "#2f6bff", "#ffffff", 100, "Джойстик"), ("hud", "#7cff4d", "#0a0d0b", 23, "Бункер"),
          ("synth", "#8c1eff", "#ffffff", None, "Ретро Вейв"), ("versus", "#e8202a", "#ffffff", 87, "Файт Клаб")]

KIND = sys.argv[1] if len(sys.argv) > 1 else "club"
if KIND == "salon":
    U = ROOT / "tools" / "newclient" / "unsplash_salon"
    ORDER = (U / "_order.txt").read_text().split()
    SVC = [["hair", "Женская стрижка", 1200, 60, "мытьё и укладка включены", "от"], ["color", "Окрашивание", 3500, 150, "цена зависит от длины волос", "от"],
           ["style", "Укладка", 1200, 60, "локоны, объём, вечерняя", "от"], ["care", "Уход и восстановление волос", 2500, 90, "кератин, ботокс", "от"],
           ["gel", "Маникюр с покрытием гель-лак", 1600, 120, "с укреплением и снятием", "от"], ["brows", "Брови: коррекция и окрашивание", 900, 45, None, "от"]]
    THEMES = [("marble", "#a07850", "#ffffff", 19, "Белла"), ("botanic", "#5c8a5e", "#ffffff", 104, "Шалфей"), ("paris", "#c8506a", "#ffffff", 33, "Мадемуазель"),
              ("swiss", "#e2231a", "#ffffff", 91, "Форма"), ("silk", "#d98ad6", "#ffffff", 100, "Лавандовый Сад"), ("deco", "#2f7a62", "#ffffff", 136, "Гэтсби")]
EXTRA = {}
if KIND == "ceiling":
    import mk_ceil_batch as mc
    U = ROOT / "tools" / "newclient" / "unsplash_ceil"
    ORDER = (U / "_order.txt").read_text().split()
    SVC = mc.SVC
    THEMES = [("blueprint", "#1aa0e6", "#ffffff", 48, "Потолок Мастер"), ("nordic", "#a0673a", "#ffffff", 1, "Белый Лист"),
              ("loft", "#ffb020", "#1c1d1f", 104, "Лофт Лайт"), ("gloss", "#3b82f6", "#ffffff", 103, "Глянец Про"), ("sky", "#22a6e0", "#ffffff", 34, "Парящий Мир")]
    EXTRA = {"calc": mc.CALC, "bookSvc": "zamer", "kicker": "Натяжные потолки"}
batch = [{"slug": f"{KIND}test-{t}", "name": n, "short": n[0], "city": "Москва" if KIND == "club" else "Казань", "addr": "Профсоюзная улица, 56", "phone": "+79161234567", "msg": "",
          "theme": t, "accent": a, "ink": ink, "tag": {"club": "PlayStation 5 и ПК · Черёмушки", "salon": "Салон красоты · Центральный район"}.get(KIND, "Натяжные потолки под ключ · Советский район"),
          "hours": {"default": [12, 24]} if KIND == "club" else {"default": [9, 21]}, "boxes": 4 if KIND == "club" else 3, "kind": KIND,
          "demo": True, "svc": SVC, **EXTRA} for t, a, ink, ph, n in THEMES]
tmp = ROOT / "tools" / "newclient" / "_clubtest.json"
tmp.write_text(json.dumps(batch, ensure_ascii=False), encoding="utf-8")
slugs = [b["slug"] for b in batch]
try:
    subprocess.run([sys.executable, "tools/newclient/mkclients.py", str(tmp)], cwd=ROOT, check=True)
    for t, a, ink, ph, n in THEMES:
        if ph is not None:
            shutil.copy(U / f"{ORDER[ph]}.jpg", ROOT / "clients" / "photos" / f"{KIND}test-{t}.jpg")
    subprocess.run([sys.executable, "build.py", *slugs], cwd=ROOT, check=True)
    for s in slugs:
        shutil.rmtree(ROOT / ".preview" / s, ignore_errors=True)
        shutil.move(str(ROOT / "docs" / s), str(ROOT / ".preview" / s))
finally:
    tmp.unlink(missing_ok=True)
    for s in slugs:
        (ROOT / "clients" / f"{s}.json").unlink(missing_ok=True)
        (ROOT / "clients" / "photos" / f"{s}.jpg").unlink(missing_ok=True)
        shutil.rmtree(ROOT / "docs" / s, ignore_errors=True)
print("готово:", ", ".join(slugs))

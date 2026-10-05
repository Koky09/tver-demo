"""Собирает приложение записи под каждый бизнес из clients/*.json.

    python build.py            -> docs/<slug>/ для всех клиентов + docs/index.html со списком
    python build.py morrus     -> только один клиент
"""
import json
import os
import shutil
import sys
import time
from pathlib import Path

import logo

ROOT = Path(__file__).parent
TEMPLATE = ROOT / "template"
CLIENTS = ROOT / "clients"
DIST = ROOT / "docs"  # GitHub Pages публикует папку /docs
SETTINGS_FILE = ROOT / "settings.json"
SETTINGS = json.loads(SETTINGS_FILE.read_text(encoding="utf-8")) if SETTINGS_FILE.exists() else {}


# Стиль сайта (поле "theme" в clients/<slug>.json) -> шрифты Google Fonts. Все с кириллицей.
GF = "https://fonts.googleapis.com/css2?family="
THEME_FONTS = {
    "lacquer": "Onest:wght@400;500;600;700&family=Unbounded:wght@500;600;700",
    "atelier": "Cormorant+Garamond:ital,wght@0,500;0,600;0,700;1,500&family=Manrope:wght@400;500;600;700",
    "race": "Oswald:wght@500;600;700&family=Golos+Text:wght@400;500;600;700",
    "protocol": "IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600",
    "aqua": "Comfortaa:wght@600;700&family=Nunito:wght@400;500;600;700",
    "stitch": "Unbounded:wght@500;600;800&family=Onest:wght@400;500;600;700",
    "sticker": "Dela+Gothic+One&family=Rubik:wght@400;500;600;700",
}


def build(cfg_path):
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg["hours"] = {int(k): v for k, v in cfg["hours"].items()}
    # Адрес сервера записи (Google Apps Script /exec). Пусто — запись хранится в браузере (локальная проверка).
    cfg["apiUrl"] = os.environ.get("API_URL", SETTINGS.get("apiUrl", ""))
    if cfg["apiUrl"]:
        cfg.pop("adminPin", None)  # на сервере у каждого владельца свой PIN, в код сайта он не попадает
    out = DIST / cfg["slug"]
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(TEMPLATE, out)

    (out / "config.js").write_text("window.CONFIG = " + json.dumps(cfg, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    theme = cfg.get("theme", "lacquer")
    if theme not in THEME_FONTS:
        sys.exit(f"{cfg_path.name}: неизвестный theme «{theme}», есть: {', '.join(THEME_FONTS)}")
    page = out / "index.html"
    page.write_text(page.read_text(encoding="utf-8")
                    .replace("<!--THEME-->", f' data-theme="{theme}"')
                    .replace("<!--FONTS-->", f'<link rel="stylesheet" href="{GF}{THEME_FONTS[theme]}&display=swap" media="print" onload="this.media=&#39;all&#39;">'), encoding="utf-8")
    sw = out / "sw.js"
    sw.write_text(sw.read_text(encoding="utf-8").replace("__VERSION__", str(int(time.time()))), encoding="utf-8")
    manifest = {
        "name": f"{cfg['name']} — онлайн-запись",
        "short_name": cfg["name"][:12],
        "start_url": "./",
        "scope": "./",
        "display": "standalone",
        "background_color": logo.splash_color(cfg),  # заставка при запуске — под цвет логотипа
        "theme_color": logo.splash_color(cfg),
        "lang": "ru",
        "icons": [
            {"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
    }
    (out / "manifest.webmanifest").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    # Логотип сервиса: иконка на рабочий стол и эмблема в шапке (logo.py)
    logo.make_logo(cfg, 192).save(out / "icon-192.png")
    logo.make_logo(cfg, 512).save(out / "icon-512.png")
    print(f"  {cfg['slug']:<16} [{theme}] {cfg['name']}  ({len(cfg['services'])} услуг, {cfg.get('boxLabel', 'Бокс').lower()}ов: {cfg['boxes']})")
    return cfg


def main():
    only = sys.argv[1:]
    DIST.mkdir(exist_ok=True)
    (DIST / ".nojekyll").write_text("", encoding="utf-8")
    built = [build(p) for p in sorted(CLIENTS.glob("*.json")) if not only or p.stem in only]
    all_cfgs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(CLIENTS.glob("*.json"))]
    rows = "".join(
        f'<a href="{c["slug"]}/"><b>{c["name"]}</b><span>{c["tagline"]}</span></a>'
        f'<a class="adm" href="{c["slug"]}/#admin">кабинет</a>' for c in all_cfgs
    )
    (DIST / "index.html").write_text(f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Демо записи</title>
<style>body{{margin:0;background:#0f1012;color:#f2f3f5;font:16px/1.4 system-ui,sans-serif}}
main{{max-width:560px;margin:0 auto;padding:24px 16px}}h1{{font-size:22px}}
.g{{display:grid;grid-template-columns:1fr auto;gap:8px}}a{{color:inherit;text-decoration:none;background:#17191c;border:1px solid #2b2f35;border-radius:14px;padding:14px}}
a span{{display:block;color:#9aa1ab;font-size:14px}}.adm{{display:grid;place-items:center;color:#9aa1ab;font-size:14px}}</style></head>
<body><main><h1>Демо-приложения записи</h1><div class="g">{rows}</div></main></body></html>""", encoding="utf-8")
    print(f"Готово: {len(built)} шт. -> {DIST}")


if __name__ == "__main__":
    main()

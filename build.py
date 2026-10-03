"""Собирает приложение записи под каждый бизнес из clients/*.json.

    python build.py            -> docs/<slug>/ для всех клиентов + docs/index.html со списком
    python build.py morrus     -> только один клиент
"""
import json
import shutil
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent
TEMPLATE = ROOT / "template"
CLIENTS = ROOT / "clients"
DIST = ROOT / "docs"  # GitHub Pages публикует папку /docs
SETTINGS_FILE = ROOT / "settings.json"
SETTINGS = json.loads(SETTINGS_FILE.read_text(encoding="utf-8")) if SETTINGS_FILE.exists() else {}


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def font(size):
    for name in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_icon(cfg, size, path):
    img = Image.new("RGB", (size, size), hex_rgb(cfg["accent"]))
    d = ImageDraw.Draw(img)
    text = cfg["short"]
    f = font(int(size * (0.5 if len(text) == 1 else 0.38)))
    box = d.textbbox((0, 0), text, font=f)
    w, h = box[2] - box[0], box[3] - box[1]
    d.text(((size - w) / 2 - box[0], (size - h) / 2 - box[1]), text, font=f, fill=hex_rgb(cfg.get("accentInk", "#111111")))
    img.save(path)


def build(cfg_path):
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg["hours"] = {int(k): v for k, v in cfg["hours"].items()}
    cfg["notifyUrl"] = SETTINGS.get("notifyUrl", "")
    out = DIST / cfg["slug"]
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(TEMPLATE, out)

    (out / "config.js").write_text("window.CONFIG = " + json.dumps(cfg, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    sw = out / "sw.js"
    sw.write_text(sw.read_text(encoding="utf-8").replace("__VERSION__", str(int(time.time()))), encoding="utf-8")
    manifest = {
        "name": f"{cfg['name']} — онлайн-запись",
        "short_name": cfg["name"][:12],
        "start_url": "./",
        "scope": "./",
        "display": "standalone",
        "background_color": "#0f1012",
        "theme_color": "#0f1012",
        "lang": "ru",
        "icons": [
            {"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
    }
    (out / "manifest.webmanifest").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    make_icon(cfg, 192, out / "icon-192.png")
    make_icon(cfg, 512, out / "icon-512.png")
    print(f"  {cfg['slug']:<16} {cfg['name']}  ({len(cfg['services'])} услуг, {cfg.get('boxLabel', 'Бокс').lower()}ов: {cfg['boxes']})")
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

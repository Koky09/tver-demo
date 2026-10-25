"""Что реально попало на сайты (шапка + галерея), по 10 бань на лист: python tools/newclient/applied_sheet.py <партия.json> <out-префикс>"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
b = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
font = ImageFont.truetype("arial.ttf", 18)
for k in range(0, len(b), 10):
    rows = b[k:k + 10]
    sh = Image.new("RGB", (9 * 170 + 200, len(rows) * 130), "white")
    dr = ImageDraw.Draw(sh)
    for r, x in enumerate(rows):
        fs = [ROOT / "clients" / "photos" / f'{x["slug"]}.jpg'] + sorted((ROOT / "clients" / "gallery" / x["slug"]).glob("*.jpg"))
        dr.text((4, r * 130 + 50), f'{k + r + 1}. {x["slug"][6:]}', fill="black", font=font)
        for c, f in enumerate(fs[:9]):
            im = Image.open(f); im.thumbnail((165, 125))
            sh.paste(im, (200 + c * 170, r * 130))
    sh.save(f"{sys.argv[2]}-{k // 10 + 1}.jpg", quality=78)

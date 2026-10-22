"""Снимки пробных сайтов из .preview: python tools/newclient/club_shots.py <out.jpg> [slug ...]"""
import functools, http.server, sys, threading
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image
ROOT = Path(__file__).resolve().parents[2]
out = sys.argv[1]
slugs = sys.argv[2:] or [f"clubtest-{t}" for t in ("neon", "arcade", "console", "hud", "synth", "versus")]
if slugs == ["salon"]:
    slugs = [f"salontest-{t}" for t in ("marble", "botanic", "paris", "swiss", "silk", "deco")]
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8771), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / ".preview")))
threading.Thread(target=srv.serve_forever, daemon=True).start()
tops, mids = [], []
with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, locale="ru-RU", service_workers="block").new_page()
    for s in slugs:
        pg.goto(f"http://127.0.0.1:8771/{s}/", wait_until="load", timeout=60000); pg.wait_for_timeout(2500)
        tops.append(Image.open(__import__("io").BytesIO(pg.screenshot())))
        pg.mouse.wheel(0, 760); pg.wait_for_timeout(700)
        mids.append(Image.open(__import__("io").BytesIO(pg.screenshot())))
    br.close()
srv.shutdown()
ims = tops + mids
w, h = ims[0].size; n = len(slugs)
sh = Image.new("RGB", (n * (w + 20), 2 * (h + 20)), "white")
for i, im in enumerate(ims):
    sh.paste(im, ((i % n) * (w + 20), (i // n) * (h + 20)))
sh.thumbnail((3000, 3000)); sh.save(out, quality=85)

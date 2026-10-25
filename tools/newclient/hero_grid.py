"""Первые экраны сайтов сеткой (проверка глазами): python tools/newclient/hero_grid.py <партия.json> <out-префикс>"""
import functools, http.server, io, json, sys, threading
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
slugs = [x["slug"] for x in json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))]
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8778), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / "docs")))
srv.RequestHandlerClass.log_message = lambda *a: None
threading.Thread(target=srv.serve_forever, daemon=True).start()
shots = []
with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(viewport={"width": 390, "height": 760}, service_workers="block")
    pg = ctx.new_page()
    for s in slugs:
        pg.goto(f"http://127.0.0.1:8778/{s}/", wait_until="load"); pg.wait_for_selector(".svc"); pg.wait_for_timeout(700)
        shots.append(Image.open(io.BytesIO(pg.screenshot())).resize((195, 380)))
    br.close()
srv.shutdown()
for k in range(0, len(shots), 20):
    part = shots[k:k + 20]
    g = Image.new("RGB", (10 * 200, 2 * 385), "white")
    for i, im in enumerate(part):
        g.paste(im, ((i % 10) * 200, (i // 10) * 385))
    g.save(f"{sys.argv[2]}-{k // 20 + 1}.jpg", quality=82)
print("готово")

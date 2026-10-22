"""Снимок страницы целиком (телефон и компьютер): python tools/newclient/page_shot.py <папка> <out-префикс>"""
import functools, http.server, sys, threading
from playwright.sync_api import sync_playwright
d, out = sys.argv[1], sys.argv[2]
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8774), functools.partial(http.server.SimpleHTTPRequestHandler, directory=d))
threading.Thread(target=srv.serve_forever, daemon=True).start()
with sync_playwright() as p:
    br = p.chromium.launch()
    for name, vp, sc in (("mobile", {"width": 390, "height": 844}, 2), ("desktop", {"width": 1366, "height": 860}, 1)):
        pg = br.new_page(viewport=vp, device_scale_factor=sc)
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://127.0.0.1:8774/", wait_until="load", timeout=90000); pg.wait_for_timeout(3500)
        pg.evaluate("window.scrollTo(0, document.body.scrollHeight)"); pg.wait_for_timeout(1500); pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(600)
        pg.screenshot(path=f"{out}-{name}.png", full_page=True)
        print(name, "ошибки:", errs or "нет")
    br.close()
srv.shutdown()

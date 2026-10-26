"""Снимок одного сайта из docs/ (с общими файлами вроде docs/fonts): python tools/newclient/site_shot.py <slug> <out.png> [высота]"""
import functools, http.server, sys, threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8779), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / "docs")))
srv.RequestHandlerClass.log_message = lambda *a: None
threading.Thread(target=srv.serve_forever, daemon=True).start()
with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={"width": 390, "height": int(sys.argv[3]) if len(sys.argv) > 3 else 844}, device_scale_factor=2, service_workers="block")
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(f"http://127.0.0.1:8779/{sys.argv[1]}/", wait_until="load"); pg.wait_for_selector(".svc"); pg.wait_for_timeout(900)
    pg.screenshot(path=sys.argv[2], full_page=True)
    print("ошибки:", errs or "нет", "| шрифт Pricedown:", pg.evaluate("document.fonts.check('40px Pricedown')"))
    br.close()
srv.shutdown()

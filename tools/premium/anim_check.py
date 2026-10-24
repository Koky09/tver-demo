"""Проверка анимаций премиум-сайта: python tools/premium/anim_check.py extra/<папка> [out.jpg]
Снимки на 0,3–2,6 с после загрузки и после прокрутки; печатает итоговый рейтинг, видимость блоков и ошибки страницы."""
import functools, http.server, io, sys, threading
from playwright.sync_api import sync_playwright
from PIL import Image

d = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else ".preview/_anim.jpg"
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8776), functools.partial(http.server.SimpleHTTPRequestHandler, directory=d))
threading.Thread(target=srv.serve_forever, daemon=True).start()
with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={"width": 390, "height": 844})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://127.0.0.1:8776/", wait_until="domcontentloaded")
    shots, prev = [], 0
    for t in (300, 500, 700, 1200, 2600):
        pg.wait_for_timeout(t - prev); prev = t
        shots.append(Image.open(io.BytesIO(pg.screenshot())))
    print("рейтинг:", pg.inner_text(".hero .rating").replace("\n", " "))
    pg.mouse.wheel(0, 1400); pg.wait_for_timeout(250); shots.append(Image.open(io.BytesIO(pg.screenshot())))
    pg.wait_for_timeout(1400); shots.append(Image.open(io.BytesIO(pg.screenshot())))
    hidden = pg.evaluate("[...document.querySelectorAll('[data-reveal]>*')].filter(e=>e.getBoundingClientRect().top<innerHeight && getComputedStyle(e).opacity<.99).length")
    print("невидимых блоков в кадре после прокрутки:", hidden, "| ошибки:", errs or "нет")
    w, h = shots[0].size
    s = Image.new("RGB", (len(shots) * (w + 10), h), "white")
    for i, im in enumerate(shots):
        s.paste(im, (i * (w + 10), 0))
    s.thumbnail((2800, 1000)); s.save(out, quality=80)
    br.close()
srv.shutdown()

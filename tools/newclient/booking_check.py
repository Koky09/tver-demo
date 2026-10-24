"""Проверка сайтов из docs/: открывается, нет ошибок, запись проходит до талона (без сервера записи — локально).
    python tools/newclient/booking_check.py <slug> [slug ...]"""
import functools, http.server, json, re, sys, threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8777), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / "docs")))
threading.Thread(target=srv.serve_forever, daemon=True).start()
with sync_playwright() as p:
    br = p.chromium.launch()
    for slug in sys.argv[1:]:
        ctx = br.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        # без сервера записи: apiUrl пустой — запись сохраняется в браузере
        ctx.route(re.compile(r".*/config\.js.*"), lambda r: r.fulfill(response=r.fetch(), body=re.sub(r'"apiUrl":\s*"[^"]*"', '"apiUrl": ""', r.fetch().text())))
        pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"http://127.0.0.1:8777/{slug}/", wait_until="load"); pg.wait_for_selector(".svc", timeout=30000)
        pg.locator('[data-act="book"]').click(); pg.wait_for_timeout(400)
        sheet = pg.locator(".sheet")
        if sheet.locator("[data-svc]").count(): sheet.locator("[data-svc]").first.click(); pg.wait_for_timeout(300)
        days = sheet.locator("button[data-day]:not([disabled])")
        if days.count() > 1: days.nth(1).click(); pg.wait_for_timeout(300)
        sheet.locator("button").filter(has_text=re.compile(r"^\s*\d{1,2}:\d{2}\s*$")).first.click(); pg.wait_for_timeout(300)
        nxt = sheet.locator("button").filter(has_text=re.compile("Далее"))
        if nxt.count(): nxt.first.click(); pg.wait_for_timeout(300)
        pg.fill("#f-name", "Проверка"); pg.fill("#f-phone", "+79001234567")
        sheet.locator('[data-act="confirm"]').click(); pg.wait_for_timeout(800)
        ok = sheet.locator(".ok").count() > 0
        print(f"{slug:30} запись: {'прошла' if ok else 'НЕ прошла'} | ошибки: {errs or 'нет'}", flush=True)
        ctx.close()
    br.close()
srv.shutdown()

"""Короткое видео для рассылки: как клиентка записывается на сайте студии и запись приходит владельцу.
    python tools/outreach/mkvideo.py batches/<партия>.json [slug ...]   -> tools/outreach/video/<slug>.mp4
Сайт берётся с GitHub Pages, но запросы записи уходят в mock-сервер (node backend/mock-server.js, порт 8766),
чтобы не создавать настоящих записей. Подписи шагов и «уведомление в Telegram» дорисовываются поверх страницы."""
import json, re, shutil, subprocess, sys, time
from pathlib import Path
import imageio_ffmpeg
from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
OUT = HERE / "video"
BASE = "https://koky09.github.io/tver-demo/"
MOCK = "http://localhost:8766"
W, H = 390, 760

CSS = """
#vcap{position:fixed;left:12px;right:12px;top:12px;z-index:2147483647;background:rgba(17,17,20,.92);color:#fff;
 font:600 17px/1.3 -apple-system,Segoe UI,Roboto,sans-serif;padding:12px 14px;border-radius:14px;box-shadow:0 8px 24px rgba(0,0,0,.35);
 transition:opacity .35s;display:flex;gap:10px;align-items:center;pointer-events:none}
#vcap b{background:#fff;color:#111;border-radius:50%;min-width:26px;height:26px;display:inline-flex;align-items:center;justify-content:center;font-size:15px}
#vtg{position:fixed;left:10px;right:10px;top:-200px;z-index:2147483647;background:#fff;color:#111;border-radius:16px;padding:12px 14px;
 font:14px/1.35 -apple-system,Segoe UI,Roboto,sans-serif;box-shadow:0 12px 32px rgba(0,0,0,.35);transition:top .6s cubic-bezier(.2,.8,.2,1);pointer-events:none}
#vtg .h{display:flex;align-items:center;gap:8px;margin-bottom:6px;color:#555;font-size:13px}
#vtg .h i{width:22px;height:22px;border-radius:50%;background:#2aabee;display:inline-block}
#vtg .t{font-weight:700;margin-bottom:2px}
#vcur{position:fixed;width:26px;height:26px;border-radius:50%;background:rgba(255,255,255,.55);border:2px solid rgba(0,0,0,.45);
 z-index:2147483646;pointer-events:none;transform:translate(-50%,-50%);transition:left .45s,top .45s}
"""


def cap(page, n, text):
    page.evaluate("""([n,t])=>{let c=document.getElementById('vcap'); if(!c){c=document.createElement('div');c.id='vcap';document.body.appendChild(c)}
        c.style.opacity=1; c.innerHTML=(n?'<b>'+n+'</b>':'')+'<span>'+t+'</span>';}""", [n, text])


def tap(page, loc):
    loc.scroll_into_view_if_needed()
    b = loc.bounding_box()
    x, y = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
    page.evaluate("""([x,y])=>{let c=document.getElementById('vcur'); if(!c){c=document.createElement('div');c.id='vcur';document.body.appendChild(c)}
        c.style.left=x+'px'; c.style.top=y+'px';}""", [x, y])
    page.wait_for_timeout(550)
    loc.click()


def record(slug, cfg):
    tmp = OUT / f"_{slug}"
    shutil.rmtree(tmp, ignore_errors=True)
    with sync_playwright() as p:
        br = p.chromium.launch()
        # запись идёт в размере окна, поэтому окно вдвое больше, а страница увеличена zoom:2 (вёрстка как на телефоне 390 px)
        ctx = br.new_context(viewport={"width": W * 2, "height": H * 2}, device_scale_factor=1, has_touch=False,
                             record_video_dir=str(tmp), record_video_size={"width": W * 2, "height": H * 2}, locale="ru-RU")
        # config.js с живого сайта, но apiUrl -> mock: записи не попадают в настоящую таблицу
        def cfg_route(route):
            r = route.fetch()
            body = re.sub(r'"apiUrl":\s*"[^"]*"', f'"apiUrl": "{MOCK}"', r.text())
            route.fulfill(response=r, body=body)
        ctx.route(re.compile(r".*/config\.js.*"), cfg_route)
        ctx.route(re.compile(r".*/sw\.js.*"), lambda r: r.abort())
        page = ctx.new_page()
        page.add_init_script(f"document.addEventListener('DOMContentLoaded',()=>{{const s=document.createElement('style');s.textContent='html{{zoom:2}}'+{json.dumps(CSS)};document.head.appendChild(s)}})")
        page.goto(BASE + slug + "/", wait_until="load", timeout=90000)
        page.wait_for_selector(".svc", timeout=60000)   # сайт дорисовался (бывает медленно)
        page.wait_for_timeout(1200)
        page.wait_for_timeout(600)
        cap(page, 1, f"Ваш сайт «{cfg['name']}» — с вашими фото" if cfg.get("kind") == "sauna" else f"Ваша страница записи «{cfg['name']}»")
        page.wait_for_timeout(2600)
        sauna = cfg.get("kind") == "sauna"
        club = cfg.get("kind") == "club" or sauna
        guest = "Дмитрий" if sauna else "Артём" if club else "Анна"
        ceil = cfg.get("kind") == "ceiling"
        if ceil:   # потолки: клиент считает цену в калькуляторе и вызывает замерщика
            guest = "Ольга"
            cap(page, 2, "Клиент сам считает цену своей комнаты")
            page.locator("#calc").scroll_into_view_if_needed()
            page.mouse.wheel(0, 160)
            page.wait_for_timeout(900)
            for v in range(18, 23):
                page.fill("#c-area", str(v)); page.dispatch_event("#c-area", "input"); page.wait_for_timeout(120)
            tap(page, page.locator('[data-ctype="1"]'))
            page.wait_for_timeout(500)
            for _ in range(3):
                tap(page, page.locator('[data-cex="0"][data-d="1"]'))
            page.wait_for_timeout(900)
            svc = next((s for s in cfg["services"] if s["id"] == cfg.get("bookSvc")), cfg["services"][0])
            tap(page, page.locator('[data-act="zamer"]'))
            page.wait_for_timeout(1300)
            cap(page, 3, "…и вызывает замерщика на удобное время")
        else:
            cap(page, 2, "Гость выбирает зал и сколько часов" if sauna else "Гость выбирает, во что играть" if club else "Клиентка выбирает услугу")
            page.mouse.wheel(0, 380)
            page.wait_for_timeout(1400)
            svc = next((s for s in cfg["services"] if s["id"].startswith("gel")), cfg["services"][0]) if cfg.get("kind") == "nail" else cfg["services"][0]
            tap(page, page.get_by_text(svc["name"], exact=True).first)
            page.wait_for_timeout(1500)
            cap(page, 3, "…и свободное время" if club else "…и свободное окошко у мастера")
        sheet = page.locator(".sheet")
        days = sheet.locator("button:not([disabled])").filter(has_text=re.compile(r"^\s*(пн|вт|ср|чт|пт|сб|вс)\s*\d+\s*$"))
        if days.count() > 1:
            tap(page, days.nth(1))
            page.wait_for_timeout(900)
        times = sheet.locator("button").filter(has_text=re.compile(r"^\s*\d{1,2}:\d{2}\s*$"))
        k = min(3, times.count() - 1)
        tap(page, times.nth(k))
        page.wait_for_timeout(700)
        nxt = sheet.locator("button").filter(has_text=re.compile("Далее|Продолжить"))
        if nxt.count():
            tap(page, nxt.first)
        page.wait_for_timeout(900)
        cap(page, 4, "Оставляет имя и телефон — без звонков")
        ins = sheet.locator("input")
        ins.nth(0).click(); ins.nth(0).type(guest, delay=110)
        ins.nth(1).click(); ins.nth(1).type("+7 916 123-45-67", delay=60)
        page.wait_for_timeout(500)
        tap(page, sheet.get_by_role("button", name=re.compile("^(Записаться|Забронировать|Записаться на замер)$")))
        page.wait_for_timeout(1800)
        cap(page, 5, "Готово — замер назначен" if ceil else "Готово — время за ним" if sauna else "Готово — место за ним" if club else "Готово — клиентка записана")
        page.wait_for_timeout(1800)
        slot = sheet.inner_text()
        when = re.search(r"\d{1,2}:\d{2}", slot)
        day = re.search(r"(Сегодня|Завтра|[А-ЯЁа-яё]+),\s*\d+\s+[а-яё]+", slot)
        what = page.evaluate("() => (document.querySelector('#c-sum') || {}).textContent || ''") if ceil else ""
        msg = ("Заявка на замер|" if ceil else "Бронь|" if club else "Запись|") + (f"Замер: 22 м², глянец, 3 светильника — около {what}<br>" if ceil else f"Новая {'бронь' if club else 'запись'}: {svc['name']}<br>") + f"{(day.group(0) if day else 'завтра')}, {when.group(0) if when else ''} · {cfg.get('boxLabel', 'Мастер')} 1<br>{guest}, +7 916 123-45-67"
        page.evaluate("""(m)=>{const c=document.getElementById('vcap'); if(c) c.style.opacity=0;
            const t=document.createElement('div'); t.id='vtg'; t.innerHTML='<div class=h><i></i>Telegram · сейчас</div><div class=t>'+m.split('|')[0]+' в «'+document.title+'»</div>'+m.split('|')[1];
            document.body.appendChild(t); requestAnimationFrame(()=>requestAnimationFrame(()=>t.style.top='12px'));}""", msg)
        page.wait_for_timeout(900)
        cap(page, 6, "А заявка сразу приходит вам в Telegram" if ceil else "А бронь сразу приходит вам в Telegram" if club else "А запись сразу приходит вам в Telegram")
        page.evaluate("()=>{const c=document.getElementById('vcap'); const g=document.getElementById('vtg').getBoundingClientRect(); c.style.top=(g.bottom/2+8)+'px'}")
        page.wait_for_timeout(3600)
        ctx.close()
        br.close()
    webm = next(tmp.glob("*.webm"))
    mp4 = OUT / f"{slug}.mp4"
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(webm), "-vf", "scale=720:-2,fps=30",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "26", "-movflags", "+faststart", "-an", str(mp4)], check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    return mp4


def main():
    batch = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    only = set(sys.argv[2:])
    OUT.mkdir(exist_ok=True)
    for b in batch:
        if only and b["slug"] not in only:
            continue
        cfg = json.loads((ROOT / "clients" / f"{b['slug']}.json").read_text(encoding="utf-8"))
        t = time.time()
        try:
            f = record(b["slug"], cfg)
            print(f"{b['slug']:32} {f.stat().st_size // 1024} КБ  {time.time() - t:.0f} с", flush=True)
        except Exception as e:
            print(f"{b['slug']:32} ОШИБКА {e}", flush=True)


if __name__ == "__main__":
    main()

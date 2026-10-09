"""Генератор логотипа сервиса (иконка на рабочий стол + эмблема в шапке).

Логотип рисуется кодом в стиле темы сайта (theme) и цвете бренда (accent):
знак по профилю (капля — мойка, блик/бриллиант — детейлинг, стекло — тонировка, машина — остальное)
и сокращение названия (short). Вариации выбираются по slug, чтобы похожие сервисы не совпадали.
Всё важное лежит в центральном круге 80% — иконка годится как maskable (Android обрежет углы).
"""
import hashlib
import math

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS = {
    "sans": ["seguibl.ttf", "segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"],
    "serif": ["georgiab.ttf", "timesbd.ttf", "DejaVuSerif-Bold.ttf"],
    "impact": ["impact.ttf", "ariblk.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"],
    "mono": ["consolab.ttf", "courbd.ttf", "DejaVuSansMono-Bold.ttf"],
    "black": ["ariblk.ttf", "seguibl.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"],
}
SS = 4  # суперсэмплинг для сглаживания


# ---------- цвет ----------
def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def lum(c):
    return (0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]) / 255


def font(kind, px):
    for name in FONTS[kind]:
        try:
            return ImageFont.truetype(name, px)
        except OSError:
            continue
    return ImageFont.load_default()


def seed(slug, n, salt=""):
    return int(hashlib.md5((slug + salt).encode()).hexdigest(), 16) % n


# ---------- примитивы ----------
def gradient(size, c1, c2, angle=90):
    """Линейный градиент c1 -> c2; angle 90 — сверху вниз, 135 — по диагонали."""
    w, h = size
    g = Image.new("RGB", (w, h))
    px = g.load()
    a = math.radians(angle)
    dx, dy = math.cos(a), math.sin(a)
    proj = [x * dx + y * dy for x, y in ((0, 0), (w, 0), (0, h), (w, h))]
    lo, hi = min(proj), max(proj)
    for y in range(h):
        for x in range(0, w):
            t = ((x * dx + y * dy) - lo) / (hi - lo)
            px[x, y] = mix(c1, c2, t)
    return g


def gradient_fast(size, c1, c2, angle=90):
    small = gradient((64, 64), c1, c2, angle)
    return small.resize(size, Image.BICUBIC)


def fill(img, mask, color):
    layer = Image.new("RGBA", img.size, color + (255,))
    img.paste(layer, (0, 0), mask)


def text_fit(text, kind, max_w, max_h):
    px = int(max_h)
    while px > 8:
        f = font(kind, px)
        b = f.getbbox(text)
        if b[2] - b[0] <= max_w and b[3] - b[1] <= max_h:
            return f
        px -= max(1, px // 20)
    return font(kind, 8)


def draw_text_center(draw, cx, cy, text, f, color):
    b = draw.textbbox((0, 0), text, font=f)
    draw.text((cx - (b[0] + b[2]) / 2, cy - (b[1] + b[3]) / 2), text, font=f, fill=color)


def layer(size):
    return Image.new("RGBA", size, (0, 0, 0, 0))


# ---------- знаки (рисуются в маску L внутри квадрата box=(x, y, s)) ----------
def P(box, pts):
    x, y, s = box
    return [(x + px * s, y + py * s) for px, py in pts]


def sym_drop(d, box, gloss=True):
    x, y, s = box
    cx, cy, r = x + .5 * s, y + .62 * s, .34 * s
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    a = math.radians(32)
    d.polygon([(x + .5 * s, y + .02 * s), (cx - r * math.cos(a), cy - r * math.sin(a)), (cx + r * math.cos(a), cy - r * math.sin(a))], fill=255)
    if not gloss:
        return
    hr = .09 * s  # блик
    d.ellipse((cx - .17 * s - hr, cy - hr * 1.2, cx - .17 * s + hr, cy + hr * 1.2), fill=0)


def sym_bubbles(d, box):
    x, y, s = box
    for bx, by, br in ((.38, .6, .3), (.74, .3, .17), (.8, .74, .12)):
        cx, cy, r = x + bx * s, y + by * s, br * s
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
        w = r * .32
        d.ellipse((cx - r + w, cy - r + w, cx + r - w, cy + r - w), fill=0)


def sym_sparkle(d, box):
    def star(cx, cy, R, r):
        pts = []
        for i in range(8):
            ang = math.radians(i * 45 - 90)
            rad = R if i % 2 == 0 else r
            pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
        d.polygon(pts, fill=255)
    x, y, s = box
    star(x + .44 * s, y + .54 * s, .44 * s, .11 * s)
    star(x + .84 * s, y + .17 * s, .15 * s, .045 * s)


def sym_diamond(d, box):
    pts = P(box, [(.2, .18), (.8, .18), (1.0, .42), (.5, .96), (0.0, .42)])
    d.polygon(pts, fill=255)
    x, y, s = box
    lw = max(2, int(.045 * s))
    for a, b in (((0.0, .42), (1.0, .42)), ((.35, .18), (.28, .42)), ((.65, .18), (.72, .42)), ((.28, .42), (.5, .96)), ((.72, .42), (.5, .96))):
        d.line(P(box, [a, b]), fill=0, width=lw)


def sym_window(d, box):
    d.polygon(P(box, [(.04, .86), (.3, .14), (.96, .14), (.96, .86)]), fill=255)
    x, y, s = box
    lw = max(3, int(.07 * s))
    for k in (.42, .62, .82):
        d.line(P(box, [(k - .22, .86), (k + .02, .14)]), fill=0, width=lw)


def sym_car(d, box):
    body = P(box, [(.02, .74), (.04, .56), (.2, .5), (.33, .28), (.64, .25), (.8, .48), (.95, .53), (.98, .74)])
    d.polygon(body, fill=255)
    for wx in (.25, .76):
        x, y, s = box
        cx, cy = x + wx * s, y + .76 * s
        R, r = .15 * s, .11 * s
        d.ellipse((cx - R, cy - R, cx + R, cy + R), fill=0)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    d.polygon(P(box, [(.37, .33), (.47, .32), (.47, .47), (.28, .48)]), fill=0)
    d.polygon(P(box, [(.51, .32), (.61, .31), (.73, .47), (.51, .47)]), fill=0)


def sym_wheel(d, box):
    x, y, s = box
    cx, cy = x + .5 * s, y + .5 * s
    R, r, h = .46 * s, .3 * s, .1 * s
    d.ellipse((cx - R, cy - R, cx + R, cy + R), fill=255)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=0)
    for i in range(5):
        a = math.radians(90 + 72 * i)
        d.line([(cx, cy), (cx + .27 * s * math.cos(a), cy - .27 * s * math.sin(a))], fill=255, width=max(2, int(.07 * s)))
    d.ellipse((cx - h, cy - h, cx + h, cy + h), fill=255)
    for i in range(16):  # протектор
        a = math.radians(360 / 16 * i)
        px, py = cx + (R - .02 * s) * math.cos(a), cy + (R - .02 * s) * math.sin(a)
        d.ellipse((px - .035 * s, py - .035 * s, px + .035 * s, py + .035 * s), fill=0)


SYMBOLS = {"wheel": sym_wheel, "drop": sym_drop, "bubbles": sym_bubbles, "sparkle": sym_sparkle, "diamond": sym_diamond, "window": sym_window, "car": sym_car}


def pick_symbol(cfg):
    kinds = [s.get("iconKey") or s["id"] for s in cfg.get("services", [])]
    ids = [s["id"].rstrip("0123456789") for s in cfg.get("services", [])]
    tint = sum(1 for i in ids if i in ("tint",)) + sum(1 for k in kinds if k == "tint")
    det = sum(1 for i in ids if i in ("polish", "ceramic", "ppf", "detail", "noise", "presale", "coat", "vinyl"))
    wash = sum(1 for i in ids if i in ("wash", "body", "touchless", "express", "under", "engine", "complex"))
    tire = sum(1 for i in ids if i in ("tire", "balance", "rims", "repair", "storage"))
    v = seed(cfg["slug"], 2, "sym")
    if tire >= 2:
        return "wheel"
    if tint >= 2:
        return "car"
    if det > wash:
        return ("sparkle", "diamond")[v]
    if wash:
        return ("drop", "bubbles")[v]
    return "car"


def symbol_mask(size, name, box):
    m = Image.new("L", size, 0)
    SYMBOLS[name](ImageDraw.Draw(m), box)
    return m


def rounded_dashes(d, box, radius, dash, gap, color, width):
    """Пунктирная «строчка» по скруглённому прямоугольнику."""
    x0, y0, x1, y1 = box
    pts = []
    def arc(cx, cy, a0, a1):
        for i in range(13):
            a = math.radians(a0 + (a1 - a0) * i / 12)
            pts.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))
    arc(x1 - radius, y0 + radius, -90, 0)
    arc(x1 - radius, y1 - radius, 0, 90)
    arc(x0 + radius, y1 - radius, 90, 180)
    arc(x0 + radius, y0 + radius, 180, 270)
    pts.append(pts[0])
    on, left = True, dash
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        seg = math.hypot(bx - ax, by - ay)
        pos = 0
        while pos < seg:
            step = min(left, seg - pos)
            if on:
                t0, t1 = pos / seg, (pos + step) / seg
                d.line([(ax + (bx - ax) * t0, ay + (by - ay) * t0), (ax + (bx - ax) * t1, ay + (by - ay) * t1)], fill=color, width=width)
            pos += step
            left -= step
            if left <= 0:
                on = not on
                left = dash if on else gap


# ---------- темы ----------
def draw_lacquer(img, cfg, S, u):
    acc, ink = rgb(cfg["accent"]), rgb(cfg.get("accentInk", "#ffffff"))
    base = mix(acc, (20, 23, 27), .45)
    img.paste(gradient_fast((S, S), mix(acc, (255, 255, 255), .08), base, 115))
    gloss = layer((S, S)); g = ImageDraw.Draw(gloss)
    g.ellipse((-30 * u, -60 * u, 95 * u, 42 * u), fill=(255, 255, 255, 38))
    gloss = gloss.filter(ImageFilter.GaussianBlur(4 * u))
    img.alpha_composite(gloss)
    d = ImageDraw.Draw(img)
    d.line([(-5 * u, 96 * u), (45 * u, 88 * u), (105 * u, 76 * u)], fill=(255, 255, 255, 70), width=int(.8 * u))
    sym = pick_symbol(cfg)
    fill(img, symbol_mask((S, S), sym, (31 * u, 17 * u, 38 * u)), (255, 255, 255))
    f = text_fit(cfg["short"], "sans", 56 * u, 21 * u)
    draw_text_center(d, 50 * u, 70 * u, cfg["short"], f, (255, 255, 255))


def draw_atelier(img, cfg, S, u):
    gold = rgb(cfg["accent"])
    img.paste((21, 20, 18), (0, 0, S, S))
    glow = layer((S, S)); g = ImageDraw.Draw(glow)
    g.ellipse((10 * u, -20 * u, 90 * u, 50 * u), fill=gold + (40,))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(12 * u)))
    d = ImageDraw.Draw(img)
    d.ellipse((14 * u, 14 * u, 86 * u, 86 * u), outline=gold, width=int(1.6 * u))
    d.ellipse((18.5 * u, 18.5 * u, 81.5 * u, 81.5 * u), outline=mix(gold, (21, 20, 18), .45), width=int(.7 * u))
    sp = Image.new("L", (S, S), 0)
    sym_sparkle(ImageDraw.Draw(sp), (45 * u, 20 * u, 10 * u))
    fill(img, sp, gold)
    txt = cfg["short"]
    f = text_fit(txt, "serif", 46 * u, 30 * u if len(txt) < 3 else 22 * u)
    draw_text_center(d, 50 * u, 53 * u, txt, f, gold)
    d.line([(38 * u, 70 * u), (62 * u, 70 * u)], fill=mix(gold, (21, 20, 18), .3), width=int(.8 * u))


def draw_race(img, cfg, S, u):
    acc = rgb(cfg["accent"])
    img.paste((22, 24, 27), (0, 0, S, S))
    st = layer((S, S)); g = ImageDraw.Draw(st)
    off = seed(cfg["slug"], 3, "r") * 4
    for i in range(5):
        x = (54 + off + i * 12) * u
        g.polygon([(x, -5 * u), (x + 7 * u, -5 * u), (x - 22 * u, 105 * u), (x - 29 * u, 105 * u)], fill=acc + (235,))
    img.alpha_composite(st)
    t = layer((S, S)); td = ImageDraw.Draw(t)
    txt = cfg["short"].upper()
    f = text_fit(txt, "impact", 50 * u, 34 * u)
    draw_text_center(td, 44 * u, 50 * u, txt, f, (255, 255, 255, 255))
    t = t.transform((S, S), Image.AFFINE, (1, 0.2, -10 * u, 0, 1, 0), resample=Image.BICUBIC)
    shadow = Image.new("RGBA", (S, S), (22, 24, 27, 0))
    shadow.putalpha(t.getchannel("A").filter(ImageFilter.GaussianBlur(2 * u)))
    img.alpha_composite(Image.composite(Image.new("RGBA", (S, S), (22, 24, 27, 230)), Image.new("RGBA", (S, S), (0, 0, 0, 0)), shadow.getchannel("A")))
    img.alpha_composite(t)
    d = ImageDraw.Draw(img)
    d.polygon([(22 * u, 70 * u), (66 * u, 70 * u), (64 * u, 75 * u), (20 * u, 75 * u)], fill=acc)


def draw_protocol(img, cfg, S, u):
    acc = rgb(cfg["accent"])
    ink = mix(acc, (0, 0, 0), .42)
    img.paste((243, 246, 244), (0, 0, S, S))
    d0 = ImageDraw.Draw(img)
    for yy in range(14, 96, 9):  # линовка бланка
        d0.line([(0, yy * u), (S, yy * u)], fill=(214, 224, 218), width=max(1, int(.35 * u)))
    st = layer((S, S)); d = ImageDraw.Draw(st)
    d.ellipse((13 * u, 13 * u, 87 * u, 87 * u), outline=ink + (255,), width=int(3.2 * u))
    d.ellipse((19 * u, 19 * u, 81 * u, 81 * u), outline=ink + (255,), width=int(1 * u))
    txt = cfg["short"]
    f = text_fit(txt, "mono", 46 * u, 26 * u)
    draw_text_center(d, 50 * u, 47 * u, txt, f, ink + (255,))
    city = (cfg.get("city") or cfg["address"].split(",")[0]).upper()
    city = {"ЕКАТЕРИНБУРГ": "ЕКБ"}.get(city, city)[:8]
    f2 = text_fit(city, "mono", 34 * u, 7 * u)
    draw_text_center(d, 50 * u, 66 * u, city, f2, ink + (255,))
    ang = -12 if seed(cfg["slug"], 2, "p") else 10
    st = st.rotate(ang, resample=Image.BICUBIC, center=(50 * u, 50 * u))
    a = st.getchannel("A").point(lambda v: int(v * .92))
    st.putalpha(a)
    img.alpha_composite(st)


def draw_aqua(img, cfg, S, u):
    acc, ink = rgb(cfg["accent"]), rgb(cfg.get("accentInk", "#04202c"))
    img.paste(gradient_fast((S, S), mix(acc, (255, 255, 255), .45), acc, 90))
    d = ImageDraw.Draw(img)
    for bx, by, br in ((18, 22, 6), (82, 30, 9), (86, 72, 4), (14, 70, 3.5)):
        d.ellipse(((bx - br) * u, (by - br) * u, (bx + br) * u, (by + br) * u), outline=(255, 255, 255), width=int(.9 * u))
    wave = Image.new("L", (S, S), 0); w = ImageDraw.Draw(wave)
    pts = [(x * u, (86 + 3 * math.sin(x / 9)) * u) for x in range(0, 101, 2)] + [(S, S), (0, S)]
    w.polygon(pts, fill=90)
    fill(img, wave, (255, 255, 255))
    m = Image.new("L", (S, S), 0)
    sym_drop(ImageDraw.Draw(m), (22 * u, 8 * u, 56 * u), gloss=False)
    fill(img, m, (255, 255, 255))
    txt = cfg["short"]
    f = text_fit(txt, "sans", 30 * u, 17 * u)
    dark = mix(acc, (0, 0, 0), .5) if lum(acc) > .35 else acc
    draw_text_center(d, 50 * u, 46 * u + 3 * u, txt, f, dark)


def draw_stitch(img, cfg, S, u):
    acc = rgb(cfg["accent"])
    plum = mix(acc, (23, 18, 29), .78)
    img.paste(gradient_fast((S, S), mix(acc, plum, .55), plum, 120))
    d = ImageDraw.Draw(img)
    rounded_dashes(d, (11 * u, 11 * u, 89 * u, 89 * u), 14 * u, 4 * u, 2.6 * u, mix(acc, (255, 255, 255), .55), int(1.2 * u))
    sym = pick_symbol(cfg)
    sym = sym if sym != "car" else "sparkle"
    fill(img, symbol_mask((S, S), sym, (39 * u, 20 * u, 22 * u)), mix(acc, (255, 255, 255), .35))
    txt = cfg["short"]
    f = text_fit(txt, "sans", 52 * u, 24 * u)
    draw_text_center(d, 50 * u, 63 * u, txt, f, (255, 255, 255))


def draw_sticker(img, cfg, S, u):
    acc = rgb(cfg["accent"])
    black = (29, 15, 23)
    img.paste(acc, (0, 0, S, S))
    d0 = ImageDraw.Draw(img)
    for i in range(0, 100, 8):  # точечный фон
        for j in range(0, 100, 8):
            d0.ellipse(((i + 2) * u, (j + 2) * u, (i + 3.1) * u, (j + 3.1) * u), fill=mix(acc, black, .12))
    st = layer((S, S)); d = ImageDraw.Draw(st)
    d.ellipse((22 * u, 22 * u, 84 * u, 84 * u), fill=black + (255,))
    d.ellipse((17 * u, 17 * u, 79 * u, 79 * u), fill=(255, 255, 255, 255), outline=black + (255,), width=int(2.4 * u))
    txt = cfg["short"]
    f = text_fit(txt, "black", 40 * u, 24 * u)
    draw_text_center(d, 48 * u, 48 * u, txt, f, black + (255,))
    ang = -9 if seed(cfg["slug"], 2, "s") else 8
    st = st.rotate(ang, resample=Image.BICUBIC, center=(50 * u, 50 * u))
    img.alpha_composite(st)
    sp = Image.new("L", (S, S), 0)
    sym_sparkle(ImageDraw.Draw(sp), (64 * u, 12 * u, 22 * u))
    edge = sp.filter(ImageFilter.MaxFilter(int(2 * u) | 1))
    fill(img, edge, black)
    fill(img, sp, (255, 225, 77))


THEMES = {"lacquer": draw_lacquer, "atelier": draw_atelier, "race": draw_race, "protocol": draw_protocol,
          "aqua": draw_aqua, "stitch": draw_stitch, "sticker": draw_sticker}


def make_logo(cfg, size):
    S = size * SS
    u = S / 100
    img = Image.new("RGBA", (S, S), (0, 0, 0, 255))
    THEMES.get(cfg.get("theme", "lacquer"), draw_lacquer)(img, cfg, S, u)
    return img.convert("RGB").resize((size, size), Image.LANCZOS)


def splash_color(cfg):
    """Цвет фона заставки при запуске с рабочего стола — под логотип."""
    acc = rgb(cfg["accent"])
    t = cfg.get("theme", "lacquer")
    c = {"atelier": (21, 20, 18), "race": (22, 24, 27), "protocol": (243, 246, 244), "aqua": acc, "sticker": acc,
         "stitch": mix(acc, (23, 18, 29), .78)}.get(t, mix(acc, (20, 23, 27), .45))
    return "#%02x%02x%02x" % c

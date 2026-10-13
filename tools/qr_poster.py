"""QR-постер для печати: python tools/qr_poster.py <slug>  -> kp/qr-<slug>-A4.pdf/.png и qr-<slug>-A6.png
Ссылка на запись, логотип клиента, название, крупная надпись «Записаться онлайн». Цвет — accent клиента."""
import json, sys
from pathlib import Path
import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
slug = sys.argv[1]
cfg = json.loads((ROOT / "clients" / f"{slug}.json").read_text(encoding="utf-8"))
url = f"https://koky09.github.io/tver-demo/{slug}/"
acc = cfg["accent"]
F = "C:/Windows/Fonts/"
bold = lambda s: ImageFont.truetype(F + "arialbd.ttf", s)
reg = lambda s: ImageFont.truetype(F + "arial.ttf", s)


def qr_img(px):
    q = qrcode.QRCode(error_correction=ERROR_CORRECT_H, border=2, box_size=10)
    q.add_data(url); q.make(fit=True)
    im = q.make_image(fill_color="#0b0b0b", back_color="white").convert("RGB").resize((px, px), Image.NEAREST)
    logo_p = ROOT / "clients" / "logos" / f"{slug}.png"
    if logo_p.exists():  # логотип в центре (уровень коррекции H выдерживает до 30%)
        lg = Image.open(logo_p).convert("RGB"); s = px // 4
        lg = lg.resize((s, s), Image.LANCZOS)
        pad = Image.new("RGB", (s + 16, s + 16), "white"); pad.paste(lg, (8, 8))
        im.paste(pad, ((px - pad.width) // 2, (px - pad.height) // 2))
    return im


def center(d, y, text, font, fill, W):
    w = d.textlength(text, font=font); d.text(((W - w) / 2, y), text, font=font, fill=fill)


def poster(W, H, k):
    im = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, int(H * .2)), fill=acc)
    logo_p = ROOT / "clients" / "logos" / f"{slug}.png"
    if logo_p.exists():
        s = int(H * .15); lg = Image.open(logo_p).convert("RGB").resize((s, s), Image.LANCZOS)
        im.paste(lg, ((W - s) // 2, int(H * .025)))
    else:
        center(d, int(H * .07), cfg["name"], bold(int(90 * k)), "white", W)
    center(d, int(H * .24), "Записаться онлайн", bold(int(110 * k)), "#0b0b0b", W)
    center(d, int(H * .24) + int(135 * k), "Наведите камеру телефона на код", reg(int(52 * k)), "#444444", W)
    qs = int(W * .62); q = qr_img(qs)
    qy = int(H * .37); im.paste(q, ((W - qs) // 2, qy))
    d.rounded_rectangle(((W - qs) // 2 - 12, qy - 12, (W + qs) // 2 + 12, qy + qs + 12), radius=24, outline=acc, width=int(10 * k))
    y = qy + qs + int(60 * k)
    for t, f in (("Выберите услугу и свободное время —", reg(int(50 * k))), ("без звонка, в любое время суток", reg(int(50 * k)))):
        center(d, y, t, f, "#222222", W); y += int(66 * k)
    d.rectangle((0, H - int(H * .07), W, H), fill="#0b0b0b")
    center(d, H - int(H * .07) + int(H * .018), f"{cfg['name']} · {cfg['address'].replace('Москва, ', '')}", reg(int(44 * k)), "white", W)
    return im


out = ROOT / "kp"
a4 = poster(2480, 3508, 1.0)                       # A4, 300 dpi
a4.save(out / f"qr-{slug}-A4.png"); a4.save(out / f"qr-{slug}-A4.pdf", resolution=300)
a6 = poster(1240, 1748, 0.5)                       # A6 табличка, 300 dpi
a6.save(out / f"qr-{slug}-A6.png")
qr_img(1200).save(out / f"qr-{slug}-only.png")
print("готово:", url)

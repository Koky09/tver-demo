"""Скачать фото Unsplash по списку id и собрать пронумерованные листы для выбора.
    python tools/newclient/contact_sheet.py tools/newclient/unsplash_<ниша>
В папке нужен _ids.txt (id через пробел или по строке). Пишет <id>.jpg, _order.txt (номер -> id) и _sheet0.jpg, _sheet1.jpg ..."""
import sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image, ImageDraw

out = Path(sys.argv[1])
ids = (out / "_ids.txt").read_text().split()


def get(i):
    p = out / f"{i}.jpg"
    if p.exists():
        return
    u = f"https://images.unsplash.com/{i}?w=1080&q=80&fm=jpg&fit=max"
    try:
        p.write_bytes(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read())
    except Exception as e:
        print(i, e)


with ThreadPoolExecutor(8) as ex:
    list(ex.map(get, ids))
fs = sorted(out.glob("photo-*.jpg"))
(out / "_order.txt").write_text("\n".join(f.stem for f in fs))
W, H, C = 200, 150, 12
for part in range(0, len(fs), 96):
    chunk = fs[part:part + 96]
    sh = Image.new("RGB", (C * W, ((len(chunk) + C - 1) // C) * H), "white")
    d = ImageDraw.Draw(sh)
    for i, f in enumerate(chunk):
        im = Image.open(f).convert("RGB")
        r = max(W / im.width, H / im.height)
        im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1))
        x, y = (im.width - W) // 2, (im.height - H) // 2
        sh.paste(im.crop((x, y, x + W, y + H)), ((i % C) * W, (i // C) * H))
        d.rectangle(((i % C) * W, (i // C) * H, (i % C) * W + 34, (i // C) * H + 18), fill="black")
        d.text(((i % C) * W + 3, (i // C) * H + 3), str(part + i), fill="yellow")
    sh.save(out / f"_sheet{part // 96}.jpg", quality=80)
print(len(fs))

"""Фото, которые есть сразу у нескольких бань (реклама и чужие фото в выдаче Яндекса), -> sauna_photos/_dupes.json; apply их пропускает.
    python tools/newclient/sauna_dedupe.py"""
import json
from pathlib import Path
from PIL import Image

PH = Path(__file__).parent / "sauna_photos"


def ah(f):
    im = Image.open(f).convert("L").resize((12, 12))
    px = list(im.getdata()); m = sum(px) / len(px)
    return sum(1 << i for i, p in enumerate(px) if p > m)


seen = {}
for d in sorted(p for p in PH.iterdir() if p.is_dir() and not p.name.startswith("_")):
    for f in d.glob("*.jpg"):
        seen.setdefault(ah(f), []).append((d.name, int(f.stem)))
dup = {}
for h, lst in seen.items():
    if len({s for s, _ in lst}) > 1:
        for s, n in lst:
            dup.setdefault(s, []).append(n)
(PH / "_dupes.json").write_text(json.dumps(dup, indent=0), encoding="utf-8")
print("бань с чужими фото:", len(dup), "фото:", sum(map(len, dup.values())))

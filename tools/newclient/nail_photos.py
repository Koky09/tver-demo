"""Фото для шапки сайтов маникюра: своё у каждой студии, в настроении её стиля и в её цвете.
    python tools/newclient/nail_photos.py [slug ...]     -> clients/photos/<slug>.jpg
Нужен локальный Forge API: D:\\AI\\sd-webui-forge-neo, launch.py --api --nowebui --port 7861 (модель Flux).
Фото иллюстративные (на сайте и в рассылке сказано, что заменим на фото студии)."""
import base64, colorsys, hashlib, io, json, sys, urllib.request
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "clients" / "photos"
API = "http://127.0.0.1:7861/sdapi/v1/txt2img"
MODEL = "fluxFusionV24StepsGGUFNF4_V2GGUFQ4KS"
MODULES = ["clip_l.safetensors", "t5xxl_fp8_e4m3fn.safetensors", "ae.safetensors"]

SCENE = {
    "noir": "elegant woman's hand with long almond nails, glossy {c} gel polish, thin gold rings, resting on black velvet, dramatic low-key studio light, luxury magazine",
    "petal": "delicate hand with short rounded nails, soft {c} gel polish with tiny painted flowers, holding a peony, pastel background, soft daylight, dreamy",
    "vogue": "fashion editorial photo, hand with long square nails painted {c}, touching face of a stylish model, bold, high contrast, magazine cover look",
    "glass": "close-up of manicured hand with {c} chrome nails, neon reflections, bokeh lights of a modern nail salon at night, cinematic",
    "arch": "minimalist photo, hand with clean nude manicure and {c} accent nail, holding a ceramic cup, beige linen, warm natural window light, calm aesthetic",
    "bloom": "playful colorful nail art, hand with {c} nails decorated with smiley faces and hearts, bright candy background, fun pop style",
}
NEG = "deformed fingers, extra fingers, missing fingers, fused fingers, bad hands, text, watermark, logo"


def color_word(hexc):
    r, g, b = (int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    h *= 360
    if s < .2:
        return "nude beige" if l > .5 else "dark espresso"
    names = [(15, "red"), (35, "terracotta"), (50, "golden caramel"), (70, "gold"), (160, "mint green"), (200, "teal"),
             (250, "lilac"), (290, "lavender purple"), (330, "hot pink"), (345, "raspberry"), (361, "red")]
    for lim, n in names:
        if h < lim:
            return ("deep " if l < .35 else "pastel " if l > .7 else "") + n


def gen(slug, theme, accent):
    seed = int(hashlib.md5(slug.encode()).hexdigest()[:8], 16) % 2_000_000_000
    prompt = SCENE[theme].format(c=color_word(accent)) + ", photorealistic, sharp focus, beautiful anatomically correct hand, 85mm"
    body = {"prompt": prompt, "negative_prompt": NEG, "steps": 6, "cfg_scale": 1, "distilled_cfg_scale": 3.5,
            "width": 832, "height": 1088, "sampler_name": "Euler", "scheduler": "Simple", "seed": seed,
            "override_settings": {"sd_model_checkpoint": MODEL, "forge_additional_modules": MODULES}}
    req = urllib.request.Request(API, json.dumps(body).encode(), {"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=900))
    im = Image.open(io.BytesIO(base64.b64decode(r["images"][0]))).convert("RGB")
    OUT.mkdir(parents=True, exist_ok=True)
    im.save(OUT / f"{slug}.jpg", quality=84, optimize=True, progressive=True)


def main():
    only = set(sys.argv[1:])
    for p in sorted((ROOT / "clients").glob("nail-*.json")):
        c = json.loads(p.read_text(encoding="utf-8"))
        if only and c["slug"] not in only:
            continue
        if not only and (OUT / f"{c['slug']}.jpg").exists():
            continue
        if c["theme"] not in SCENE:
            print("пропуск, стиль не салонный:", c["slug"], c["theme"]); continue
        gen(c["slug"], c["theme"], c["accent"])
        print("фото:", c["slug"], c["theme"], color_word(c["accent"]), flush=True)


if __name__ == "__main__":
    main()

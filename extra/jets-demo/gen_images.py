"""Генерирует фото самолётов для демо через локальный Forge (API на порту 7861, модель Flux)."""
import base64, json, sys, time, urllib.request
from pathlib import Path

API = "http://127.0.0.1:7861/sdapi/v1/txt2img"
OUT = Path(__file__).parent / "img"; OUT.mkdir(exist_ok=True)
STYLE = ", cinematic photo, dark moody minimalist, deep shadows, subtle warm gold rim light, ultra detailed, 35mm, high-end aviation advertising"
SHOTS = {
    "hero": (1536, 864, "private business jet flying above clouds at dusk, side view, dark blue sky, golden sunset glow on fuselage"),
    "jet1": (1024, 768, "small white light business jet Cessna Citation parked on dark wet tarmac at night, airport lights bokeh"),
    "jet2": (1024, 768, "light business jet Embraer Phenom taxiing on runway at blue hour, reflections on wet asphalt"),
    "jet3": (1024, 768, "midsize business jet Bombardier Challenger in a dark minimalist hangar, spotlight from above"),
    "jet4": (1024, 768, "midsize business jet taking off at sunset, low angle, dramatic sky"),
    "jet5": (1024, 768, "large long-range Gulfstream business jet on private airfield at twilight, three quarter view, dark sky"),
    "jet6": (1024, 768, "large ultra long range business jet Global 7500 flying above clouds at night, moonlight"),
}

def gen(name, w, h, prompt):
    body = {"prompt": prompt + STYLE, "steps": 6, "cfg_scale": 1, "distilled_cfg_scale": 3.5,
            "width": w, "height": h, "sampler_name": "Euler", "scheduler": "Simple", "seed": -1,
            "override_settings": {"sd_model_checkpoint": "fluxFusionV24StepsGGUFNF4_V2GGUFQ4KS",
                                  "forge_additional_modules": ["clip_l.safetensors", "t5xxl_fp8_e4m3fn.safetensors", "ae.safetensors"]}}
    req = urllib.request.Request(API, json.dumps(body).encode(), {"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=900))
    (OUT / f"{name}.png").write_bytes(base64.b64decode(r["images"][0]))
    print("ok", name, flush=True)

for n in (sys.argv[1:] or SHOTS):
    t = time.time(); gen(n, *SHOTS[n]); print(f"  {time.time()-t:.0f}s", flush=True)

"""Раздаёт студиям маникюра салонные стили (noir, petal, vogue, glass, arch, bloom), цвета и подписи так, чтобы не было двух одинаковых.
    python tools/newclient/nail_themes.py"""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
THEMES = ["noir", "petal", "vogue", "glass", "arch", "bloom"]
HINT = [(r"золот|diamond|gold|lux|noir|нуар|миндал|огон|vip|визион|vision", "noir"), (r"fairy|цвет|роз|ягод|ника|лу ?лу|флор|flor", "petal"),
        (r"why|vogue|setka|the |лица|pudra|пудра|style", "vogue"), (r"neon|glass|star|breeze|chiki|manik|time", "glass"),
        (r"арка|nuance|нюанс|academ|академ|марф|марафет|image|имидж", "arch"), (r"chiki|riki|мама|солнц|samanic|polly|blash|блаш", "bloom")]
COLORS = {  # акцент, цвет текста на нём
    "noir": [("#e5c07b", "#17120c"), ("#5e8b7e", "#ffffff"), ("#c48b9f", "#ffffff"), ("#c9a86a", "#17120c"), ("#b76e79", "#ffffff"), ("#8e1b3a", "#ffffff"), ("#d4a373", "#17120c"), ("#7d5ba6", "#ffffff"), ("#a3333d", "#ffffff")],
    "petal": [("#f4978e", "#3a1210"), ("#b8a1d9", "#22163a"), ("#e3a587", "#3a1d0e"), ("#e8879c", "#ffffff"), ("#c58fd3", "#ffffff"), ("#f2a07b", "#3a1a0e"), ("#d77fa1", "#ffffff"), ("#9fb8a0", "#16261a"), ("#e6a4b4", "#3b1420")],
    "vogue": [("#2563eb", "#ffffff"), ("#b91c1c", "#ffffff"), ("#65a30d", "#ffffff"), ("#e11d48", "#ffffff"), ("#111111", "#ffffff"), ("#d97706", "#ffffff"), ("#7c3aed", "#ffffff"), ("#be185d", "#ffffff"), ("#0f766e", "#ffffff")],
    "glass": [("#f97316", "#1a0a02"), ("#3b82f6", "#ffffff"), ("#d946ef", "#ffffff"), ("#ec4899", "#ffffff"), ("#8b5cf6", "#ffffff"), ("#06b6d4", "#04161a"), ("#f43f5e", "#ffffff"), ("#a855f7", "#ffffff"), ("#14b8a6", "#04161a")],
    "arch": [("#7a8b99", "#ffffff"), ("#b07d62", "#ffffff"), ("#94776b", "#ffffff"), ("#a0785a", "#ffffff"), ("#b5838d", "#ffffff"), ("#6d6875", "#ffffff"), ("#8a9a5b", "#ffffff"), ("#c08552", "#ffffff"), ("#9d6b53", "#ffffff")],
    "bloom": [("#ffb703", "#1a1300"), ("#e84393", "#ffffff"), ("#6c5ce7", "#ffffff"), ("#ff5c8a", "#ffffff"), ("#7b61ff", "#ffffff"), ("#ff8a3d", "#1a0d02"), ("#00b894", "#04140f"), ("#ff4757", "#ffffff"), ("#3d9cff", "#ffffff")],
}
KICK = {
    "noir": ["Студия маникюра", "Маникюр премиум-класса", "Ногтевая студия", "Искусство маникюра"],
    "petal": ["маникюр и педикюр", "нежный маникюр", "красота в деталях", "уход и маникюр"],
    "vogue": ["Маникюр, который хочется показать", "Ногти как с обложки", "Тренды сезона — у нас", "Ваш лучший маникюр"],
    "glass": None, "bloom": None,
    "arch": ["Ногтевая студия", "Маникюр и уход", "Студия красоты", "Чистый маникюр"],
}
RING = ["маникюр • педикюр • дизайн • запись онлайн • ", "ногти • дизайн • уход • запись 24/7 • ", "маникюр • покрытие • френч • запись онлайн • "]


def main():
    files = sorted((ROOT / "clients").glob("nail-*.json"))
    count = {t: 0 for t in THEMES}
    i = 0
    for p in files:
        c = json.loads(p.read_text(encoding="utf-8"))
        n = c["name"].lower()
        want = next((t for rx, t in HINT if re.search(rx, n)), None)
        cap = len(files) // len(THEMES) + 1
        if not want or count[want] >= cap:
            want = min(THEMES, key=lambda t: (count[t], (THEMES.index(t) - i) % len(THEMES)))
        k = count[want]
        count[want] += 1
        i += 1
        c["theme"] = want
        c["accent"], c["accentInk"] = COLORS[want][k % len(COLORS[want])]
        if KICK.get(want):
            c["kicker"] = KICK[want][k % len(KICK[want])]
        else:
            c.pop("kicker", None)
        if want == "bloom":
            c["ringText"] = RING[k % len(RING)]
        else:
            c.pop("ringText", None)
        p.write_text(json.dumps(c, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{c['slug']:32} {want:6} {c['accent']}")
    print(count)


if __name__ == "__main__":
    main()

"""Сервер демо: раздаёт dist/ и шлёт уведомления о записях в Telegram.

    python server.py               -> http://localhost:8765
    python server.py --find-chat   -> показать chat_id тех, кто написал боту

Настройки в .env рядом с файлом:
    TG_BOT_TOKEN=123456:ABC...     (от @BotFather)
    TG_CHAT_ID=123456789           (куда слать; можно несколько через запятую)
"""
import html
import json
import os
import sys
import time
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "docs"
PORT = int(os.environ.get("PORT", 8765))


def load_env():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8-sig").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


load_env()
TOKEN = os.environ.get("TG_BOT_TOKEN", "")
CHATS = [c.strip() for c in os.environ.get("TG_CHAT_ID", "").split(",") if c.strip()]


def tg(method, payload):
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/{method}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def client_name(slug):
    p = ROOT / "clients" / f"{slug}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))["name"]
    return slug


def format_msg(b):
    e = lambda s: html.escape(str(s or ""))
    kind = {"booking": "🆕 Новая запись", "cancel": "❌ Запись отменена"}.get(b.get("event"), "Запись")
    src = {"app": "онлайн", "phone": "добавлена владельцем"}.get(b.get("source"), b.get("source", ""))
    lines = [
        f"<b>{kind}</b> · {e(client_name(b.get('slug')))}",
        "",
        f"🛠 {e(b.get('svcName'))} — {e(b.get('priceText'))}",
        f"📅 {e(b.get('when'))}",
        f"📦 {e(b.get('boxText'))}",
        f"👤 {e(b.get('name'))}",
        f"📞 {e(b.get('phone'))}",
    ]
    if b.get("comment"):
        lines.append(f"💬 {e(b['comment'])}")
    lines.append(f"<i>{e(src)}</i>")
    return "\n".join(lines)


_last = {}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(DIST), **kw)

    def log_message(self, fmt, *args):
        if self.path.startswith("/api/"):
            super().log_message(fmt, *args)

    def send_json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/api/notify":
            return self.send_json(404, {"ok": False})
        # простая защита от спама: не чаще раза в 3 сек с одного IP
        ip = self.client_address[0]
        if time.time() - _last.get(ip, 0) < 3:
            return self.send_json(429, {"ok": False, "error": "too often"})
        _last[ip] = time.time()
        try:
            n = min(int(self.headers.get("Content-Length", 0)), 8000)
            data = json.loads(self.rfile.read(n) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self.send_json(400, {"ok": False})
        if not TOKEN or not CHATS:
            print("! TG_BOT_TOKEN / TG_CHAT_ID не заданы в .env — уведомление не отправлено")
            return self.send_json(200, {"ok": False, "error": "telegram not configured"})
        text = format_msg(data)
        sent = 0
        for chat in CHATS:
            try:
                tg("sendMessage", {"chat_id": chat, "text": text, "parse_mode": "HTML"})
                sent += 1
            except (urllib.error.URLError, TimeoutError) as err:
                print("! Telegram:", err)
        self.send_json(200, {"ok": sent > 0})


def find_chat():
    if not TOKEN:
        sys.exit("Сначала впишите TG_BOT_TOKEN в .env")
    me = tg("getMe", {})["result"]
    upd = tg("getUpdates", {})["result"]
    print(f"Бот: @{me['username']}")
    chats = {}
    for u in upd:
        m = u.get("message") or u.get("channel_post") or {}
        c = m.get("chat")
        if c:
            chats[c["id"]] = c.get("title") or " ".join(filter(None, [c.get("first_name"), c.get("last_name")])) or c.get("username")
    if not chats:
        print(f"Никто ещё не писал боту. Откройте https://t.me/{me['username']}, нажмите Start, и запустите команду снова.")
    for cid, name in chats.items():
        print(f"  chat_id={cid}   ({name})")


if __name__ == "__main__":
    if "--find-chat" in sys.argv:
        find_chat()
    else:
        print(f"http://localhost:{PORT}  | Telegram: {'настроен, чатов: ' + str(len(CHATS)) if TOKEN and CHATS else 'НЕ настроен (.env)'}")
        ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

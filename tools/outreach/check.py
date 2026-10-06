"""Проверка страницы рассылки перед публикацией: скрипт без синтаксических ошибок и все сообщения на месте.
Нужен Node.js (node --check). Пустая страница «0 из 0» 06.10.2026 была именно из-за ошибки в скрипте."""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def check_page(path, expected):
    html = Path(path).read_text(encoding="utf-8")
    script = re.findall(r"<script>(.*?)</script>", html, re.S)[-1]
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(script)
    r = subprocess.run(["node", "--check", f.name], capture_output=True, text=True, encoding="utf-8")
    Path(f.name).unlink()
    if r.returncode:
        sys.exit(f"ОШИБКА в скрипте {path}, не публиковать:\n{r.stderr}")
    data = json.loads(re.search(r"const DATA = (\[.*?\]);\n", script, re.S).group(1))
    if len(data) != expected:
        sys.exit(f"ОШИБКА: в {path} {len(data)} сообщений вместо {expected}")
    print(f"проверено: {Path(path).name} — скрипт в порядке, сообщений {len(data)}")

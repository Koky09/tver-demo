#!/usr/bin/env bash
# Сборка всех сайтов и копия для проверки без настоящих записей: .preview/ с apiUrl = mock-сервер (localhost:8766).
# Дальше: node backend/mock-server.js (PIN 123456) и статический сервер на .preview/, например
#   python -m http.server 8770 -d .preview
# Не проверять через server.py: он шлёт уведомления в настоящий Telegram.
set -e
cd "$(dirname "$0")/../.."
node --check template/app.js
PYTHONIOENCODING=utf-8 python build.py >/dev/null
rm -rf .preview && mkdir .preview && cp -r docs/* .preview/
sed -i 's#"apiUrl": "[^"]*"#"apiUrl": "http://localhost:8766"#' .preview/*/config.js
echo "собрано: $(ls -d .preview/*/ | wc -l) сайтов в .preview/"

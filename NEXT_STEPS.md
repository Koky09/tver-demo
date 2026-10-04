# Состояние проекта (обновлено 04.10.2026)

## Готово
- **Сервер записи** (Google Apps Script, развёртывание «Версия 2») работает. Проверено на живом сервере:
  - запись создаётся, двойная запись отклоняется;
  - кабинет открывается по PIN;
  - отмена работает;
  - уведомления в Telegram приходят;
  - телефон «+7…» и формулы в полях хранятся как текст.
  - Таблица: https://docs.google.com/spreadsheets/d/1lWFbcqNr8ByOfYEPzYV9uOmulhXp6h3-cvbX3gvZNZM/edit
  - Проект скрипта: https://script.google.com/home/projects/1oy2jIjXTDnGcYydFHJ_WrSzMamz9Zgp7S9JG5RsiQ61ZXLeFzS7tKFXY/edit
- **6 сайтов опубликованы:** https://koky09.github.io/tver-demo/ (morrus, nazar, expertavto, oazis, detailing69, mamina-podruga).
- Все 6 сервисов заведены в листе `clients`, PIN выданы. PIN хранятся только в таблице.

## Как обновлять сервер
1. Поменять код в `backend/Code.gs` и вставить его в редактор Apps Script (DEFAULTS и addClients в редакторе не затирать).
2. В редакторе: «Начать развертывание» → «Управление развертываниями» → «Редактировать» → «Новая версия» → «Начать развертывание».
3. URL сервера при этом не меняется.

## Сделать дальше
1. Сверить цены и часы работы 5 новых сервисов с их ВК или картами (сейчас цены примерные).
2. Удалить тестовые строки на листе `bookings` (сервисы `test` и `nazar`, имена «ТЕСТ…»).
3. Перед продажей: в `clients/<slug>.json` поставить `"demo": false`, затем `python build.py` и `publish.ps1`.
4. По желанию: переименовать бота в @BotFather (`/setname`).

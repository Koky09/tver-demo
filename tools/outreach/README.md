# Страницы рассылки

Генераторы страниц, с которых пишем владельцам: текст сообщения, кнопки WhatsApp и Telegram, галочка «Отправил».

    python tools/outreach/mkpage.py   # мойки и детейлинги, 64 сообщения → out/outreach.html
    python tools/outreach/mkrest.py   # рестораны, 50 сообщений → out/outreach-rest.html

- Каждый запуск сам проверяет страницу (`check.py`, нужен Node.js): если в скрипте ошибка или не хватает сообщений, будет «ОШИБКА…», и такую страницу не публиковать.
- `out/` не идёт в git: там телефоны.
- Опубликованные страницы (артефакты claude.ai, обновлять по тем же ссылкам):
  - «Рассылка владельцам»: https://claude.ai/artifact/2JPcxxW5ShB9kUuWx2qSWs
  - «Рассылка ресторанам»: https://claude.ai/artifact/4jCXW9thZ3JaLxLLCV7qtt
- Цена в сообщениях: 3 500 ₽ один раз, не в месяц.
- Данные ресторанов берутся из `D:\AI\sites-restaurants\sites\CLIENTS.md`; Telegram ресторанов — словарь `TG` в `mkrest.py`.

## Как искать Telegram заведения
1. 2ГИС: карточка `2gis.ru/<город>/firm/<id>`, в `initialState` → `contact_groups` (telegram, whatsapp, vkontakte, website — там тоже бывают ссылки t.me).
2. Яндекс Карты: страница `yandex.ru/maps/org/<slug>/<id>/`, ссылки в блоке `.business-contacts-view__social-links`.
   Не брать ссылки со всей страницы: там есть соцсети «похожих мест» и самих Яндекс Карт.
3. Каждую найденную ссылку проверить на `t.me/<имя>`: кнопка «Send Message» — личный аккаунт, «View in Telegram» с подписчиками — канал (лично не написать), «Start Bot» — бот.
   В описании каналов часто есть @менеджер или другой номер — это лучший контакт.
4. `t.me/+79...` — номер подключён к Telegram, можно писать по номеру.

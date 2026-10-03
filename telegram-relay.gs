// Google Apps Script: пересылает записи из приложения в Telegram.
// Токен хранится в настройках скрипта (Script Properties), в код сайта он не попадает.
//
// Установка:
// 1. https://script.google.com → «Новый проект», вставить этот код.
// 2. ⚙ «Настройки проекта» → «Свойства скрипта» → добавить:
//      TG_BOT_TOKEN = токен от @BotFather
//      TG_CHAT_ID   = ваш chat_id (несколько — через запятую)
// 3. «Начать развертывание» → «Новое развертывание» → тип «Веб-приложение»,
//    «Запуск от имени»: Я, «У кого есть доступ»: Все → «Развернуть», разрешить доступ.
// 4. Скопировать URL веб-приложения (…/exec) и вписать в settings.json → notifyUrl.

function doPost(e) {
  var props = PropertiesService.getScriptProperties();
  var token = props.getProperty('TG_BOT_TOKEN');
  var chats = String(props.getProperty('TG_CHAT_ID') || '').split(',').map(function (s) { return s.trim(); }).filter(String);
  if (!token || !chats.length) return out({ ok: false, error: 'not configured' });

  var b;
  try { b = JSON.parse(e.postData.contents); } catch (err) { return out({ ok: false }); }
  if (!b.name || !b.phone || !b.svcName) return out({ ok: false });

  // защита от спама: не больше 30 сообщений за 10 минут
  var cache = CacheService.getScriptCache();
  var n = Number(cache.get('n') || 0);
  if (n >= 30) return out({ ok: false, error: 'rate limit' });
  cache.put('n', String(n + 1), 600);

  var esc = function (s) { return String(s == null ? '' : s).slice(0, 300).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); };
  var kind = { booking: '🆕 Новая запись', cancel: '❌ Запись отменена' }[b.event] || 'Запись';
  var src = { app: 'онлайн', phone: 'добавлена владельцем' }[b.source] || '';
  var lines = [
    '<b>' + kind + '</b> · ' + esc(b.clientName || b.slug),
    '',
    '🛠 ' + esc(b.svcName) + ' — ' + esc(b.priceText),
    '📅 ' + esc(b.when),
    '📦 ' + esc(b.boxText),
    '👤 ' + esc(b.name),
    '📞 ' + esc(b.phone)
  ];
  if (b.comment) lines.push('💬 ' + esc(b.comment));
  lines.push('<i>' + esc(src) + '</i>');

  var sent = 0;
  chats.forEach(function (chat) {
    var r = UrlFetchApp.fetch('https://api.telegram.org/bot' + token + '/sendMessage', {
      method: 'post', contentType: 'application/json', muteHttpExceptions: true,
      payload: JSON.stringify({ chat_id: chat, text: lines.join('\n'), parse_mode: 'HTML' })
    });
    if (r.getResponseCode() === 200) sent++;
  });
  return out({ ok: sent > 0 });
}

function out(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

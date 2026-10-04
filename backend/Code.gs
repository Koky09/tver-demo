/**
 * Сервер онлайн-записи: Google Apps Script + Google Таблица.
 *
 * Листы таблицы:
 *   bookings — все записи всех клиентов (заполняется автоматически)
 *   clients  — владельцы: slug | name | boxes | pin | owner_chats | link_code
 *              Вы вписываете slug, name и boxes, остальное скрипт заполнит сам (меню «Запись» → «Обновить клиентов»).
 *   services — правки цен и услуг, которые владелец сделал в кабинете
 *
 * Свойства скрипта (⚙ Настройки проекта → Свойства скрипта):
 *   TG_BOT_TOKEN     — токен бота от @BotFather
 *   TG_BOT_USERNAME  — имя бота без @, например ivedomlenia_bot
 *   ADMIN_CHAT_ID    — ваш chat_id: сюда приходят записи сервисов, у которых ещё не подключён владелец
 *   COPY_ALL         — "1", если хотите получать копии всех записей всех клиентов
 *
 * Установка — в README_BACKEND.md.
 */

var SHEETS = {
  bookings: ['id', 'slug', 'created', 'status', 'date', 'start', 'end', 'box', 'svcId', 'svcName', 'price', 'name', 'phone', 'comment', 'source', 'intervals'],
  clients: ['slug', 'name', 'boxes', 'pin', 'owner_chats', 'link_code'],
  services: ['slug', 'overrides']
};

/* ================= меню и установка ================= */

function setup() {
  var ss = book_();
  Object.keys(SHEETS).forEach(function (name) {
    var sh = ss.getSheetByName(name) || ss.insertSheet(name);
    if (sh.getLastRow() === 0) sh.appendRow(SHEETS[name]);
    sh.getRange(1, 1, sh.getMaxRows(), SHEETS[name].length).setNumberFormat('@'); // всё храним как текст
    sh.setFrozenRows(1);
  });
  var has = ScriptApp.getProjectTriggers().some(function (t) { return t.getHandlerFunction() === 'pollTelegram'; });
  if (!has) ScriptApp.newTrigger('pollTelegram').timeBased().everyMinutes(1).create();
  fillClients();
}

// Выдаёт PIN и код привязки Telegram тем клиентам, у кого их ещё нет
function fillClients() {
  var sh = sheet('clients');
  var rows = sh.getDataRange().getValues();
  for (var i = 1; i < rows.length; i++) {
    if (!rows[i][0]) continue;
    if (!rows[i][3]) sh.getRange(i + 1, 4).setValue(String(100000 + Math.floor(Math.random() * 900000)));
    if (!rows[i][5]) sh.getRange(i + 1, 6).setValue(Utilities.getUuid().slice(0, 8));
    if (!rows[i][2]) sh.getRange(i + 1, 3).setValue('2');
  }
}

/* ================= HTTP API ================= */

function doGet() { return out({ ok: true, service: 'booking-api' }); }

function doPost(e) {
  var req;
  try { req = JSON.parse(e.postData.contents); } catch (err) { return out({ ok: false, error: 'bad json' }); }
  var slug = String(req.slug || '').replace(/[^a-z0-9-]/g, '').slice(0, 40);
  if (!slug) return out({ ok: false, error: 'no slug' });
  try {
    switch (req.action) {
      case 'state': return out(apiState(slug, req));
      case 'book': return out(apiBook(slug, req));
      case 'login': return out(auth(slug, req.pin) ? { ok: true } : authFail(slug));
      case 'list': return out(withAuth(slug, req, apiList));
      case 'cancel': return out(withAuth(slug, req, apiCancel));
      case 'seen': return out(withAuth(slug, req, apiSeen));
      case 'services': return out(withAuth(slug, req, apiServices));
      default: return out({ ok: false, error: 'unknown action' });
    }
  } catch (err) {
    console.error(err);
    return out({ ok: false, error: 'server' });
  }
}

// Публично: только занятость боксов (без имён и телефонов) и цены
function apiState(slug, req) {
  var busy = activeBookings(slug).map(function (b) { return { box: b.box, intervals: b.intervals }; });
  return { ok: true, busy: busy, services: overrides(slug) };
}

function apiBook(slug, req) {
  var isOwner = req.source === 'phone';
  if (isOwner && !auth(slug, req.pin)) return authFail(slug);
  if (!isOwner && !rateOk('book:' + slug, 30, 600)) return { ok: false, error: 'rate' };

  var name = clean(req.name, 60), phone = clean(req.phone, 30), comment = clean(req.comment, 200);
  if (name.length < 2 || phone.replace(/\D/g, '').length < 10) return { ok: false, error: 'invalid' };
  var ints = validIntervals(req.intervals);
  if (!ints) return { ok: false, error: 'invalid' };

  var client = clientRow(slug);
  var boxes = client ? Number(client.boxes) || 1 : Math.min(Math.max(Number(req.boxes) || 1, 1), 6);

  var lock = LockService.getScriptLock();
  lock.waitLock(15000);
  try {
    var taken = activeBookings(slug);
    var box = 0;
    for (var bx = 1; bx <= boxes && !box; bx++) {
      var busy = [];
      taken.forEach(function (b) { if (b.box === bx) busy = busy.concat(b.intervals); });
      var clash = ints.some(function (i) { return busy.some(function (x) { return x.date === i.date && i.s < x.e && x.s < i.e; }); });
      if (!clash) box = bx;
    }
    if (!box) return { ok: false, error: 'taken' };

    var b = {
      id: Utilities.getUuid().slice(0, 12), slug: slug, created: new Date().toISOString(), status: 'new',
      date: ints[0].date, start: ints[0].s, end: ints[ints.length - 1].e, box: box,
      svcId: clean(req.svcId, 40), svcName: clean(req.svcName, 80), price: Math.max(0, Math.round(Number(req.price) || 0)),
      name: name, phone: phone, comment: comment, source: isOwner ? 'phone' : 'app', intervals: ints
    };
    sheet('bookings').appendRow(SHEETS.bookings.map(function (k) { return k === 'intervals' ? JSON.stringify(b.intervals) : String(b[k]); }));
    SpreadsheetApp.flush();
  } finally {
    lock.releaseLock();
  }
  notifyOwner(slug, client, 'booking', b, req);
  return { ok: true, booking: b };
}

function apiList(slug, req) {
  var client = clientRow(slug) || {};
  var list = allBookings(slug).filter(function (b) { return b.status !== 'cancelled'; });
  return {
    ok: true, bookings: list, services: overrides(slug),
    telegram: {
      connected: !!String(client.owner_chats || '').trim(),
      link: prop('TG_BOT_USERNAME') && client.link_code ? 'https://t.me/' + prop('TG_BOT_USERNAME') + '?start=' + slug + '-' + client.link_code : ''
    }
  };
}

function apiCancel(slug, req) {
  var sh = sheet('bookings'), rows = sh.getDataRange().getValues();
  for (var i = 1; i < rows.length; i++) {
    if (rows[i][0] === req.id && rows[i][1] === slug) {
      sh.getRange(i + 1, 4).setValue('cancelled');
      var b = rowToBooking(rows[i]);
      notifyOwner(slug, clientRow(slug), 'cancel', b, req);
      return { ok: true };
    }
  }
  return { ok: false, error: 'not found' };
}

function apiSeen(slug) {
  var sh = sheet('bookings'), rows = sh.getDataRange().getValues();
  for (var i = 1; i < rows.length; i++) if (rows[i][1] === slug && rows[i][3] === 'new') sh.getRange(i + 1, 4).setValue('seen');
  return { ok: true };
}

function apiServices(slug, req) {
  var ov = req.overrides && typeof req.overrides === 'object' ? req.overrides : {};
  var clean_ = {};
  Object.keys(ov).slice(0, 50).forEach(function (id) {
    var o = ov[id] || {}, r = {};
    if (o.price != null) r.price = Math.max(0, Math.round(Number(o.price) || 0));
    if (o.duration != null) r.duration = Math.min(10080, Math.max(15, Math.round(Number(o.duration) || 15)));
    if (o.hidden != null) r.hidden = !!o.hidden;
    clean_[String(id).slice(0, 40)] = r;
  });
  var sh = sheet('services'), rows = sh.getDataRange().getValues();
  for (var i = 1; i < rows.length; i++) {
    if (rows[i][0] === slug) { sh.getRange(i + 1, 2).setValue(JSON.stringify(clean_)); return { ok: true }; }
  }
  sh.appendRow([slug, JSON.stringify(clean_)]);
  return { ok: true };
}

/* ================= доступ владельца ================= */

function withAuth(slug, req, fn) { return auth(slug, req.pin) ? fn(slug, req) : authFail(slug); }

function auth(slug, pin) {
  var c = clientRow(slug);
  var fails = Number(CacheService.getScriptCache().get('fail:' + slug) || 0);
  if (!c || !c.pin || fails >= 5) return false;
  return String(pin || '') === String(c.pin);
}

function authFail(slug) {
  var cache = CacheService.getScriptCache(), k = 'fail:' + slug;
  var n = Number(cache.get(k) || 0) + 1;
  cache.put(k, String(n), 900); // 5 ошибок → блок на 15 минут
  return { ok: false, error: n >= 5 ? 'locked' : 'auth' };
}

/* ================= Telegram ================= */

function notifyOwner(slug, client, event, b, req) {
  var chats = String((client && client.owner_chats) || '').split(',').map(trim).filter(String);
  var admin = prop('ADMIN_CHAT_ID');
  if (admin && (!chats.length || prop('COPY_ALL') === '1')) chats.push(admin);
  if (!chats.length || !prop('TG_BOT_TOKEN')) return;

  var title = (client && client.name) || clean(req.clientName, 60) || slug;
  var days = b.intervals.length > 1 ? ' (' + b.intervals.length + ' дн.)' : '';
  var text = [
    '<b>' + (event === 'cancel' ? '❌ Запись отменена' : '🆕 Новая запись') + '</b> · ' + esc(title),
    '',
    '🛠 ' + esc(b.svcName) + (b.price ? ' — ' + b.price.toLocaleString('ru-RU') + ' ₽' : ''),
    '📅 ' + humanDate(b.date) + ', ' + hm(b.start) + '–' + hm(b.end) + days,
    '📦 ' + esc(clean(req.boxLabel, 20) || 'Бокс') + ' ' + b.box,
    '👤 ' + esc(b.name),
    '📞 ' + esc(b.phone)
  ];
  if (b.comment) text.push('💬 ' + esc(b.comment));
  text.push('<i>' + (b.source === 'phone' ? 'добавлена владельцем' : 'онлайн-запись') + '</i>');
  chats.forEach(function (chat) { tg('sendMessage', { chat_id: chat, text: text.join('\n'), parse_mode: 'HTML' }); });
}

// Раз в минуту читает сообщения боту: «/start slug-код» привязывает Telegram владельца к его сервису
function pollTelegram() {
  if (!prop('TG_BOT_TOKEN')) return;
  var props = PropertiesService.getScriptProperties();
  var offset = Number(props.getProperty('TG_OFFSET') || 0);
  var res = tg('getUpdates', { offset: offset, timeout: 0, allowed_updates: ['message'] });
  if (!res || !res.ok) return;
  res.result.forEach(function (u) {
    offset = u.update_id + 1;
    var m = u.message; if (!m || !m.text) return;
    var match = m.text.match(/^\/start\s+([a-z0-9-]+)-([a-f0-9]{8})$/);
    if (!match) return;
    var sh = sheet('clients'), rows = sh.getDataRange().getValues();
    for (var i = 1; i < rows.length; i++) {
      if (rows[i][0] === match[1] && rows[i][5] === match[2]) {
        var chats = String(rows[i][4] || '').split(',').map(trim).filter(String);
        if (chats.indexOf(String(m.chat.id)) < 0) chats.push(String(m.chat.id));
        sh.getRange(i + 1, 5).setValue(chats.join(','));
        tg('sendMessage', { chat_id: m.chat.id, text: '✅ Уведомления о записях в «' + rows[i][1] + '» подключены.' });
      }
    }
  });
  props.setProperty('TG_OFFSET', String(offset));
}

function tg(method, payload) {
  try {
    var r = UrlFetchApp.fetch('https://api.telegram.org/bot' + prop('TG_BOT_TOKEN') + '/' + method, {
      method: 'post', contentType: 'application/json', payload: JSON.stringify(payload), muteHttpExceptions: true
    });
    return JSON.parse(r.getContentText());
  } catch (err) { console.error(err); return null; }
}

/* ================= данные ================= */

// Таблица: привязанная к скрипту или указанная в свойстве SHEET_ID (для отдельного проекта Apps Script)
function book_() { var id = prop('SHEET_ID'); return id ? SpreadsheetApp.openById(id) : SpreadsheetApp.getActive(); }
function sheet(name) { return book_().getSheetByName(name); }

function allBookings(slug) {
  var rows = sheet('bookings').getDataRange().getValues();
  var out_ = [];
  for (var i = 1; i < rows.length; i++) if (rows[i][1] === slug) out_.push(rowToBooking(rows[i]));
  return out_;
}

function activeBookings(slug) {
  var from = Utilities.formatDate(new Date(Date.now() - 86400000), 'Europe/Moscow', 'yyyy-MM-dd');
  return allBookings(slug).filter(function (b) {
    return b.status !== 'cancelled' && b.intervals.some(function (i) { return i.date >= from; });
  });
}

function rowToBooking(r) {
  var b = {};
  SHEETS.bookings.forEach(function (k, i) { b[k] = r[i]; });
  ['start', 'end', 'box', 'price'].forEach(function (k) { b[k] = Number(b[k]) || 0; });
  try { b.intervals = JSON.parse(b.intervals); } catch (e) { b.intervals = []; }
  return b;
}

function clientRow(slug) {
  var rows = sheet('clients').getDataRange().getValues();
  for (var i = 1; i < rows.length; i++) if (rows[i][0] === slug) {
    var c = {}; SHEETS.clients.forEach(function (k, j) { c[k] = rows[i][j]; }); return c;
  }
  return null;
}

function overrides(slug) {
  var rows = sheet('services').getDataRange().getValues();
  for (var i = 1; i < rows.length; i++) if (rows[i][0] === slug) { try { return JSON.parse(rows[i][1]); } catch (e) { return {}; } }
  return {};
}

function validIntervals(arr) {
  if (!Array.isArray(arr) || !arr.length || arr.length > 30) return null;
  var today = Utilities.formatDate(new Date(), 'Europe/Moscow', 'yyyy-MM-dd');
  var limit = Utilities.formatDate(new Date(Date.now() + 90 * 86400000), 'Europe/Moscow', 'yyyy-MM-dd');
  var res = [];
  for (var i = 0; i < arr.length; i++) {
    var d = String(arr[i].date || ''), s = Number(arr[i].s), e = Number(arr[i].e);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(d) || d < today || d > limit) return null;
    if (!(s >= 0 && e <= 1440 && s < e)) return null;
    res.push({ date: d, s: s, e: e });
  }
  return res;
}

function rateOk(key, max, sec) {
  var cache = CacheService.getScriptCache(), n = Number(cache.get(key) || 0);
  if (n >= max) return false;
  cache.put(key, String(n + 1), sec);
  return true;
}

/* ================= утилиты ================= */

function out(obj) { return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON); }
// Несекретные настройки можно задать здесь. Токен бота — только в свойствах скрипта.
var DEFAULTS = {
  SHEET_ID: '',
  TG_BOT_USERNAME: '',
  ADMIN_CHAT_ID: ''
};
function prop(k) { return PropertiesService.getScriptProperties().getProperty(k) || DEFAULTS[k] || ''; }
function clean(s, n) { return String(s == null ? '' : s).replace(/[\u0000-\u001f]/g, ' ').trim().slice(0, n); }
function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
function trim(s) { return String(s).trim(); }
function pad(n) { return (n < 10 ? '0' : '') + n; }
function hm(m) { return pad(Math.floor(m / 60)) + ':' + pad(m % 60); }
function humanDate(d) {
  var p = d.split('-'), mon = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];
  var wd = ['вс', 'пн', 'вт', 'ср', 'чт', 'пт', 'сб'][new Date(+p[0], +p[1] - 1, +p[2]).getDay()];
  return Number(p[2]) + ' ' + mon[Number(p[1]) - 1] + ', ' + wd;
}

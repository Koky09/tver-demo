// Локальный двойник Google Apps Script для проверки: выполняет backend/Code.gs,
// таблица хранится в памяти, Telegram-сообщения печатаются в консоль.
//   node backend/mock-server.js            -> http://localhost:8766
// В таблице clients заранее заведены все клиенты из clients/*.json с PIN 123456.
const http = require('http');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const crypto = require('crypto');

const sheets = {};
function makeSheet(name) {
  const rows = [];
  const sh = {
    rows,
    appendRow: (r) => rows.push(r.map(String)),
    getLastRow: () => rows.length,
    getMaxRows: () => Math.max(rows.length, 1000),
    getDataRange: () => ({ getValues: () => rows.map((r) => r.slice()) }),
    getRange: (row, col) => ({
      setValue: (v) => { while (rows.length < row) rows.push([]); rows[row - 1][col - 1] = String(v); },
      setNumberFormat: () => {},
    }),
    setFrozenRows: () => {},
  };
  return sh;
}
const ss = {
  getSheetByName: (n) => sheets[n] || null,
  insertSheet: (n) => (sheets[n] = makeSheet(n)),
};
const cache = new Map();
const props = new Map(Object.entries({ TG_BOT_TOKEN: 'mock', TG_BOT_USERNAME: 'mock_bot', ADMIN_CHAT_ID: '1' }));
const sent = [];

const ctx = {
  console,
  JSON, Math, Date, String, Number, Array, Object,
  SpreadsheetApp: { getActive: () => ss, openById: () => ss, flush: () => {}, getUi: () => ({}) },
  LockService: { getScriptLock: () => ({ waitLock: () => {}, releaseLock: () => {} }) },
  CacheService: { getScriptCache: () => ({ get: (k) => (cache.has(k) ? cache.get(k) : null), put: (k, v) => cache.set(k, v) }) },
  PropertiesService: { getScriptProperties: () => ({ getProperty: (k) => props.get(k) || null, setProperty: (k, v) => props.set(k, v) }) },
  ScriptApp: { getProjectTriggers: () => [{ getHandlerFunction: () => 'pollTelegram' }], newTrigger: () => ({}) },
  Utilities: {
    getUuid: () => crypto.randomUUID(),
    formatDate: (d) => {
      const m = new Date(d.getTime() + 3 * 3600000); // Europe/Moscow
      return m.toISOString().slice(0, 10);
    },
  },
  ContentService: { createTextOutput: (s) => ({ body: s, setMimeType() { return this; } }), MimeType: { JSON: 'json' } },
  UrlFetchApp: {
    fetch: (url, opt) => {
      const p = JSON.parse(opt.payload);
      if (url.endsWith('/sendMessage')) { sent.push(p); console.log('\n[telegram -> ' + p.chat_id + ']\n' + p.text + '\n'); }
      return { getContentText: () => JSON.stringify({ ok: true, result: [] }) };
    },
  },
};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(__dirname, 'Code.gs'), 'utf8'), ctx);
vm.runInContext('setup()', ctx);

// заводим всех клиентов из clients/*.json
const clientsDir = path.join(__dirname, '..', 'clients');
for (const f of fs.readdirSync(clientsDir).filter((f) => f.endsWith('.json'))) {
  const c = JSON.parse(fs.readFileSync(path.join(clientsDir, f), 'utf8'));
  sheets.clients.appendRow([c.slug, c.name, String(c.boxes), '123456', '', 'abcdef12']);
}

http.createServer((req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  if (req.method === 'GET' && req.url === '/sent') { res.setHeader('Content-Type', 'application/json'); return res.end(JSON.stringify(sent)); }
  // отдаёт актуальный Code.gs — удобно вставлять в редактор Apps Script
  if (req.method === 'GET' && req.url === '/Code.gs') {
    res.setHeader('Access-Control-Allow-Private-Network', 'true');
    res.setHeader('Content-Type', 'text/plain; charset=utf-8');
    return res.end(fs.readFileSync(path.join(__dirname, 'Code.gs'), 'utf8'));
  }
  if (req.method === 'OPTIONS') {
    res.setHeader('Access-Control-Allow-Private-Network', 'true');
    res.setHeader('Access-Control-Allow-Headers', '*');
    return res.end();
  }
  if (req.method !== 'POST') return res.end(JSON.stringify(ctx.doGet().body ? JSON.parse(ctx.doGet().body) : {}));
  let body = '';
  req.on('data', (c) => (body += c));
  req.on('end', () => {
    const out = ctx.doPost({ postData: { contents: body } });
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    res.end(out.body);
  });
}).listen(8766, () => console.log('mock Apps Script: http://localhost:8766'));

/* Шаблон онлайн-записи для автосервиса / детейлинга.
   Все данные бизнеса — в config.js (window.CONFIG).
   С C.apiUrl записи хранятся на сервере (backend/Code.gs), без него — в localStorage (локальная проверка). */
(function () {
  'use strict';
  const C = window.CONFIG;
  const $ = (s, el = document) => el.querySelector(s);
  const app = $('#app');
  const KEY = (k) => `bk:${C.slug}:${k}`;
  const STEP = C.slotStep || 30;
  const DAYS_AHEAD = C.daysAhead || 14;
  const CITY = C.city || C.address.split(',')[0].trim(); // город для шапки и печати
  const WD = ['вс', 'пн', 'вт', 'ср', 'чт', 'пт', 'сб'];
  const WD_FULL = ['воскресенье', 'понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота'];
  const MON = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];

  document.documentElement.style.setProperty('--accent', C.accent);
  document.documentElement.style.setProperty('--accent-ink', C.accentInk || '#111');
  document.title = C.name;
  $('meta[name=theme-color]').content = getComputedStyle(document.documentElement).getPropertyValue('--chrome').trim() || '#15181c';

  /* ---------- storage ---------- */
  const load = (k, d) => { try { const v = localStorage.getItem(KEY(k)); return v ? JSON.parse(v) : d; } catch { return d; } };
  const save = (k, v) => { try { localStorage.setItem(KEY(k), JSON.stringify(v)); } catch {} };

  const REMOTE = !!C.apiUrl;
  let svcOv = REMOTE ? {} : load('services', {});
  function services(all) {
    const list = C.services.map((s) => Object.assign({}, s, svcOv[s.id] || {}));
    return all ? list : list.filter((s) => !s.hidden);
  }
  const svcById = (id) => services(true).find((s) => s.id === id);
  // Локально: все записи. С сервером: у клиента — только занятость боксов, в кабинете — записи владельца.
  let bookings = [];
  const saveBookings = () => { if (!REMOTE) save('bookings', bookings); };

  // Запрос к серверу. text/plain — чтобы браузер не делал CORS-preflight, который Apps Script не поддерживает.
  async function api(action, data) {
    const r = await fetch(C.apiUrl, { method: 'POST', headers: { 'Content-Type': 'text/plain;charset=utf-8' },
      body: JSON.stringify(Object.assign({ action, slug: C.slug }, data)) });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  }
  const pin = () => sessionStorage.getItem(KEY('pin')) || '';

  // Свежая занятость и цены с сервера
  async function loadState() {
    if (!REMOTE) return;
    const res = await api('state', {});
    if (!res.ok) throw new Error(res.error);
    bookings = res.busy.map((b) => ({ box: b.box, intervals: b.intervals, status: 'busy' }));
    svcOv = res.services || {};
  }

  /* ---------- helpers ---------- */
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const pad = (n) => String(n).padStart(2, '0');
  const ymd = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const parseYmd = (s) => { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d); };
  const addDays = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
  const hm = (min) => `${pad(Math.floor(min / 60))}:${pad(min % 60)}`;
  const rub = (n) => n.toLocaleString('ru-RU') + ' ₽';
  const priceStr = (s) => (s.priceFrom ? 'от ' : '') + rub(s.price);
  const durStr = (min) => {
    if (min >= 24 * 60 || min > dayLenMax()) { const d = daysNeeded(min); return `${d} ${plural(d, 'день', 'дня', 'дней')}`; }
    const h = Math.floor(min / 60), m = min % 60;
    return [h ? `${h} ч` : '', m ? `${m} мин` : ''].filter(Boolean).join(' ');
  };
  const plural = (n, a, b, c) => { const m10 = n % 10, m100 = n % 100; return m10 === 1 && m100 !== 11 ? a : m10 >= 2 && m10 <= 4 && (m100 < 10 || m100 >= 20) ? b : c; };
  const dateHuman = (s) => { const d = parseYmd(s); const t = ymd(new Date()); const tm = ymd(addDays(new Date(), 1));
    const base = `${d.getDate()} ${MON[d.getMonth()]}, ${WD[d.getDay()]}`; return s === t ? `сегодня, ${base}` : s === tm ? `завтра, ${base}` : base; };
  const toast = (t) => { const el = $('#toast'); el.textContent = t; el.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(() => (el.hidden = true), 2600); };
  const uid = () => Math.random().toString(36).slice(2, 10);

  /* ---------- расписание ---------- */
  function hoursFor(date) { const h = C.hours[date.getDay()]; return h ? [Math.round(h[0] * 60), Math.round(h[1] * 60)] : null; }
  function dayLenMax() { return Math.max(...Object.values(C.hours).filter(Boolean).map((h) => (h[1] - h[0]) * 60)); }
  function daysNeeded(min) { return Math.ceil(min / dayLenMax()); }
  function isOpenNow() { const n = new Date(); const h = hoursFor(n); const m = n.getHours() * 60 + n.getMinutes(); return h && m >= h[0] && m < h[1]; }
  // [8.5, 23] -> «8:30–23:00», [0, 24] -> «круглосуточно»
  const dayHours = (h) => !h ? 'выходной' : h[0] === 0 && h[1] === 24 ? 'круглосуточно' : `${hm(Math.round(h[0] * 60))}–${hm(Math.round(h[1] * 60))}`;
  function hoursText() {
    const groups = []; const order = [1, 2, 3, 4, 5, 6, 0];
    order.forEach((d) => { const key = dayHours(C.hours[d]); const g = groups[groups.length - 1];
      if (g && g.key === key) g.to = d; else groups.push({ key, from: d, to: d }); });
    if (groups.length === 1) return `ежедневно, ${groups[0].key}`;
    return groups.map((g) => `${WD[g.from]}${g.from !== g.to ? '–' + WD[g.to] : ''}: ${g.key}`).join(', ');
  }

  // «Открыто до 19:00» / «Откроется завтра в 10:00»
  function statusText() {
    const n = new Date(); const h = hoursFor(n); const m = n.getHours() * 60 + n.getMinutes();
    if (isOpenNow()) return h[0] === 0 && h[1] === 1440 ? 'Открыто круглосуточно' : h[1] === 1440 ? 'Открыто до полуночи' : `Открыто до ${hm(h[1])}`;
    if (h && m < h[0]) return `Откроется сегодня в ${hm(h[0])}`;
    const WD_IN = ['в воскресенье', 'в понедельник', 'во вторник', 'в среду', 'в четверг', 'в пятницу', 'в субботу'];
    for (let i = 1; i <= 7; i++) { const d = addDays(n, i); const hh = hoursFor(d); if (hh) return `Откроется ${i === 1 ? 'завтра' : WD_IN[d.getDay()]} в ${hm(hh[0])}`; }
    return 'Сейчас закрыто';
  }
  // Часы по дням недели, сегодняшний выделен
  function weekHtml() {
    const today = new Date().getDay();
    return `<ul class="week">${[1, 2, 3, 4, 5, 6, 0].map((d) => { const h = C.hours[d];
      return `<li ${d === today ? 'aria-current="date"' : ''}><span>${WD[d]}${d === today ? ', сегодня' : ''}</span><span class="${h ? '' : 'off'}">${dayHours(h)}</span></li>`; }).join('')}</ul>`;
  }

  // Интервалы занятости, которые даст запись услуги svc на дату date со стартом start
  function intervalsFor(svc, dateStr, start) {
    const date = parseYmd(dateStr); const h = hoursFor(date); if (!h) return null;
    if (svc.duration <= h[1] - h[0]) return start + svc.duration <= h[1] ? [{ date: dateStr, s: start, e: start + svc.duration }] : null;
    // многодневная работа: приём с утра, бокс занят несколько рабочих дней
    if (start !== h[0]) return null;
    const out = []; let left = svc.duration; let d = date; let guard = 0;
    while (left > 0 && guard++ < 30) { const hh = hoursFor(d); if (hh) { out.push({ date: ymd(d), s: hh[0], e: hh[1] }); left -= hh[1] - hh[0]; } d = addDays(d, 1); }
    return out;
  }
  const overlap = (a, b) => a.date === b.date && a.s < b.e && b.s < a.e;
  function freeBox(ints, ignoreId) {
    for (let box = 1; box <= C.boxes; box++) {
      const busy = bookings.filter((b) => b.box === box && b.status !== 'cancelled' && (ignoreId == null || b.id !== ignoreId)).flatMap((b) => b.intervals);
      if (!ints.some((i) => busy.some((x) => overlap(i, x)))) return box;
    }
    return 0;
  }
  function slotsFor(svc, dateStr) {
    const date = parseYmd(dateStr); const h = hoursFor(date); if (!h) return [];
    const now = new Date(); const isToday = dateStr === ymd(now); const nowMin = now.getHours() * 60 + now.getMinutes() + 30;
    const res = [];
    for (let t = h[0]; t < h[1]; t += STEP) {
      if (isToday && t < nowMin) continue;
      const ints = intervalsFor(svc, dateStr, t); if (!ints) continue;
      if (freeBox(ints)) res.push(t);
    }
    return res;
  }
  function nextDays() { const out = []; const t = new Date(); for (let i = 0; i < DAYS_AHEAD; i++) out.push(ymd(addDays(t, i))); return out; }

  // Возвращает запись, null (время заняли) или бросает ошибку сети
  async function createBooking({ svcId, date, start, name, phone, comment, source }) {
    const svc = svcById(svcId); const ints = intervalsFor(svc, date, start); if (!ints) return null;
    if (REMOTE) {
      const res = await api('book', { svcId, svcName: svc.name, price: svc.price, intervals: ints, boxes: C.boxes, boxLabel: C.boxLabel,
        clientName: C.name, name: name.trim(), phone: phone.trim(), comment: (comment || '').trim(), source, pin: source === 'phone' ? pin() : '' });
      if (!res.ok && res.error !== 'taken') throw new Error(res.error);
      if (res.ok) { loadState().catch(() => {}); return res.booking; } // расписание обновим в фоне — подтверждение показываем сразу
      await loadState().catch(() => {}); // время заняли — нужны свежие окна, чтобы предложить другие
      return null;
    }
    const box = freeBox(ints); if (!box) return null;
    const b = { id: uid(), svcId, svcName: svc.name, price: svc.price, date, start, end: ints[ints.length - 1].e, intervals: ints, box,
      name: name.trim(), phone: phone.trim(), comment: (comment || '').trim(), source: source || 'app', created: Date.now(), status: 'new' };
    bookings.push(b); saveBookings(); notify('booking', b); return b;
  }

  // Локальный режим: уведомление через server.py (/api/notify). С сервером уведомляет сам backend.
  function notify(event, b) {
    if (REMOTE || !location.protocol.startsWith('http')) return;
    const days = b.intervals.length > 1 ? ` (${b.intervals.length} ${plural(b.intervals.length, 'день', 'дня', 'дней')})` : '';
    const svc = svcById(b.svcId);
    fetch('/api/notify', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
      event, slug: C.slug, clientName: C.name, svcName: b.svcName, priceText: svc ? priceStr(svc) : rub(b.price),
      when: `${dateHuman(b.date)}, ${hm(b.start)}–${hm(b.intervals[b.intervals.length - 1].e)}${days}`,
      boxText: `${C.boxLabel || 'Бокс'} ${b.box}`, name: b.name, phone: b.phone, comment: b.comment, source: b.source,
    }) }).catch(() => {});
  }

  function seedDemo() {
    const list = []; const names = ['Алексей (демо)', 'Марина (демо)', 'Дмитрий (демо)', 'Сергей (демо)'];
    const svcs = C.services.filter((s) => s.duration <= 240);
    let made = 0;
    for (let i = 0; i < DAYS_AHEAD && made < 4; i++) {
      const d = addDays(new Date(), i); const h = hoursFor(d); if (!h || i === 0) continue;
      const svc = svcs[made % svcs.length]; if (!svc) break;
      const start = h[0] + 60 * (1 + (made % 3));
      if (start + svc.duration > h[1]) continue;
      list.push({ id: uid(), svcId: svc.id, svcName: svc.name, price: svc.price, date: ymd(d), start, end: start + svc.duration,
        intervals: [{ date: ymd(d), s: start, e: start + svc.duration }], box: 1 + (made % C.boxes), name: names[made],
        phone: '+7 900 000-00-0' + made, comment: '', source: 'demo', created: Date.now(), status: 'new' });
      made++;
    }
    return list;
  }

  if (!REMOTE) {
    bookings = load('bookings', null);
    if (!bookings) { bookings = seedDemo(); saveBookings(); }
  }

  /* ---------- иконки ---------- */
  const P = {
    phone: '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"/>',
    map: '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>',
    msg: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    spark: '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M19 16.5l.7 1.8 1.8.7-1.8.7-.7 1.8-.7-1.8-1.8-.7 1.8-.7z"/>',
    close: '<path d="M6 6l12 12M18 6L6 18"/>',
    send: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    check: '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.7 2.7L16 9.8"/>',
    // услуги
    bucket: '<path d="M5 9.5h14l-1.6 10.5H6.6z"/><path d="M8 9.5a4 4 0 0 1 8 0"/><path d="M9 14h6"/>',
    bubbles: '<circle cx="9" cy="14" r="5"/><circle cx="16.5" cy="7.5" r="3"/><circle cx="18" cy="16.5" r="2"/>',
    spray: '<path d="M3 9.5h6l2 1.5v2l-2 1.5H3z"/><path d="M14 9.5l6-2.5M14 12h7M14 14.5l6 2.5"/>',
    seat: '<path d="M8.5 3h4.5a2 2 0 0 1 2 2.2L14 13H8.8L7 5.3A2 2 0 0 1 8.5 3z"/><path d="M6 13h11.5l.8 4H6z"/><path d="M8 17v4M16 17v4"/>',
    diamond: '<path d="M6.5 4h11L21 9l-9 11L3 9z"/><path d="M3 9h18M10 4l-1.5 5L12 20l3.5-11L14 4"/>',
    shield: '<path d="M12 3l8 3v6c0 5-3.4 8.2-8 9-4.6-.8-8-4-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
    tint: '<path d="M3.5 18L7 6h10l3.5 12z"/><path d="M9 18l3-12M13.5 18l3-12" opacity=".55"/>',
    light: '<path d="M11 5.5a6.5 6.5 0 0 0 0 13z"/><path d="M15 8h6M15 12h6M15 16h6"/>',
    drop: '<path d="M12 3s6 6.4 6 11a6 6 0 0 1-12 0c0-4.6 6-11 6-11z"/><path d="M9.5 14.5a2.5 2.5 0 0 0 2.5 2.5"/>',
    roller: '<rect x="3" y="3.5" width="14" height="6" rx="1.5"/><path d="M17 6.5h3v5h-8v3"/><rect x="10.5" y="14.5" width="3" height="6.5" rx="1"/>',
    mute: '<path d="M4 9h4l5-4v14l-5-4H4z"/><path d="M16.5 9.5l5 5M21.5 9.5l-5 5"/>',
    gear: '<circle cx="12" cy="12" r="3.2"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M5.3 18.7l2.1-2.1M16.6 7.4l2.1-2.1"/>',
    tag: '<path d="M3 12.2V4h8.2L21 13.8 13.8 21z"/><circle cx="7.6" cy="8.6" r="1.4"/>',
  };
  const I = new Proxy({}, { get: (_, k) => `<svg class="ic" viewBox="0 0 24 24" aria-hidden="true">${P[k] || P.spark}</svg>` });
  // Иконка услуги по id (или по названию для новых услуг), задаётся в config полем iconKey
  const SVC_ICON = { wash: 'bubbles', detail: 'bucket', body: 'spray', touchless: 'spray', interior: 'seat', 'interior-full': 'seat', seats: 'seat',
    leather: 'seat', plastic: 'shield', rain: 'drop', polish: 'spark', ceramic: 'diamond', coat: 'diamond', ppf: 'shield', tint: 'tint',
    headlights: 'light', vinyl: 'roller', noise: 'mute', 'noise-doors': 'mute', engine: 'gear', presale: 'tag' };
  const SVC_WORDS = [[/мойк/i, 'bubbles'], [/химчист|салон/i, 'seat'], [/керамик|покрыт/i, 'diamond'], [/плёнк|пленк|защит/i, 'shield'],
    [/тонир/i, 'tint'], [/фар/i, 'light'], [/дожд/i, 'drop'], [/винил/i, 'roller'], [/шум/i, 'mute'], [/двигат/i, 'gear']];
  const svcIcon = (s) => I[s.iconKey || SVC_ICON[s.id] || (SVC_WORDS.find(([re]) => re.test(s.name)) || [])[1] || 'spark'];

  /* ---------- клиентская часть ---------- */
  let deferredInstall = null;
  window.addEventListener('beforeinstallprompt', (e) => { e.preventDefault(); deferredInstall = e; const el = $('#install'); if (el) el.hidden = false; });
  const standalone = () => matchMedia('(display-mode: standalone)').matches || navigator.standalone;
  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);

  // Шапка: у каждого сервиса свой характер (поле theme в clients/<slug>.json)
  function heroHtml(open, longest, street) {
    const demo = C.demo !== false ? '<span class="demo-tag">Демо-версия</span>' : '';
    const name = `<h1 style="--n:${Math.max(6, longest)}">${esc(C.name)}</h1>`;
    const tag = `<p class="tag">${esc(C.tagline)}</p>`;
    const meta = `<div class="hero-meta"><span class="status ${open ? 'open' : ''}">${statusText()}</span><span class="addr">${esc(street)}</span></div>`;
    const img = C.heroImage ? ` has-img" style="background-image:url('${esc(C.heroImage)}')` : '';
    switch (C.theme) {
      case 'atelier':
        return `<section class="hero${img}"><div class="frame">${demo}<div class="mono" aria-hidden="true">${esc(C.short)}</div>${name}${tag}${meta}</div></section>`;
      case 'race':
        return `<section class="hero${img}"><div class="stripes" aria-hidden="true"></div>
          <div class="hero-top"><div class="emblem" aria-hidden="true">${esc(C.short)}</div>${demo}</div>
          <div><h1 style="--n:${Math.max(6, longest)}">${C.name.split(/\s+/).map((w) => `<span>${esc(w)}</span>`).join(' ')}</h1>${tag}${meta}</div></section>`;
      case 'protocol':
        return `<section class="hero${img}"><div class="doc-head"><span>Карточка сервиса</span>${demo}</div>
          <div class="stamp" aria-hidden="true">${esc(C.short)}<small>${esc(CITY.length > 9 ? ({ 'Екатеринбург': 'Екб' })[CITY] || CITY.slice(0, 8) + '.' : CITY)}</small></div>
          ${name}${tag}
          <dl class="fields">
            <div><dt>Сейчас</dt><dd><span class="status ${open ? 'open' : ''}">${statusText()}</span></dd></div>
            <div><dt>Адрес</dt><dd>${esc(street)}</dd></div>
            <div><dt>Режим</dt><dd>${esc(hoursText())}</dd></div>
          </dl></section>`;
      case 'aqua':
        return `<section class="hero${img}">
          <svg class="bubbles" viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><circle cx="40" cy="60" r="14"/><circle cx="70" cy="30" r="6"/><circle cx="350" cy="80" r="22"/><circle cx="320" cy="40" r="8"/><circle cx="372" cy="150" r="7"/><circle cx="24" cy="170" r="9"/></svg>
          ${demo}<div class="emblem" aria-hidden="true">${esc(C.short)}</div>${name}${tag}${meta}
          <svg class="wave" viewBox="0 0 400 40" preserveAspectRatio="none" aria-hidden="true"><path d="M0 22 C 60 2, 120 2, 200 20 S 340 40, 400 16 V40 H0z"/></svg></section>`;
      case 'stitch':
        return `<section class="hero${img}"><div class="bignum" aria-hidden="true">${esc(C.short)}</div>
          <div class="hero-top"><div class="emblem" aria-hidden="true">${esc(C.short)}</div>${demo}</div>
          <div>${name}${tag}${meta}</div></section>`;
      case 'sticker':
        return `<section class="hero${img}">
          <div class="hero-top"><div class="emblem" aria-hidden="true">${esc(C.short)}</div>${demo}</div>
          <div>${name}${tag}${meta}</div></section>`;
      default:
        return `<section class="hero${img}">
          <svg class="crease" viewBox="0 0 400 260" preserveAspectRatio="none" aria-hidden="true"><path d="M-10 168 C 110 120, 250 112, 410 52"/><path d="M-10 182 C 120 136, 260 128, 410 70"/></svg>
          <div class="hero-top"><div class="emblem" aria-hidden="true">${esc(C.short)}</div>${demo}</div>
          <div>${name}${tag}${meta}</div></section>`;
    }
  }

  function renderClient() {
    const open = isOpenNow();
    const msgr = C.socials && (C.socials.tg || C.socials.vk || C.socials.max);
    const longest = Math.max(...C.name.split(/\s+/).map((w) => w.length), Math.ceil(C.name.length / 2)); // кегль названия: длинное слово должно влезть, а длинное название — уложиться в 2–3 строки
    const street = C.address.startsWith(CITY + ', ') ? C.address.slice(CITY.length + 2) : C.address;
    app.innerHTML = `
    <div class="wrap">
      ${heroHtml(open, longest, street)}
      <nav class="quick" aria-label="Связаться">
        <a href="tel:${esc(C.phoneHref)}">${I.phone}Позвонить</a>
        <a href="https://yandex.ru/maps/?text=${encodeURIComponent(C.mapQuery || C.address)}" target="_blank" rel="noopener">${I.map}Маршрут</a>
        ${msgr ? `<a href="${esc(C.socials.tg || C.socials.vk || C.socials.max)}" target="_blank" rel="noopener">${I.msg}Написать</a>` : `<button data-act="chat">${I.msg}Спросить</button>`}
      </nav>
      ${standalone() ? '' : `<div class="install" id="install" ${deferredInstall || isIOS ? '' : 'hidden'}>
        <div class="body"><b>Добавьте на экран</b><br><span class="muted">${isIOS ? 'Нажмите «Поделиться» → «На экран „Домой“»' : 'Запись в один тап, как в приложении'}</span></div>
        ${isIOS ? '' : '<button class="btn sm" data-act="install">Добавить</button>'}
      </div>`}
      <div class="sec-head"><h2>Услуги и цены</h2><p class="muted small">Нажмите на услугу, чтобы выбрать время</p></div>
      <div class="list">${services().map((s) => `
        <button class="svc" data-svc="${s.id}">
          <span class="ico">${svcIcon(s)}</span>
          <span class="body"><span class="name">${esc(s.name)}</span><span class="meta">${durStr(s.duration)}${s.note ? ', ' + esc(s.note) : ''}</span></span>
          <span class="lead" aria-hidden="true"></span><span class="price">${s.priceFrom ? '<small>от</small>' : ''}${rub(s.price)}</span>
        </button>`).join('')}</div>
      ${C.gallery && C.gallery.length ? `<h2>Наши работы</h2><div class="gallery">${C.gallery.map((g) => `<img loading="lazy" src="${esc(g)}" alt="">`).join('')}</div>` : ''}
      <h2>Как нас найти</h2>
      <div class="place">
        <div class="row"><span>Адрес</span><span>${esc(C.address)}</span></div>
        <div class="row"><span>Телефон</span><a href="tel:${esc(C.phoneHref)}">${esc(C.phone)}</a></div>
        <div class="row"><span>Часы работы</span>${weekHtml()}</div>
      </div>
      <div class="foot">${esc(C.name)}, онлайн-запись<br><a href="#admin">Вход для владельца</a></div>
    </div>
    <div class="bar"><div class="inner">
      <button class="btn" data-act="book">Записаться онлайн</button>
      <button class="btn chat-btn" data-act="chat" aria-label="Подобрать время с ассистентом">${I.spark}</button>
    </div></div>`;

    app.onclick = (e) => {
      const t = e.target.closest('[data-act],[data-svc]'); if (!t) return;
      if (t.dataset.svc) return openBooking({ svcId: t.dataset.svc, step: 2 });
      const a = t.dataset.act;
      if (a === 'book') openBooking({ step: 1 });
      if (a === 'chat') openChat();
      if (a === 'install' && deferredInstall) { deferredInstall.prompt(); deferredInstall = null; }
    };
  }

  /* ---------- шторка записи ---------- */
  function sheet(html) {
    closeSheet();
    const bg = document.createElement('div'); bg.className = 'sheet-bg'; bg.id = 'sheet';
    bg.innerHTML = `<div class="sheet" role="dialog" aria-modal="true" tabindex="-1"><div class="grab"></div>${html}</div>`;
    bg.addEventListener('click', (e) => { if (e.target === bg || e.target.closest('.x')) closeSheet(); });
    document.body.appendChild(bg); document.body.style.overflow = 'hidden';
    sheet.back = document.activeElement; bg.firstElementChild.focus({ preventScroll: true });
    return bg.firstElementChild;
  }
  function closeSheet() {
    const s = $('#sheet'); if (!s) return;
    s.remove(); document.body.style.overflow = '';
    if (sheet.back && document.contains(sheet.back)) sheet.back.focus({ preventScroll: true });
  }
  addEventListener('keydown', (e) => { if (e.key === 'Escape' && $('#sheet')) closeSheet(); });
  const xBtn = `<button class="x" aria-label="Закрыть">${I.close}</button>`;

  function openBooking(st) {
    const state = Object.assign({ step: 1, svcId: null, date: null, start: null, name: load('name', ''), phone: load('phone', ''), comment: '', admin: false }, st);
    const el = sheet('<div id="bk"></div>');
    const root = $('#bk', el);
    const draw = () => {
      const svc = state.svcId && svcById(state.svcId);
      const head = (title) => `<div class="sheet-head"><h3 id="sh-t">${title}</h3>${xBtn}</div>
        <ol class="steps">${['Услуга', 'Время', state.admin ? 'Клиент' : 'Контакты'].map((l, i) => `<li class="${i < state.step ? 'on' : ''}" ${i + 1 === state.step ? 'aria-current="step"' : ''}>${l}</li>`).join('')}</ol>`;
      el.setAttribute('aria-labelledby', 'sh-t');
      if (state.step === 1) {
        root.innerHTML = head('Выберите услугу') + `<div class="list">${services().map((s) => `
          <button class="svc ${s.id === state.svcId ? 'sel' : ''}" data-svc="${s.id}">
            <span class="ico">${svcIcon(s)}</span>
            <span class="body"><span class="name">${esc(s.name)}</span><span class="meta">${durStr(s.duration)}</span></span>
            <span class="price">${s.priceFrom ? '<small>от</small>' : ''}${rub(s.price)}</span></button>`).join('')}</div>`;
      } else if (state.step === 2) {
        const days = nextDays();
        if (!state.date) state.date = days.find((d) => slotsFor(svc, d).length) || days[0];
        const slots = slotsFor(svc, state.date);
        const multi = svc.duration > dayLenMax();
        const parts = [['Ночь', 0, 6 * 60], ['Утро', 6 * 60, 12 * 60], ['День', 12 * 60, 17 * 60], ['Вечер', 17 * 60, 24 * 60]]
          .map(([l, a, z]) => [l, slots.filter((t) => t >= a && t < z)]).filter(([, l]) => l.length);
        const sd = parseYmd(state.date);
        root.innerHTML = head('Дата и время') + `
          <div class="pick"><span class="ico" style="color:var(--accent-text)">${svcIcon(svc)}</span><span><b>${esc(svc.name)}</b><br>${durStr(svc.duration)}, ${priceStr(svc)}</span></div>
          <div class="days" role="group" aria-label="День">${days.map((d) => { const dt = parseYmd(d); const has = hoursFor(dt) && slotsFor(svc, d).length;
            return `<button class="day ${d === state.date ? 'sel' : ''}" data-day="${d}" ${has ? '' : 'disabled'} aria-pressed="${d === state.date}" aria-label="${dateHuman(d)}${has ? '' : ', нет мест'}"><span>${WD[dt.getDay()]}</span><b>${dt.getDate()}</b></button>`; }).join('')}</div>
          <p class="muted small" style="margin:6px 0 0">${dateHuman(state.date).replace(/^./, (c) => c.toUpperCase())}${hoursFor(sd) ? '' : ', выходной'}</p>
          ${multi ? `<p class="note" style="margin:12px 0 0">Работа займёт ${durStr(svc.duration)}. Приём автомобиля утром, мы позвоним, когда будет готово.</p>` : ''}
          ${parts.length ? parts.map(([l, list]) => `<div class="slot-group"><h4>${l}</h4><div class="slots">${list.map((t) => `<button class="slot ${t === state.start ? 'sel' : ''}" data-t="${t}" aria-pressed="${t === state.start}">${hm(t)}</button>`).join('')}</div></div>`).join('')
            : `<p class="empty" style="margin-top:14px">На этот день свободного времени нет. Выберите другой день.</p>`}
          <button class="btn" data-act="next" ${state.start == null ? 'disabled' : ''}>${state.start == null ? 'Выберите время' : `Далее: ${hm(state.start)}`}</button>
          <button class="btn ghost" data-act="back">Назад</button>`;
      } else if (state.step === 3) {
        root.innerHTML = head(state.admin ? 'Данные клиента' : 'Ваши контакты') + `
          <div class="summary">
            <div><span>Услуга</span><span>${esc(svc.name)}</span></div>
            <div><span>Когда</span><span>${dateHuman(state.date)}, ${hm(state.start)}</span></div>
            <div><span>Стоимость</span><span>${priceStr(svc)}</span></div>
          </div>
          <label class="f" for="f-name">Имя</label><input class="in" id="f-name" autocomplete="name" value="${esc(state.name)}" placeholder="Как к вам обращаться">
          <label class="f" for="f-phone">Телефон</label><input class="in" id="f-phone" type="tel" autocomplete="tel" inputmode="tel" value="${esc(state.phone)}" placeholder="+7 900 000-00-00">
          <label class="f" for="f-comm">Марка и модель авто, комментарий</label><input class="in" id="f-comm" value="${esc(state.comment)}" placeholder="Например: Kia Rio, белая">
          <button class="btn" data-act="confirm">${state.admin ? 'Добавить запись' : 'Записаться'}</button>
          <button class="btn ghost" data-act="back">Назад</button>
          ${state.admin ? '' : '<p class="muted small" style="text-align:center">Нажимая «Записаться», вы соглашаетесь на обработку контактных данных для связи по записи.</p>'}`;
      } else if (state.step === 4) {
        const b = state.booking;
        const dh = dateHuman(b.date);
        root.innerHTML = `<div class="sheet-head"><h3 id="sh-t">${state.admin ? 'Запись добавлена' : 'Талон записи'}</h3>${xBtn}</div>
          <div class="ticket" role="status">
            <div class="ticket-top">
              <span class="ok">${I.check}${state.admin ? 'Запись в расписании' : 'Вы записаны'}</span>
              <div class="ticket-when">${hm(b.start)}<span>${dh.replace(/^./, (c) => c.toUpperCase())}</span></div>
            </div>
            <div class="ticket-cut"></div>
            <div class="summary">
              <div><span>Услуга</span><span>${esc(b.svcName)}</span></div>
              <div><span>Адрес</span><span>${esc(C.address)}</span></div>
              <div><span>Телефон</span><a href="tel:${esc(C.phoneHref)}">${esc(C.phone)}</a></div>
            </div>
          </div>
          ${state.admin ? '' : '<p class="muted small" style="text-align:center">Если планы изменятся, позвоните нам.</p>'}
          <button class="btn" data-act="close">Готово</button>`;
      }
    };
    root.onclick = (e) => {
      const t = e.target.closest('[data-svc],[data-day],[data-t],[data-act]'); if (!t) return;
      if (t.dataset.svc) { state.svcId = t.dataset.svc; state.date = null; state.start = null; state.step = 2; }
      else if (t.dataset.day) { state.date = t.dataset.day; state.start = null; }
      else if (t.dataset.t) { state.start = +t.dataset.t; }
      else {
        const a = t.dataset.act;
        if (a === 'next') state.step = 3;
        if (a === 'back') state.step = state.step === 3 ? 2 : 1;
        if (a === 'close') { closeSheet(); if (state.onDone) state.onDone(); return; }
        if (a === 'confirm') return confirm_(t);
      }
      const strip = $('.days', root); const sl = strip ? strip.scrollLeft : 0; // лента дней не прыгает в начало при выборе
      draw();
      if (sl && $('.days', root)) $('.days', root).scrollLeft = sl;
    };
    async function confirm_(btn) {
      state.name = $('#f-name', root).value; state.phone = $('#f-phone', root).value; state.comment = $('#f-comm', root).value;
      if (state.name.trim().length < 2) return toast('Укажите имя');
      if (state.phone.replace(/\D/g, '').length < 10) return toast('Проверьте номер телефона');
      btn.disabled = true; btn.textContent = 'Записываем…';
      let b;
      try {
        b = await createBooking({ svcId: state.svcId, date: state.date, start: state.start, name: state.name, phone: state.phone, comment: state.comment, source: state.admin ? 'phone' : 'app' });
      } catch (err) {
        btn.disabled = false; btn.textContent = state.admin ? 'Добавить запись' : 'Записаться';
        return toast('Нет связи с сервером. Попробуйте ещё раз или позвоните нам.');
      }
      if (!b) {
        toast('Это время только что заняли — выберите другое');
        state.step = 2; state.start = null;
        if (!slotsFor(svcById(state.svcId), state.date).length) state.date = null; // день кончился — к ближайшему свободному
        return draw();
      }
      if (!state.admin) { save('name', state.name); save('phone', state.phone); }
      state.booking = b; state.step = 4; draw();
    }
    if (REMOTE) {
      root.innerHTML = '<p class="muted" style="text-align:center;padding:40px 0">Загружаем свободное время…</p>';
      loadState().then(draw, () => { toast('Нет связи с сервером'); draw(); });
    } else draw();
  }

  /* ---------- ассистент (разбор запроса без внешнего ИИ) ---------- */
  function openChat() {
    if (REMOTE) loadState().catch(() => {});
    const el = sheet(`<div class="sheet-head"><h3 id="sh-t">Подобрать время</h3>${xBtn}</div>
      <div class="chat" id="chat" aria-live="polite"></div>
      <div class="hints" id="hints">${(C.chatHints || []).map((h) => `<button>${esc(h)}</button>`).join('')}</div>
      <form class="chat-in" id="chat-f" style="margin-top:8px"><input class="in" id="chat-i" aria-label="Ваш вопрос" placeholder="Например: ${esc((C.chatHints || ['завтра после 18'])[0])}" autocomplete="off"><button class="btn" aria-label="Отправить">${I.send}</button></form>`);
    el.setAttribute('aria-labelledby', 'sh-t');
    const chat = $('#chat', el);
    const say = (who, html, opts) => {
      const m = document.createElement('div'); m.className = 'msg ' + who; m.innerHTML = html;
      if (opts && opts.length) { const o = document.createElement('div'); o.className = 'opts';
        opts.forEach((op) => { const b = document.createElement('button'); b.textContent = op.label; b.onclick = op.run; o.appendChild(b); }); m.appendChild(o); }
      chat.appendChild(m); m.scrollIntoView({ block: 'end', behavior: 'smooth' });
    };
    const ask = (text) => { say('me', esc(text)); setTimeout(() => answer(text), 250); };
    say('bot', `Здравствуйте! Я помогу записаться в «${esc(C.name)}». Напишите, что нужно и когда удобно — я подберу свободное время.`);
    $('#chat-f', el).onsubmit = (e) => { e.preventDefault(); const i = $('#chat-i', el); const v = i.value.trim(); if (v) { i.value = ''; ask(v); } };
    $('#hints', el).onclick = (e) => { if (e.target.tagName === 'BUTTON') ask(e.target.textContent); };

    function answer(raw) {
      const q = raw.toLowerCase().replace(/ё/g, 'е');
      if (/адрес|где вы|где наход|как доехать|как добраться/.test(q)) return say('bot', `Мы находимся: ${esc(C.address)}.\nЧасы работы: ${esc(hoursText())}.`);
      if (/телефон|номер|позвонить/.test(q)) return say('bot', `Наш телефон: <a href="tel:${esc(C.phoneHref)}">${esc(C.phone)}</a>`);
      if (/часы|график|режим|работаете|до скольки|во сколько открыва/.test(q) && !/запис|после|до \d/.test(q)) return say('bot', `Часы работы: ${esc(hoursText())}.`);

      const svc = matchService(q);
      const when = parseWhen(q);
      const priceAsk = /сколько стоит|цена|стоимост|почем|прайс/.test(q);
      if (svc && priceAsk && !when.day) {
        return say('bot', `${esc(svc.name)} — ${priceStr(svc)}, займёт ${durStr(svc.duration)}. Подобрать время?`,
          [{ label: 'Да, подобрать', run: () => offer(svc, { from: 0, to: 24 * 60 }) }]);
      }
      if (!svc) {
        return say('bot', 'Уточните, пожалуйста, какая услуга нужна:', services().slice(0, 8).map((s) => ({ label: s.name, run: () => { say('me', esc(s.name)); offer(s, when); } })));
      }
      offer(svc, when);
    }

    function offer(svc, when) {
      const days = nextDays(); const startIdx = when.day ? Math.max(0, days.indexOf(when.day)) : 0;
      const found = [];
      for (let i = startIdx; i < days.length && found.length < 4; i++) {
        const sl = slotsFor(svc, days[i]).filter((t) => t >= (when.from ?? 0) && t + Math.min(svc.duration, 24 * 60) <= (when.to ?? 24 * 60) + (svc.duration > dayLenMax() ? 24 * 60 : 0));
        sl.slice(0, 4 - found.length).forEach((t) => found.push({ d: days[i], t }));
        if (when.day && found.length && i === startIdx) break;
      }
      if (!found.length) return say('bot', `К сожалению, свободных окон на «${esc(svc.name)}» в ближайшие ${DAYS_AHEAD} дней по этим условиям нет. Позвоните нам: <a href="tel:${esc(C.phoneHref)}">${esc(C.phone)}</a>`);
      const exact = !when.day || found[0].d === when.day;
      say('bot', `${exact ? 'Есть свободное время' : 'В этот день мест нет, ближайшие варианты'} — ${esc(svc.name)} (${priceStr(svc)}, ${durStr(svc.duration)}):`,
        found.map((f) => ({ label: `${dateHuman(f.d).replace(/, \w\w$/, '')} ${hm(f.t)}`, run: () => openBooking({ svcId: svc.id, date: f.d, start: f.t, step: 3 }) })));
    }
  }

  function stem(w) { return w.replace(/(ами|ями|ов|ев|ей|ой|ий|ый|ая|яя|ое|ее|ые|ие|ам|ям|ах|ях|ом|ем|ую|юю|а|я|у|ю|ы|и|е|о|ь)$/, ''); }
  function matchService(q) {
    const words = q.split(/[^a-zа-я0-9]+/).filter((w) => w.length > 2).map(stem);
    let best = null, bestScore = 0;
    services().forEach((s) => {
      const keys = [...(s.keywords || []), ...s.name.toLowerCase().split(/[^a-zа-я0-9]+/)].filter((w) => w.length > 2).map(stem);
      let score = 0;
      keys.forEach((k) => { if (words.some((w) => w.startsWith(k) || k.startsWith(w) && w.length >= 4)) score++; });
      if (score > bestScore) { bestScore = score; best = s; }
    });
    return best;
  }
  function parseWhen(q) {
    const r = {}; const today = new Date();
    if (/послезавтра/.test(q)) r.day = ymd(addDays(today, 2));
    else if (/завтра/.test(q)) r.day = ymd(addDays(today, 1));
    else if (/сегодня/.test(q)) r.day = ymd(today);
    else {
      const wd = [['воскрес', 0], ['понедел', 1], ['вторник', 2], ['сред', 3], ['четверг', 4], ['пятниц', 5], ['суббот', 6]].find(([w]) => q.includes(w));
      if (wd) { let d = addDays(today, 1); while (d.getDay() !== wd[1]) d = addDays(d, 1); r.day = ymd(d); }
      const m = q.match(/(\d{1,2})[./](\d{1,2})/) || q.match(new RegExp('(\\d{1,2})\\s+(' + MON.map((x) => x.slice(0, 3)).join('|') + ')'));
      if (m) { const mon = isNaN(+m[2]) ? MON.findIndex((x) => x.startsWith(m[2])) : +m[2] - 1; let d = new Date(today.getFullYear(), mon, +m[1]);
        if (d < addDays(today, -1)) d.setFullYear(d.getFullYear() + 1); r.day = ymd(d); }
    }
    const hour = (h) => { h = +h; if (h < 8 && /вечер|дня|pm/.test(q)) h += 12; else if (h <= 7) h += 12; return h * 60; };
    let m;
    if ((m = q.match(/после\s+(\d{1,2})/))) r.from = hour(m[1]);
    if ((m = q.match(/(?:^|\s)до\s+(\d{1,2})/))) r.to = hour(m[1]);
    if ((m = q.match(/(?:^|\s)(?:в|к|на)\s+(\d{1,2})(?::(\d\d))?(?!\s*(?:числ|[./]))/)) && r.from == null) { const h = hour(m[1]); r.from = h - 30; r.to = h + 90; }
    if (/утр/.test(q)) { r.from = r.from ?? 0; r.to = r.to ?? 12 * 60; }
    if (/(днем|днём|обед)/.test(q)) { r.from = r.from ?? 12 * 60; r.to = r.to ?? 16 * 60; }
    if (/вечер/.test(q) && r.from == null) r.from = 16 * 60;
    return r;
  }

  /* ---------- кабинет владельца ---------- */
  // Загрузка записей владельца с сервера (+ обновление раз в минуту, пока открыт кабинет)
  async function adminLoad() {
    try {
      const res = await api('list', { pin: pin() });
      if (!res.ok) {
        if (res.error === 'auth' || res.error === 'locked') { sessionStorage.removeItem(KEY('pin')); return route(); }
        throw new Error(res.error);
      }
      bookings = res.bookings; svcOv = res.services || {}; adminLoad.tg = res.telegram || {};
      adminLoad.loaded = true;
    } catch (err) {
      if (!adminLoad.loaded) {
        app.innerHTML = `<div class="wrap" style="text-align:center;padding-top:60px"><p>Нет связи с сервером</p>
          <button class="btn" onclick="location.reload()">Повторить</button></div>`;
        return;
      }
      return toast('Нет связи с сервером');
    }
    if (location.hash === '#admin' && !$('#sheet') && !(document.activeElement && document.activeElement.matches('.edit-row input'))) renderAdmin();
  }
  setInterval(() => { if (REMOTE && location.hash === '#admin' && pin() && !document.hidden) adminLoad(); }, 60000);

  function renderAdmin() {
    if (REMOTE ? !pin() : sessionStorage.getItem(KEY('auth')) !== '1') return renderPin();
    if (REMOTE && !adminLoad.loaded) { app.innerHTML = '<div class="wrap"><p class="muted" style="text-align:center;padding:60px 0">Загружаем записи…</p></div>'; return adminLoad(); }
    const view = renderAdmin.view || 'day';
    const day = renderAdmin.day || ymd(new Date());
    const dayBk = bookings.filter((b) => b.status !== 'cancelled' && b.intervals.some((i) => i.date === day));
    const h = hoursFor(parseYmd(day));
    const capacity = h ? (h[1] - h[0]) * C.boxes : 0;
    const used = dayBk.flatMap((b) => b.intervals.filter((i) => i.date === day)).reduce((a, i) => a + (i.e - i.s), 0);
    const revenue = dayBk.filter((b) => b.date === day).reduce((a, b) => a + b.price, 0);
    const newCount = bookings.filter((b) => b.status === 'new' && b.source === 'app').length;

    let body = '';
    if (view === 'day') {
      body = `
        <div class="days" style="margin-bottom:14px">${nextDays().map((d) => { const dt = parseYmd(d); const n = bookings.filter((b) => b.status !== 'cancelled' && b.intervals.some((i) => i.date === d)).length;
          return `<button class="day ${d === day ? 'sel' : ''}" data-day="${d}"><span>${WD[dt.getDay()]}</span><b>${dt.getDate()}</b><span>${n ? n + ' зап.' : '·'}</span></button>`; }).join('')}</div>
        <div class="stats">
          <div class="stat"><b>${dayBk.length}</b><span>записей</span></div>
          <div class="stat"><b>${capacity ? Math.round((used / capacity) * 100) : 0}%</b><span>загрузка</span></div>
          <div class="stat"><b>${revenue ? Math.round(revenue / 1000) + 'k' : '0'}</b><span>выручка ≈, ₽</span></div>
        </div>
        ${h ? '' : '<div class="note">Выходной день по графику.</div>'}
        ${Array.from({ length: C.boxes }, (_, i) => i + 1).map((box) => {
          const list = dayBk.filter((b) => b.box === box).sort((a, b) => a.start - b.start);
          return `<div class="box-col"><h4>${esc(C.boxLabel || 'Бокс')} ${box}</h4>${list.length ? list.map((b) => {
            const it = b.intervals.find((i) => i.date === day);
            return `<div class="bk"><div><div class="t"><span class="num">${hm(it.s)}–${hm(it.e)}</span><br>${esc(b.svcName)}</div>
              <div>${esc(b.name)} · <a href="tel:${esc(b.phone.replace(/[^\d+]/g, ''))}">${esc(b.phone)}</a></div>
              ${b.comment ? `<div class="muted small">${esc(b.comment)}</div>` : ''}
              <div class="muted small">${b.source === 'app' ? 'онлайн-запись' : b.source === 'phone' ? 'добавлено вручную' : 'демо'}${b.intervals.length > 1 ? ` · ${b.intervals.length} дн.` : ''} · ${rub(b.price)}</div></div>
              <button class="btn sm danger" data-cancel="${b.id}">Отменить</button></div>`; }).join('') : '<div class="empty">Свободно</div>'}</div>`; }).join('')}
        <button class="btn" data-act="add">+ Добавить запись (звонок)</button>`;
    } else if (view === 'svc') {
      body = `<div class="note">Цены и длительность меняются здесь и сразу видны клиентам. Сохраняется автоматически.${C.demoPrices ? '<br><b>Сейчас стоят примерные цены — поправьте под свой прайс.</b>' : ''}</div>
        <div class="edit-row muted small" style="padding-top:0"><span>Услуга</span><span>Цена, ₽</span><span>Мин.</span></div>
        ${services(true).map((s) => `<div class="edit-row" data-row="${s.id}">
          <label style="display:flex;gap:8px;align-items:center"><input type="checkbox" data-f="visible" ${s.hidden ? '' : 'checked'}> ${esc(s.name)}</label>
          <input class="in" type="number" min="0" step="100" data-f="price" value="${s.price}" aria-label="Цена, ₽: ${esc(s.name)}">
          <input class="in" type="number" min="15" step="15" data-f="duration" value="${s.duration}" aria-label="Длительность, мин: ${esc(s.name)}"></div>`).join('')}`;
    } else {
      const link = location.href.split('#')[0];
      const tgInfo = adminLoad.tg || {};
      body = `<div class="summary">
          <div><span>Ссылка для клиентов</span><span></span></div>
          <input class="in" readonly value="${esc(link)}" id="lnk">
          <button class="btn sm" data-act="copy" style="margin-top:8px">Скопировать</button>
        </div>
        <p class="muted small">Поставьте ссылку в шапку профиля ВКонтакте, Telegram, Авито, на карточку в Яндекс Картах и 2ГИС. Клиент откроет её как приложение — без установки.</p>
        ${REMOTE ? `<div class="summary" style="margin-top:12px">
          <div><span>Уведомления в Telegram</span><span>${tgInfo.connected ? '✅ подключены' : 'не подключены'}</span></div>
          ${tgInfo.link ? `<a class="btn sm" href="${esc(tgInfo.link)}" target="_blank" rel="noopener" style="margin-top:8px">${tgInfo.connected ? 'Добавить ещё один Telegram' : 'Подключить Telegram'}</a>
          <p class="muted small" style="margin:8px 0 0">Откройте ссылку и нажмите «Старт» — новые записи будут приходить в течение минуты после подключения.</p>` : ''}
        </div>` : ''}
        <div class="summary" style="margin-top:12px"><div><span>${esc(C.boxLabel || 'Бокс')}ов</span><span>${C.boxes}</span></div><div><span>Часы</span><span style="text-align:right">${esc(hoursText())}</span></div></div>
        ${REMOTE ? '' : '<button class="btn ghost" data-act="reset">Сбросить демо-данные</button>'}
        <button class="btn ghost" data-act="logout">Выйти</button>`;
    }

    app.innerHTML = `<div class="wrap">
      <div class="top"><div class="top-id"><div class="emblem" aria-hidden="true">${esc(C.short)}</div><div><div class="muted small">Кабинет владельца</div><h1>${esc(C.name)}</h1></div></div><a class="btn sm ghost" href="#">Сайт</a></div>
      ${newCount ? `<div class="note alert" role="status">Новых онлайн-записей: <b>${newCount}</b></div>` : ''}
      <div class="tabs">
        <button class="${view === 'day' ? 'on' : ''}" data-view="day">Расписание</button>
        <button class="${view === 'svc' ? 'on' : ''}" data-view="svc">Услуги</button>
        <button class="${view === 'set' ? 'on' : ''}" data-view="set">Ссылка</button>
      </div>${body}</div>`;

    app.onclick = (e) => {
      const t = e.target.closest('[data-view],[data-day],[data-cancel],[data-act]'); if (!t) return;
      if (t.dataset.view) { renderAdmin.view = t.dataset.view; if (t.dataset.view === 'day') markSeen(); return renderAdmin(); }
      if (t.dataset.day) { renderAdmin.day = t.dataset.day; return renderAdmin(); }
      if (t.dataset.cancel) {
        if (!confirm('Отменить запись?')) return;
        if (REMOTE) {
          t.disabled = true;
          return api('cancel', { pin: pin(), id: t.dataset.cancel }).then((r) => { toast(r.ok ? 'Запись отменена' : 'Не удалось отменить'); adminLoad(); }, () => { t.disabled = false; toast('Нет связи с сервером'); });
        }
        const b = bookings.find((x) => x.id === t.dataset.cancel); b.status = 'cancelled'; saveBookings(); notify('cancel', b); toast('Запись отменена'); return renderAdmin();
      }
      const a = t.dataset.act;
      if (a === 'add') openBooking({ step: 1, admin: true, name: '', phone: '', onDone: REMOTE ? adminLoad : renderAdmin });
      if (a === 'copy') { const i = $('#lnk'); i.select(); (navigator.clipboard ? navigator.clipboard.writeText(i.value) : Promise.resolve(document.execCommand('copy'))).then(() => toast('Ссылка скопирована')); }
      if (a === 'reset') { if (!confirm('Удалить все записи и правки цен в этом браузере?')) return; bookings = seedDemo(); saveBookings(); save('services', {}); toast('Демо-данные сброшены'); renderAdmin(); }
      if (a === 'logout') { sessionStorage.removeItem(KEY('auth')); sessionStorage.removeItem(KEY('pin')); adminLoad.loaded = false; location.hash = ''; }
    };
    app.onchange = (e) => {
      const row = e.target.closest('[data-row]'); if (!row) return;
      const id = row.dataset.row; svcOv[id] = svcOv[id] || {};
      const f = e.target.dataset.f;
      if (f === 'visible') svcOv[id].hidden = !e.target.checked;
      else { const v = Math.max(0, Math.round(+e.target.value || 0)); if (f === 'duration' && v < 15) return toast('Минимум 15 минут'); svcOv[id][f] = v; }
      if (!REMOTE) { save('services', svcOv); return toast('Сохранено'); }
      api('services', { pin: pin(), overrides: svcOv }).then((r) => toast(r.ok ? 'Сохранено' : 'Не удалось сохранить'), () => toast('Нет связи с сервером'));
    };
    if (view === 'day') setTimeout(markSeen, 4000);
  }
  function markSeen() {
    let ch = false; bookings.forEach((b) => { if (b.status === 'new' && b.source === 'app') { b.status = 'seen'; ch = true; } });
    if (!ch) return;
    if (REMOTE) api('seen', { pin: pin() }).catch(() => {}); else saveBookings();
  }

  function renderPin() {
    const LEN = REMOTE ? 6 : 4;
    app.innerHTML = `<div class="wrap pin-screen">
      <div class="hero"><div class="emblem" aria-hidden="true">${esc(C.short)}</div></div>
      <h1>Кабинет владельца</h1>
      <p class="muted">${esc(C.name)}</p>
      <form id="pf"><div class="pin" role="group" aria-label="PIN-код">${Array.from({ length: LEN }, (_, i) => `<input class="in" inputmode="numeric" maxlength="1" type="password" aria-label="Цифра ${i + 1}">`).join('')}</div>
      <p class="muted small">${REMOTE ? 'PIN выдаётся при подключении сервиса' : `Демо-доступ: PIN ${esc(C.adminPin)}`}</p></form>
      <a class="btn ghost" href="#">← К записи</a></div>`;
    const ins = [...app.querySelectorAll('.pin input')]; ins[0].focus();
    const reset = (msg) => { toast(msg); ins.forEach((x) => { x.value = ''; x.disabled = false; }); ins[0].focus(); };
    ins.forEach((inp, i) => inp.addEventListener('input', async () => {
      if (inp.value && ins[i + 1]) ins[i + 1].focus();
      const v = ins.map((x) => x.value).join('');
      if (v.length !== LEN) return;
      if (!REMOTE) {
        if (v === String(C.adminPin)) { sessionStorage.setItem(KEY('auth'), '1'); renderAdmin(); } else reset('Неверный PIN');
        return;
      }
      ins.forEach((x) => (x.disabled = true));
      try {
        const r = await api('login', { pin: v });
        if (r.ok) { sessionStorage.setItem(KEY('pin'), v); adminLoad.loaded = false; renderAdmin(); }
        else reset(r.error === 'locked' ? 'Слишком много попыток. Подождите 15 минут' : 'Неверный PIN');
      } catch (err) { reset('Нет связи с сервером'); }
    }));
  }

  /* ---------- роутинг ---------- */
  function route() {
    closeSheet(); app.onchange = null;
    if (location.hash === '#admin') { adminLoad.loaded = false; renderAdmin(); }
    else { if (REMOTE) bookings = []; renderClient(); if (REMOTE) loadState().then(() => { if (location.hash !== '#admin' && !$('#sheet')) renderClient(); }, () => {}); }
    scrollTo(0, 0);
  }
  addEventListener('hashchange', route);
  addEventListener('storage', (e) => { if (!REMOTE && e.key === KEY('bookings')) { bookings = load('bookings', []); if (location.hash === '#admin') renderAdmin(); } });
  route();

  if ('serviceWorker' in navigator && location.protocol.startsWith('http')) navigator.serviceWorker.register('sw.js').catch(() => {});
})();

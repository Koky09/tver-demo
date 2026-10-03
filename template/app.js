/* Шаблон онлайн-записи для автосервиса / детейлинга.
   Все данные бизнеса — в config.js (window.CONFIG). Хранилище демо — localStorage. */
(function () {
  'use strict';
  const C = window.CONFIG;
  const $ = (s, el = document) => el.querySelector(s);
  const app = $('#app');
  const KEY = (k) => `bk:${C.slug}:${k}`;
  const STEP = C.slotStep || 30;
  const DAYS_AHEAD = C.daysAhead || 14;
  const WD = ['вс', 'пн', 'вт', 'ср', 'чт', 'пт', 'сб'];
  const WD_FULL = ['воскресенье', 'понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота'];
  const MON = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];

  document.documentElement.style.setProperty('--accent', C.accent);
  document.documentElement.style.setProperty('--accent-ink', C.accentInk || '#111');
  document.title = C.name;
  $('meta[name=theme-color]').content = '#0f1012';

  /* ---------- storage ---------- */
  const load = (k, d) => { try { const v = localStorage.getItem(KEY(k)); return v ? JSON.parse(v) : d; } catch { return d; } };
  const save = (k, v) => { try { localStorage.setItem(KEY(k), JSON.stringify(v)); } catch {} };

  function services(all) {
    const ov = load('services', {});
    const list = C.services.map((s) => Object.assign({}, s, ov[s.id] || {}));
    return all ? list : list.filter((s) => !s.hidden);
  }
  const svcById = (id) => services(true).find((s) => s.id === id);
  let bookings;
  const saveBookings = () => save('bookings', bookings);

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
  function hoursFor(date) { const h = C.hours[date.getDay()]; return h ? [h[0] * 60, h[1] * 60] : null; }
  function dayLenMax() { return Math.max(...Object.values(C.hours).filter(Boolean).map((h) => (h[1] - h[0]) * 60)); }
  function daysNeeded(min) { return Math.ceil(min / dayLenMax()); }
  function isOpenNow() { const n = new Date(); const h = hoursFor(n); const m = n.getHours() * 60 + n.getMinutes(); return h && m >= h[0] && m < h[1]; }
  function hoursText() {
    const groups = []; const order = [1, 2, 3, 4, 5, 6, 0];
    order.forEach((d) => { const h = C.hours[d]; const key = h ? `${h[0]}–${h[1]}` : 'выходной'; const g = groups[groups.length - 1];
      if (g && g.key === key) g.to = d; else groups.push({ key, from: d, to: d }); });
    return groups.map((g) => `${WD[g.from]}${g.from !== g.to ? '–' + WD[g.to] : ''}: ${g.key === 'выходной' ? g.key : g.key.replace(/(\d+)–(\d+)/, '$1:00–$2:00')}`).join(', ');
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
      const busy = bookings.filter((b) => b.box === box && b.status !== 'cancelled' && b.id !== ignoreId).flatMap((b) => b.intervals);
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

  function createBooking({ svcId, date, start, name, phone, comment, source }) {
    const svc = svcById(svcId); const ints = intervalsFor(svc, date, start); if (!ints) return null;
    const box = freeBox(ints); if (!box) return null;
    const b = { id: uid(), svcId, svcName: svc.name, price: svc.price, date, start, end: ints[ints.length - 1].e, intervals: ints, box,
      name: name.trim(), phone: phone.trim(), comment: (comment || '').trim(), source: source || 'app', created: Date.now(), status: 'new' };
    bookings.push(b); saveBookings(); notify('booking', b); return b;
  }

  // Уведомление в Telegram: через Google Apps Script (C.notifyUrl) на GitHub Pages
  // или через локальный server.py (/api/notify). Токен бота в код сайта не попадает.
  function notify(event, b) {
    if (!location.protocol.startsWith('http')) return;
    const days = b.intervals.length > 1 ? ` (${b.intervals.length} ${plural(b.intervals.length, 'день', 'дня', 'дней')})` : '';
    const svc = svcById(b.svcId);
    const local = /^(localhost|127\.0\.0\.1)$/.test(location.hostname);
    const url = local || !C.notifyUrl ? '/api/notify' : C.notifyUrl;
    // text/plain + no-cors: Apps Script не поддерживает CORS-preflight, ответ нам не нужен
    const opts = url === C.notifyUrl ? { mode: 'no-cors', headers: { 'Content-Type': 'text/plain;charset=utf-8' } } : { headers: { 'Content-Type': 'application/json' } };
    fetch(url, { method: 'POST', ...opts, body: JSON.stringify({
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

  bookings = load('bookings', null);
  if (!bookings) { bookings = seedDemo(); saveBookings(); }

  /* ---------- иконки ---------- */
  const I = {
    phone: '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"/></svg>',
    map: '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',
    msg: '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    spark: '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M19 17l.8 2.2L22 20l-2.2.8L19 23l-.8-2.2L16 20l2.2-.8z"/></svg>',
  };

  /* ---------- клиентская часть ---------- */
  let deferredInstall = null;
  window.addEventListener('beforeinstallprompt', (e) => { e.preventDefault(); deferredInstall = e; const el = $('#install'); if (el) el.hidden = false; });
  const standalone = () => matchMedia('(display-mode: standalone)').matches || navigator.standalone;
  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);

  function renderClient() {
    const open = isOpenNow();
    const msgr = C.socials && (C.socials.tg || C.socials.vk || C.socials.max);
    app.innerHTML = `
    <div class="wrap">
      <section class="hero ${C.heroImage ? 'has-img' : ''}" ${C.heroImage ? `style="background-image:url('${esc(C.heroImage)}')"` : ''}>
        <div class="logo">${esc(C.short)}</div>
        <h1>${esc(C.name)}</h1>
        <p>${esc(C.tagline)}</p>
        <div class="chips">
          <span class="chip ${open ? 'open' : 'closed'}">${open ? '● Открыто сейчас' : '● Сейчас закрыто'}</span>
          <span class="chip">${esc(C.address)}</span>
          ${C.demo !== false ? '<span class="chip">Демо-версия</span>' : ''}
        </div>
      </section>
      <div class="quick">
        <a href="tel:${esc(C.phoneHref)}">${I.phone}Позвонить</a>
        <a href="https://yandex.ru/maps/?text=${encodeURIComponent(C.mapQuery || C.address)}" target="_blank" rel="noopener">${I.map}Маршрут</a>
        ${msgr ? `<a href="${esc(C.socials.tg || C.socials.vk || C.socials.max)}" target="_blank" rel="noopener">${I.msg}Написать</a>` : `<button data-act="chat">${I.msg}Ассистент</button>`}
      </div>
      ${standalone() ? '' : `<div class="install" id="install" ${deferredInstall || isIOS ? '' : 'hidden'}>
        <div class="body"><b>Добавьте на экран</b><br><span class="muted">${isIOS ? 'Нажмите «Поделиться» → «На экран „Домой“»' : 'Запись в один тап, как в приложении'}</span></div>
        ${isIOS ? '' : '<button class="btn sm" data-act="install">Добавить</button>'}
      </div>`}
      <h2>Услуги и цены</h2>
      ${services().map((s) => `
        <button class="svc" data-svc="${s.id}">
          <span class="ico">${s.icon || '🚗'}</span>
          <span class="body"><span class="name">${esc(s.name)}</span><br><span class="meta">${durStr(s.duration)}${s.note ? ' · ' + esc(s.note) : ''}</span></span>
          <span class="price">${priceStr(s)}</span>
        </button>`).join('')}
      ${C.gallery && C.gallery.length ? `<h2>Наши работы</h2><div class="gallery">${C.gallery.map((g) => `<img loading="lazy" src="${esc(g)}" alt="">`).join('')}</div>` : ''}
      <h2>Как нас найти</h2>
      <div class="summary">
        <div><span>Адрес</span><span>${esc(C.address)}</span></div>
        <div><span>Телефон</span><a href="tel:${esc(C.phoneHref)}">${esc(C.phone)}</a></div>
        <div><span>Часы</span><span style="text-align:right">${esc(hoursText())}</span></div>
      </div>
      <div class="foot">${esc(C.name)} · онлайн-запись<br><a href="#admin">Вход для владельца</a></div>
    </div>
    <div class="bar"><div class="inner">
      <button class="btn" data-act="book">Записаться онлайн</button>
      <button class="btn chat-btn" data-act="chat" aria-label="Ассистент">${I.spark}</button>
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
    bg.innerHTML = `<div class="sheet"><div class="grab"></div>${html}</div>`;
    bg.addEventListener('click', (e) => { if (e.target === bg || e.target.closest('.x')) closeSheet(); });
    document.body.appendChild(bg); document.body.style.overflow = 'hidden';
    return bg.firstElementChild;
  }
  function closeSheet() { const s = $('#sheet'); if (s) s.remove(); document.body.style.overflow = ''; }

  function openBooking(st) {
    const state = Object.assign({ step: 1, svcId: null, date: null, start: null, name: load('name', ''), phone: load('phone', ''), comment: '', admin: false }, st);
    const el = sheet('<div id="bk"></div>');
    const root = $('#bk', el);
    const draw = () => {
      const svc = state.svcId && svcById(state.svcId);
      const head = (title) => `<div class="sheet-head"><h3>${title}</h3><button class="x" aria-label="Закрыть">✕</button></div>
        <div class="steps">${[1, 2, 3].map((i) => `<i class="${i <= state.step ? 'on' : ''}"></i>`).join('')}</div>`;
      if (state.step === 1) {
        root.innerHTML = head('Выберите услугу') + services().map((s) => `
          <button class="svc ${s.id === state.svcId ? 'sel' : ''}" data-svc="${s.id}">
            <span class="ico">${s.icon || '🚗'}</span>
            <span class="body"><span class="name">${esc(s.name)}</span><br><span class="meta">${durStr(s.duration)}</span></span>
            <span class="price">${priceStr(s)}</span></button>`).join('');
      } else if (state.step === 2) {
        const days = nextDays();
        if (!state.date) state.date = days.find((d) => slotsFor(svc, d).length) || days[0];
        const slots = slotsFor(svc, state.date);
        const multi = svc.duration > dayLenMax();
        root.innerHTML = head('Дата и время') + `
          <div class="muted small" style="margin-bottom:10px">${esc(svc.name)} · ${durStr(svc.duration)} · ${priceStr(svc)}</div>
          <div class="days">${days.map((d) => { const dt = parseYmd(d); const has = hoursFor(dt) && slotsFor(svc, d).length;
            return `<button class="day ${d === state.date ? 'sel' : ''}" data-day="${d}" ${has ? '' : 'disabled'}><span>${WD[dt.getDay()]}</span><b>${dt.getDate()}</b></button>`; }).join('')}</div>
          ${multi ? `<p class="muted small">Работа займёт ${durStr(svc.duration)} — приём автомобиля утром, мы позвоним, когда будет готово.</p>` : ''}
          ${slots.length ? `<div class="slots">${slots.map((t) => `<button class="slot ${t === state.start ? 'sel' : ''}" data-t="${t}">${hm(t)}</button>`).join('')}</div>`
            : `<p class="empty">На этот день свободных окон нет — выберите другой.</p>`}
          <button class="btn" data-act="next" ${state.start == null ? 'disabled' : ''}>Далее</button>
          <button class="btn ghost" data-act="back">Назад</button>`;
      } else if (state.step === 3) {
        root.innerHTML = head(state.admin ? 'Данные клиента' : 'Ваши контакты') + `
          <div class="summary">
            <div><span>Услуга</span><span>${esc(svc.name)}</span></div>
            <div><span>Когда</span><span>${dateHuman(state.date)}, ${hm(state.start)}</span></div>
            <div><span>Стоимость</span><span>${priceStr(svc)}</span></div>
          </div>
          <label class="f">Имя</label><input class="in" id="f-name" autocomplete="name" value="${esc(state.name)}" placeholder="Как к вам обращаться">
          <label class="f">Телефон</label><input class="in" id="f-phone" type="tel" autocomplete="tel" inputmode="tel" value="${esc(state.phone)}" placeholder="+7 900 000-00-00">
          <label class="f">Марка и модель авто, комментарий</label><input class="in" id="f-comm" value="${esc(state.comment)}" placeholder="Например: Kia Rio, белая">
          <button class="btn" data-act="confirm">${state.admin ? 'Добавить запись' : 'Записаться'}</button>
          <button class="btn ghost" data-act="back">Назад</button>
          ${state.admin ? '' : '<p class="muted small" style="text-align:center">Нажимая «Записаться», вы соглашаетесь на обработку контактных данных для связи по записи.</p>'}`;
      } else if (state.step === 4) {
        const b = state.booking;
        root.innerHTML = `<div class="sheet-head"><h3></h3><button class="x" aria-label="Закрыть">✕</button></div>
          <div class="done"><div class="big">✓</div><h3 style="margin:0 0 4px">${state.admin ? 'Запись добавлена' : 'Вы записаны!'}</h3>
          <p class="muted" style="margin:0">${dateHuman(b.date)}, ${hm(b.start)}</p></div>
          <div class="summary">
            <div><span>Услуга</span><span>${esc(b.svcName)}</span></div>
            <div><span>Адрес</span><span>${esc(C.address)}</span></div>
            <div><span>Телефон</span><a href="tel:${esc(C.phoneHref)}">${esc(C.phone)}</a></div>
          </div>
          ${state.admin ? '' : '<p class="muted small" style="text-align:center">Если планы изменятся — просто позвоните нам.</p>'}
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
        if (a === 'confirm') {
          state.name = $('#f-name', root).value; state.phone = $('#f-phone', root).value; state.comment = $('#f-comm', root).value;
          if (state.name.trim().length < 2) return toast('Укажите имя');
          if (state.phone.replace(/\D/g, '').length < 10) return toast('Проверьте номер телефона');
          const b = createBooking({ svcId: state.svcId, date: state.date, start: state.start, name: state.name, phone: state.phone, comment: state.comment, source: state.admin ? 'phone' : 'app' });
          if (!b) { toast('Это время только что заняли — выберите другое'); state.step = 2; state.start = null; return draw(); }
          if (!state.admin) { save('name', state.name); save('phone', state.phone); }
          state.booking = b; state.step = 4;
        }
      }
      draw();
    };
    draw();
  }

  /* ---------- ассистент (разбор запроса без внешнего ИИ) ---------- */
  function openChat() {
    const el = sheet(`<div class="sheet-head"><h3>Ассистент записи</h3><button class="x" aria-label="Закрыть">✕</button></div>
      <div class="chat" id="chat"></div>
      <div class="hints" id="hints">${(C.chatHints || []).map((h) => `<button>${esc(h)}</button>`).join('')}</div>
      <form class="chat-in" id="chat-f" style="margin-top:8px"><input class="in" id="chat-i" placeholder="Например: ${esc((C.chatHints || ['завтра после 18'])[0])}" autocomplete="off"><button class="btn">→</button></form>`);
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
  function renderAdmin() {
    if (sessionStorage.getItem(KEY('auth')) !== '1') return renderPin();
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
          <div class="stat"><b>${revenue ? Math.round(revenue / 1000) + 'k' : '0'}</b><span>≈ выручка, ₽</span></div>
        </div>
        ${h ? '' : '<div class="note">Выходной день по графику.</div>'}
        ${Array.from({ length: C.boxes }, (_, i) => i + 1).map((box) => {
          const list = dayBk.filter((b) => b.box === box).sort((a, b) => a.start - b.start);
          return `<div class="box-col"><h4>${esc(C.boxLabel || 'Бокс')} ${box}</h4>${list.length ? list.map((b) => {
            const it = b.intervals.find((i) => i.date === day);
            return `<div class="bk"><div><div class="t">${hm(it.s)}–${hm(it.e)} · ${esc(b.svcName)}</div>
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
          <input class="in" type="number" min="0" step="100" data-f="price" value="${s.price}">
          <input class="in" type="number" min="15" step="15" data-f="duration" value="${s.duration}"></div>`).join('')}`;
    } else {
      const link = location.href.split('#')[0];
      body = `<div class="summary">
          <div><span>Ссылка для клиентов</span><span></span></div>
          <input class="in" readonly value="${esc(link)}" id="lnk">
          <button class="btn sm" data-act="copy" style="margin-top:8px">Скопировать</button>
        </div>
        <p class="muted small">Поставьте ссылку в шапку профиля ВКонтакте, Telegram, Авито, на карточку в Яндекс Картах и 2ГИС. Клиент откроет её как приложение — без установки.</p>
        <div class="summary"><div><span>Боксов</span><span>${C.boxes}</span></div><div><span>Часы</span><span style="text-align:right">${esc(hoursText())}</span></div></div>
        <button class="btn ghost" data-act="reset">Сбросить демо-данные</button>
        <button class="btn ghost" data-act="logout">Выйти</button>`;
    }

    app.innerHTML = `<div class="wrap">
      <div class="top"><div><div class="muted small">Кабинет владельца</div><h1>${esc(C.name)}</h1></div><a class="btn sm ghost" href="#">Открыть как клиент</a></div>
      ${newCount ? `<div class="note" style="border-style:solid;border-color:var(--accent)">🔔 Онлайн-записей от клиентов: <b>${newCount}</b> новых</div>` : ''}
      <div class="tabs">
        <button class="${view === 'day' ? 'on' : ''}" data-view="day">Расписание</button>
        <button class="${view === 'svc' ? 'on' : ''}" data-view="svc">Услуги</button>
        <button class="${view === 'set' ? 'on' : ''}" data-view="set">Ссылка</button>
      </div>${body}</div>`;

    app.onclick = (e) => {
      const t = e.target.closest('[data-view],[data-day],[data-cancel],[data-act]'); if (!t) return;
      if (t.dataset.view) { renderAdmin.view = t.dataset.view; if (t.dataset.view === 'day') markSeen(); return renderAdmin(); }
      if (t.dataset.day) { renderAdmin.day = t.dataset.day; return renderAdmin(); }
      if (t.dataset.cancel) { if (!confirm('Отменить запись?')) return; const b = bookings.find((x) => x.id === t.dataset.cancel); b.status = 'cancelled'; saveBookings(); notify('cancel', b); toast('Запись отменена'); return renderAdmin(); }
      const a = t.dataset.act;
      if (a === 'add') openBooking({ step: 1, admin: true, name: '', phone: '', onDone: renderAdmin });
      if (a === 'copy') { const i = $('#lnk'); i.select(); (navigator.clipboard ? navigator.clipboard.writeText(i.value) : Promise.resolve(document.execCommand('copy'))).then(() => toast('Ссылка скопирована')); }
      if (a === 'reset') { if (!confirm('Удалить все записи и правки цен в этом браузере?')) return; bookings = seedDemo(); saveBookings(); save('services', {}); toast('Демо-данные сброшены'); renderAdmin(); }
      if (a === 'logout') { sessionStorage.removeItem(KEY('auth')); location.hash = ''; }
    };
    app.onchange = (e) => {
      const row = e.target.closest('[data-row]'); if (!row) return;
      const ov = load('services', {}); const id = row.dataset.row; ov[id] = ov[id] || {};
      const f = e.target.dataset.f;
      if (f === 'visible') ov[id].hidden = !e.target.checked;
      else { const v = Math.max(0, Math.round(+e.target.value || 0)); if (f === 'duration' && v < 15) return toast('Минимум 15 минут'); ov[id][f] = v; }
      save('services', ov); toast('Сохранено');
    };
    if (view === 'day') setTimeout(markSeen, 4000);
  }
  function markSeen() { let ch = false; bookings.forEach((b) => { if (b.status === 'new' && b.source === 'app') { b.status = 'seen'; ch = true; } }); if (ch) saveBookings(); }

  function renderPin() {
    app.innerHTML = `<div class="wrap" style="max-width:380px;text-align:center;padding-top:60px">
      <div class="hero" style="min-height:0;align-items:center;margin-bottom:20px"><div class="logo" style="margin:0">${esc(C.short)}</div></div>
      <h1 style="font-size:22px;margin:0">Кабинет владельца</h1>
      <p class="muted">${esc(C.name)}</p>
      <form id="pf"><div class="pin">${[0, 1, 2, 3].map(() => '<input class="in" inputmode="numeric" maxlength="1" type="password">').join('')}</div>
      <p class="muted small">Демо-доступ: PIN ${esc(C.adminPin)}</p></form>
      <a class="btn ghost" href="#">← К записи</a></div>`;
    const ins = [...app.querySelectorAll('.pin input')]; ins[0].focus();
    ins.forEach((inp, i) => inp.addEventListener('input', () => {
      if (inp.value && ins[i + 1]) ins[i + 1].focus();
      const v = ins.map((x) => x.value).join('');
      if (v.length === 4) { if (v === String(C.adminPin)) { sessionStorage.setItem(KEY('auth'), '1'); renderAdmin(); } else { toast('Неверный PIN'); ins.forEach((x) => (x.value = '')); ins[0].focus(); } }
    }));
  }

  /* ---------- роутинг ---------- */
  function route() { closeSheet(); app.onchange = null; if (location.hash === '#admin') renderAdmin(); else renderClient(); scrollTo(0, 0); }
  addEventListener('hashchange', route);
  addEventListener('storage', (e) => { if (e.key === KEY('bookings')) { bookings = load('bookings', []); if (location.hash === '#admin') renderAdmin(); } });
  route();

  if ('serviceWorker' in navigator && location.protocol.startsWith('http')) navigator.serviceWorker.register('sw.js').catch(() => {});
})();

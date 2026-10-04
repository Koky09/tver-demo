// Проверка API сервера записи на локальном двойнике (node backend/mock-server.js должен быть запущен).
const URL = 'http://localhost:8766';
const call = (body) => fetch(URL, { method: 'POST', headers: { 'Content-Type': 'text/plain' }, body: JSON.stringify(body) }).then((r) => r.json());
const day = (n) => { const d = new Date(Date.now() + n * 86400000); return d.toISOString().slice(0, 10); };
let fails = 0;
const check = (name, cond, extra) => { console.log((cond ? 'OK   ' : 'FAIL ') + name + (cond ? '' : '  ' + JSON.stringify(extra))); if (!cond) fails++; };

(async () => {
  const slug = 'detailing69'; // 1 бокс
  const d = day(3);
  const base = { slug, svcId: 'interior', svcName: 'Химчистка салона', price: 6000, boxes: 1, name: 'Иван', phone: '+7 900 111-22-33', source: 'app' };

  let r = await call({ ...base, action: 'book', intervals: [{ date: d, s: 600, e: 900 }] });
  check('запись создаётся', r.ok && r.booking.box === 1, r);
  const id = r.booking && r.booking.id;

  r = await call({ ...base, action: 'book', intervals: [{ date: d, s: 840, e: 960 }] });
  check('пересекающееся время отклоняется (1 бокс)', !r.ok && r.error === 'taken', r);

  r = await call({ ...base, action: 'book', intervals: [{ date: d, s: 900, e: 1000 }] });
  check('впритык после — разрешено', r.ok, r);

  r = await call({ ...base, action: 'book', name: 'И', intervals: [{ date: d, s: 1000, e: 1100 }] });
  check('короткое имя отклоняется', !r.ok && r.error === 'invalid', r);

  r = await call({ ...base, action: 'book', slug: 'oazis', name: '=IMPORTXML("http://x","//a")', intervals: [{ date: d, s: 600, e: 700 }] });
  const inj = await call({ action: 'list', slug: 'oazis', pin: '123456' });
  check('формула в имени сохраняется как обычный текст', r.ok && inj.bookings[0].name === '=IMPORTXML("http://x","//a")', inj.bookings && inj.bookings[0].name);

  r = await call({ ...base, action: 'book', intervals: [{ date: day(-5), s: 600, e: 700 }] });
  check('дата в прошлом отклоняется', !r.ok && r.error === 'invalid', r);

  r = await call({ ...base, action: 'book', source: 'phone', pin: '000000', intervals: [{ date: d, s: 1100, e: 1200 }] });
  check('запись «по звонку» без PIN отклоняется', !r.ok && r.error === 'auth', r);

  r = await call({ action: 'state', slug });
  check('state отдаёт занятость без личных данных', r.ok && r.busy.length === 2 && !JSON.stringify(r).includes('Иван'), r);

  r = await call({ action: 'list', slug, pin: '123456' });
  check('кабинет: список записей с PIN', r.ok && r.bookings.length === 2 && r.bookings[0].name === 'Иван', r);
  check('телефон с «+» хранится как текст, а не формула', r.ok && r.bookings[0].phone === '+7 900 111-22-33', r.bookings && r.bookings[0].phone);
  check('дата записи возвращается строкой ГГГГ-ММ-ДД', r.ok && r.bookings[0].date === d, r.bookings && r.bookings[0].date);
  check('кабинет: ссылка подключения Telegram', r.ok && r.telegram.link === 'https://t.me/mock_bot?start=detailing69-abcdef12', r.telegram);

  r = await call({ action: 'cancel', slug, pin: '123456', id });
  check('отмена записи', r.ok, r);
  r = await call({ action: 'state', slug });
  check('после отмены время освободилось', r.busy.length === 1, r);

  r = await call({ action: 'services', slug, pin: '123456', overrides: { interior: { price: 6500, duration: 240 }, rain: { hidden: true } } });
  check('сохранение цен', r.ok, r);
  r = await call({ action: 'state', slug });
  check('новые цены видны клиентам', r.services.interior.price === 6500 && r.services.rain.hidden === true, r.services);

  r = await call({ action: 'list', slug: 'nazar', pin: '123456' });
  check('PIN одного сервиса не открывает чужие записи', r.ok && r.bookings.every((b) => b.slug === 'nazar'), r);

  for (let i = 0; i < 5; i++) r = await call({ action: 'login', slug: 'oazis', pin: '999999' });
  check('5 неверных PIN — блокировка', r.error === 'locked', r);
  r = await call({ action: 'login', slug: 'oazis', pin: '123456' });
  check('во время блокировки даже верный PIN не пускает', !r.ok, r);

  const sent = await fetch(URL + '/sent').then((x) => x.json());
  check('уведомления в Telegram отправлены (3 записи + 1 отмена)', sent.length === 4 && /Новая запись/.test(sent[0].text) && sent.some((s) => /отменена/.test(s.text)), sent.length);
  check('в уведомлении об отмене правильная дата', sent.some((s) => /отменена/.test(s.text) && /октября|ноября|сентября|декабря|января/.test(s.text)), sent.map((s) => s.text.split('\n')[3]));

  console.log(fails ? `\nОшибок: ${fails}` : '\nВсе проверки пройдены');
  process.exit(fails ? 1 : 0);
})();

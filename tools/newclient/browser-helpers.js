// Помощники для встроенного браузера (javascript_tool). Вставлять целиком на нужном сайте: функции живут до перезагрузки страницы.
// Ссылки на сторонние сайты (raw.githubusercontent и т.п.) со страниц 2ГИС/Яндекса не грузятся — данные передавать литералом.

// ===== 2ГИС: открыть https://2gis.ru/<город> (moscow, ekaterinburg, kazan, khimki ...) =====
window.getState = async (url) => {  // initialState карточки или выдачи
  const h = await (await fetch(url)).text();
  const a = h.indexOf("initialState = JSON.parse('"); if (a < 0) return null;
  const st = a + 27, e = h.indexOf("')", st);
  return JSON.parse(new Function("return '" + h.slice(st, e) + "'")());
};
window.contacts = (d) => {  // {phone:[], telegram:[], whatsapp:[], vkontakte:[], website:[] ...}; t.me бывают и в website
  const out = {};
  for (const g of d.contact_groups || []) for (const c of g.contacts || [])
    (out[c.type] = out[c.type] || []).push((c.url || c.value || c.text).replace(/\?text=.*/, ''));
  return out;
};
window.search2gis = async (city, q) => {  // первые фирмы выдачи: [{id, name, address}]
  const s = await getState(`/${city}/search/` + encodeURIComponent(q));
  const p = (s && s.data.entity.profile) || {};
  return Object.keys(p).filter((k) => /^\d+$/.test(k) && p[k].data && p[k].data.name && p[k].data.address_name)
    .map((id) => ({ id, name: p[id].data.name, address: p[id].data.address_name }));
};
window.firm2gis = async (city, id) => {  // карточка: контакты, часы, число филиалов, атрибуты
  const d = (await getState(`/${city}/firm/${id}`)).data.entity.profile[id].data;
  return { name: d.name, address: d.address_name, contacts: contacts(d), schedule: d.schedule,
           branches: d.org && d.org.branch_count, attrs: (d.attribute_groups || []).flatMap((g) => g.attributes || []).map((a) => a.name) };
};
window.prices2gis = async (city, id) => {  // прайс: [{name, cat, price, max, from}] (проверено 04.10.2026; пусто, если вкладки «Цены» нет)
  const s = await getState(`/${city}/firm/${id}/tab/prices`);
  const m = (s && s.data.market) || {};
  return Object.values(m.offers || {}).map((o) => o.data).filter(Boolean).map((o) => {
    const p = ((m.products || {})[o.productId] || {}).data, pr = p && p.product, r = o.price_value && o.price_value.range;
    return { name: pr && pr.name, cat: pr && pr.categories && pr.categories[0] && pr.categories[0].label, price: o.price, max: r && r.max, from: !!(r && r.min && !r.max) };
  }).filter((x) => x.name && x.price > 1);
};
window.reviews2gis = async (id) => {  // рейтинг, число отзывов, дата последнего отзыва
  const r = await (await fetch(`https://public-api.reviews.2gis.com/2.0/branches/${id}/reviews?limit=1&sort_by=date_created&key=6e7e1929-4ea9-4a5d-8c05-d601860389bd&locale=ru_RU&fields=meta.branch_rating,meta.branch_reviews_count`)).json();
  return { rating: r.meta.branch_rating, count: r.meta.branch_reviews_count, last: r.reviews[0] && r.reviews[0].date_created };
};

// ===== Яндекс Карты: открыть https://yandex.ru/maps/ =====
window.searchYandex = async (q) => {  // первая организация выдачи: "slug/id"
  const h = await (await fetch('/maps/?text=' + encodeURIComponent(q))).text();
  const m = h.match(/\/maps\/org\/([a-z0-9_]+)\/(\d+)/); return m ? m[1] + '/' + m[2] : null;
};
window.socialsYandex = async (slugId) => {  // ТОЛЬКО соцсети самой организации (на странице есть и «похожие места», и ссылки Яндекса)
  const h = await (await fetch(`/maps/org/${slugId}/`)).text();
  const d = new DOMParser().parseFromString(h, 'text/html');
  return [...new Set([...d.querySelectorAll('.business-contacts-view__social-links a[href]')]
    .map((a) => a.getAttribute('href').replace(/\?text=.*/, '')))];
};

// ===== Telegram: открыть https://t.me/ =====
window.tgInfo = async (name) => {  // kind: личный (Send Message) | канал (View in Telegram + подписчики) | бот (Start Bot)
  const h = await (await fetch('/' + name)).text();
  const d = new DOMParser().parseFromString(h, 'text/html');
  const t = (s) => ((d.querySelector(s) || {}).textContent || '').trim().replace(/\s+/g, ' ');
  const btn = t('.tgme_action_button_new'), title = t('.tgme_page_title'), desc = t('.tgme_page_description');
  const kind = !title ? 'не найден / скрыт' : /Start Bot/i.test(btn) ? 'бот' : /Send Message/i.test(btn) ? 'личный' : 'канал';
  // в описании каналов часто есть @менеджер или другой номер — это лучший контакт
  const extra = [...new Set(desc.match(/@[A-Za-z0-9_]{4,}|\+?[78][\s(-]*9\d\d[\s)-]*\d{3}[\s-]*\d\d[\s-]*\d\d/g) || [])];
  return { name, title, kind, members: t('.tgme_page_extra'), extra };
};

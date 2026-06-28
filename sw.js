const CACHE = 'porra2026-v6';
const FILES = ['./', './index.html', './manifest.json', './imagenapp.jpg', './trofeo.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES).catch(() => {})));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ));
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    fetch(e.request, { cache: 'no-store' })
      .then(resp => { caches.open(CACHE).then(c => c.put(e.request, resp.clone())); return resp; })
      .catch(() => caches.match(e.request))
  );
});

// ── Push notifications ──
self.addEventListener('push', e => {
  let data = { title: '🏆 Porra Mundial 2026', body: 'Tienes novedades en la porra.' };
  try { data = e.data.json(); } catch(_) {}
  e.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: data.icon || 'imagenapp.jpg',
      badge: 'imagenapp.jpg',
      vibrate: [200, 100, 200],
      data: { url: data.url || './' }
    })
  );
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  const url = e.notification.data?.url || './';
  e.waitUntil(clients.matchAll({ type: 'window' }).then(cs => {
    const c = cs.find(x => x.url.includes('porra') || x.url.includes('index'));
    if (c) { c.focus(); return; }
    clients.openWindow(url);
  }));
});

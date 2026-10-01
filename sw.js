const CACHE = 'loterias-v1';
const SHELL = ['./', 'index.html', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png', 'Loterias_Analyzer_Icon.png', 'euromillions.jsonl', 'eurodreams.jsonl'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

const keyFor = url => {
  const u = new URL(url);
  const file = u.pathname.split('/').pop();
  return file.endsWith('.jsonl') ? new Request(file) : new Request(u.origin + u.pathname);
};

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const key = keyFor(e.request.url);
  e.respondWith(
    fetch(e.request).then(res => {
      if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(key, copy)); }
      return res;
    }).catch(() => caches.match(key).then(r => r || caches.match('index.html')))
  );
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil(self.clients.matchAll({ type: 'window' }).then(cs => cs.length ? cs[0].focus() : self.clients.openWindow('./')));
});

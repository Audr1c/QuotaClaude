/* sw.js: makes the widget an installable app (Chrome / Edge: "Install app") that still opens without the server.
   Network first for everything: the data must be fresh. The last good answer of each file is kept, and served only
   when the server cannot be reached (the page then shows the age of its last reading, as usual). */
const CACHE = "cu-v1";
const SHELL = ["index.html", "css/style.css", "js/diag.js", "js/i18n.js", "js/model.js", "js/gauge.js", "js/views.js",
  "js/charts.js", "js/app.js", "favicon.svg", "favicon.png", "manifest.webmanifest", "icon-192.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;     // POST /api/refresh goes straight through
  if (url.pathname.startsWith("/api/")) return;
  const key = url.origin + url.pathname;                                         // ignore ?t= and ?lang=
  e.respondWith(fetch(e.request).then(r => {
    if (r.ok) { const copy = r.clone(); caches.open(CACHE).then(c => c.put(key, copy)); }
    return r;
  }).catch(() => caches.match(key).then(r => r || Response.error())));
});

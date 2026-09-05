const CACHE = "pedido-v2";
const ASSETS = [
    "../index.html",
    "manifest.json",
    "icon-192.png",
    "icon-512.png"
];

self.addEventListener("install", function(e) {
    e.waitUntil(
        caches.open(CACHE).then(function(c) {
            return c.addAll(ASSETS);
        }).catch(function() {})
    );
    self.skipWaiting();
});

self.addEventListener("activate", function(e) {
    e.waitUntil(
        caches.keys().then(function(keys) {
            return Promise.all(
                keys.filter(function(k) { return k !== CACHE; })
                    .map(function(k) { return caches.delete(k); })
            );
        })
    );
    self.clients.claim();
});

self.addEventListener("fetch", function(e) {
    e.respondWith(
        caches.match(e.request).then(function(r) {
            return r || fetch(e.request).catch(function() {
                return new Response("Offline", { status: 503 });
            });
        })
    );
});

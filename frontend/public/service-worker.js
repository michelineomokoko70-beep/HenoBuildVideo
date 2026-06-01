const CACHE_NAME = 'henobuild-downloader-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/index.html',
  '/manifest.json',
  '/favicon.ico',
  '/logo192.png',
  '/logo512.png'
];

// Install Event
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('Service Worker: Caching App Shell');
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
  self.skipWaiting();
});

// Activate Event
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keyList) => {
      return Promise.all(
        keyList.map((key) => {
          if (key !== CACHE_NAME) {
            console.log('Service Worker: Clearing Old Cache', key);
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch Event
self.addEventListener('fetch', (event) => {
  // Toujours laisser les requêtes d'API aller directement au réseau
  if (event.request.url.includes('/api/')) {
    return;
  }
  
  event.respondWith(
    caches.match(event.request).then((response) => {
      // Retourne la ressource en cache ou va la chercher sur le réseau
      return response || fetch(event.request).then((fetchResponse) => {
        // Ne mettre en cache que les requêtes GET valides (hors extension Chrome / requêtes internes)
        if (event.request.method === 'GET' && fetchResponse.status === 200 && event.request.url.startsWith(self.location.origin)) {
          const cacheCopy = fetchResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, cacheCopy);
          });
        }
        return fetchResponse;
      });
    }).catch(() => {
      // Fallback si hors ligne
      if (event.request.mode === 'navigate') {
        return caches.match('/index.html');
      }
    })
  );
});

const CACHE_NAME = 'happysnack-v1';
const urlsToCache = [
  '/',
  '/index.html',
  '/manifest.json',
  '/style.css'
];

// Установка Service Worker
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
  );
});

// Активация Service Worker
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Обработка запросов (кеширование)
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        // Возвращаем из кеша если есть
        if (response) {
          return response;
        }
        
        // Иначе делаем запрос
        return fetch(event.request).then((response) => {
          // Не кешируем если не OK
          if (!response || response.status !== 200 || response.type === 'error') {
            return response;
          }
          
          // Клонируем и кешируем
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
          
          return response;
        });
      })
  );
});

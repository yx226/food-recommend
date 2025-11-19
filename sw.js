// sw.js - 饭点子PWA Service Worker
const CACHE_NAME = 'fandianzi-v1.0.0';
const urlsToCache = [
  '/',
  '/static/flatui/dist/css/flat-ui.css',
  '/static/flatui/dist/css/vendor/bootstrap.min.css',
  '/static/flatui/other_rely/jquery-3.3.1.min.js',
  '/static/flatui/other_rely/popper.min.js',
  '/static/flatui/dist/scripts/flat-ui.js',
  // 添加你其他重要的静态资源
];

// 安装阶段
self.addEventListener('install', function(event) {
  console.log('饭点子Service Worker安装中...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        console.log('饭点子缓存已打开');
        return cache.addAll(urlsToCache);
      })
      .then(function() {
        console.log('饭点子所有资源缓存完成');
        return self.skipWaiting();
      })
  );
});

// 激活阶段
self.addEventListener('activate', function(event) {
  console.log('饭点子Service Worker激活');
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(cacheName) {
          if (cacheName !== CACHE_NAME) {
            console.log('删除旧缓存:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(function() {
      return self.clients.claim();
    })
  );
});

// 拦截请求
self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request)
      .then(function(response) {
        // 如果缓存中有，返回缓存内容
        if (response) {
          return response;
        }
        
        // 否则从网络请求
        return fetch(event.request)
          .then(function(response) {
            // 检查是否是有效响应
            if(!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }
            
            // 克隆响应
            var responseToCache = response.clone();
            
            caches.open(CACHE_NAME)
              .then(function(cache) {
                cache.put(event.request, responseToCache);
              });
              
            return response;
          })
          .catch(function() {
            // 网络请求失败，可以返回一个离线页面
            // 这里简单返回错误
            return new Response('网络连接失败', {
              status: 408,
              statusText: 'Network Timeout'
            });
          });
      })
  );
});
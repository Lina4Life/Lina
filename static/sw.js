/* Service worker to receive push events and show notifications */
self.addEventListener('push', function(event) {
  let data = {};
  if (event.data) {
    try { data = event.data.json(); } catch(e){ data = { body: event.data.text() }; }
  }
  const title = (data.title) ? data.title : 'Lina App';
  const options = {
    body: data.body || 'You have a new message',
    icon: '/static/icon-192.png',
    badge: '/static/icon-192.png',
    data: data
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  event.waitUntil(clients.matchAll({type:'window'}).then(list => {
    for (const client of list) {
      if (client.url && 'focus' in client) return client.focus();
    }
    if (clients.openWindow) return clients.openWindow('/');
  }));
});

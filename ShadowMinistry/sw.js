self.addEventListener('install', (e) => {
  console.log('Shadow Ministry SW Installed');
});

self.addEventListener('fetch', (e) => {
  // اتركها فارغة للسماح بمرور البيانات الحية من Render
});
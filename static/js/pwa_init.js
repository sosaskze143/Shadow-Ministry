if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then(reg => console.log('Sovereign System Service Worker Registered'))
            .catch(err => console.log('Service Worker Selection Failed', err));
    });
}

// منع سحب الصفحة لتحديثها (اختياري للحفاظ على تجربة التطبيق)
window.addEventListener('touchstart', function(e) {
    if (e.touches.length > 1) e.preventDefault();
}, {passive: false});
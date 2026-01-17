// --- إدارة القائمة الجانبية ---
function toggleMenu() {
    const menu = document.getElementById('sideMenu');
    if (menu) {
        menu.classList.toggle('open');
    }
}

// إغلاق القائمة عند النقر في أي مكان خارجها
document.addEventListener('click', function(event) {
    const menu = document.getElementById('sideMenu');
    const trigger = document.querySelector('.menu-trigger');
    
    if (menu && menu.classList.contains('open')) {
        if (!menu.contains(event.target) && !trigger.contains(event.target)) {
            menu.classList.remove('open');
        }
    }
});

// --- محرك البحث الفوري للمشرف ---
function filterTable() {
    const input = document.getElementById('adminSearch');
    const filter = input.value.toLowerCase();
    const rows = document.getElementById('userRows').getElementsByTagName('tr');

    for (let i = 0; i < rows.length; i++) {
        const rowText = rows[i].textContent.toLowerCase();
        if (rowText.includes(filter)) {
            rows[i].style.display = "";
            rows[i].style.animation = "fadeIn 0.3s";
        } else {
            rows[i].style.display = "none";
        }
    }
}

// --- نظام مراقبة الخمول (تسجيل خروج تلقائي بعد 10 دقائق) ---
let idleTime = 0;
const idleInterval = setInterval(() => {
    idleTime++;
    if (idleTime >= 10) { // 10 دقائق
        window.location.href = "/logout";
    }
}, 60000); // تحديث كل دقيقة

window.onmousemove = window.onkeypress = () => { idleTime = 0; };
async function initCamera() {
    const video = document.getElementById('webcam');
    const status = document.getElementById('status-bar');

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
            video: { facingMode: "user", width: 1280, height: 720 } 
        });
        video.srcObject = stream;
        status.innerText = "البصمة الحيوية جاهزة للتحليل";
        status.style.color = "#00ff88";
    } catch (err) {
        status.innerText = "خطأ: يرجى السماح بالوصول للكاميرا";
        status.style.color = "#ff4d4d";
        console.error("Camera Error: ", err);
    }
}

// استدعاء الكاميرا عند تحميل الصفحة
if (document.getElementById('webcam')) {
    initCamera();
}

// دالة محاكاة التحليل (ترتبط بـ Backend)
function startScanning() {
    const status = document.getElementById('status-bar');
    const btn = document.getElementById('capture-btn');
    
    btn.disabled = true;
    btn.innerText = "جاري المعالجة...";
    status.innerText = "يتم الآن مطابقة ملامح الوجه مع السجل المدني...";
    
    // محاكاة وقت المعالجة
    setTimeout(() => {
        window.location.href = "/auth_success";
    }, 3500);
}
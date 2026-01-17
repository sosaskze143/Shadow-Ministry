async function startCamera() {
    const video = document.getElementById('video');
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = stream;
    } catch (err) {
        alert("يرجى السماح بالوصول للكاميرا لإتمام التحقق");
    }
}

async function captureAndVerify() {
    const video = document.getElementById('video');
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    canvas.getContext('2d').drawImage(video, 0, 0);
    const imageData = canvas.toDataURL('image/jpeg');

    const response = await fetch('/api/process_face', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: imageData })
    });

    const result = await response.json();
    if (result.status === "success") {
        window.location.href = "/user_home";
    } else {
        alert("فشل التعرف على الوجه. يرجى المحاولة مرة أخرى.");
    }
}

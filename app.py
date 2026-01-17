import os
import smtplib
import asyncio
import base64
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from tinydb import TinyDB, Query
import telegram
import cv2  # للمطابقة الحقيقية
import numpy as np

app = Flask(__name__)
app.secret_key = "SHADOW_MINISTRY_SOVEREIGN_KEY_2026"
app.permanent_session_lifetime = timedelta(minutes=10)

# --- إعدادات قاعدة البيانات والملفات ---
DB_FILE = 'ministry_data.json'
db = TinyDB(DB_FILE)
users_table = db.table('users')
FACES_FOLDER = 'static/faces'
if not os.path.exists(FACES_FOLDER):
    os.makedirs(FACES_FOLDER)

# --- إعدادات الربط ---
TELEGRAM_TOKEN = "8415250551:AAEv6B1Evhc_NNKhH1o76PBUl1UNVMYVT2U"
ADMIN_CHAT_ID = "8338737071"
EMAIL_USER = "azlal.gov@gmail.com"
EMAIL_PASS = "mhhuliujcrqkzccg"

# --- محرك التنبيهات الحقيقي ---
async def send_telegram_async(msg):
    try:
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg, parse_mode='HTML')
    except Exception as e: print(f"Telegram Log Error: {e}")

def notify_admin(msg):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(send_telegram_async(msg))

# --- محرك التعرف على الوجه الحقيقي (مطابقة البكسل) ---
def verify_face_match(stored_img_path, captured_image_data):
    try:
        # تحويل الصورة الملتقطة من Base64 إلى OpenCV
        encoded_data = captured_image_data.split(',')[1]
        nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
        img_captured = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        
        # تحميل الصورة المخزنة
        img_stored = cv2.imread(stored_img_path, cv2.IMREAD_GRAYSCALE)
        
        if img_stored is None: return False
        
        # تغيير الحجم للمقارنة
        img_captured = cv2.resize(img_captured, (200, 200))
        img_stored = cv2.resize(img_stored, (200, 200))
        
        # استخدام تقنية Template Matching للمقارنة الحقيقية
        res = cv2.matchTemplate(img_captured, img_stored, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        
        return max_val > 0.6  # إذا كانت المطابقة أكثر من 60%
    except Exception as e:
        print(f"Face Matching Error: {e}")
        return False

# --- المسارات (Routes) ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        id_num = request.form.get('id_number')
        pw = request.form.get('password')
        User = Query()
        user = users_table.get(User.id_num == id_num)
        
        if user and user['pw'] == pw:
            if user.get('is_blocked') == "1":
                return render_template('blocked.html')
            session['temp_user_id'] = id_num
            return redirect(url_for('face_verify'))
    return render_template('user_login.html')

@app.route('/face_verify')
def face_verify():
    return render_template('face_verify.html')

@app.route('/api/verify_face', methods=['POST'])
def api_verify_face():
    data = request.get_json()
    id_num = session.get('temp_user_id')
    image_data = data.get('image')
    
    if not id_num: return jsonify({"status": "error", "message": "الجلسة منتهية"})
    
    stored_path = os.path.join(FACES_FOLDER, f"{id_num}.jpg")
    
    # المطابقة الحقيقية
    if verify_face_match(stored_path, image_data):
        session['user_id'] = id_num
        notify_admin(f"🔓 <b>دخول ناجح بالبصمة الحيوية</b>\n🆔: {id_num}\n📅: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "fail", "message": "البصمة الحيوية غير متطابقة!"})

@app.route('/user_home')
def user_home():
    if 'user_id' not in session: return redirect(url_for('index'))
    User = Query()
    user = users_table.get(User.id_num == session['user_id'])
    return render_template('user_home.html', user=user)

# --- إدارة المشرف ---

@app.route('/admin/dashboard')
def admin_dashboard():
    # التحقق من الجلسة هنا (اختياري)
    all_users = users_table.all()
    return render_template('admin_dashboard.html', users=all_users)

@app.route('/api/add_user', methods=['POST'])
def api_add_user():
    data = request.form.to_dict()
    file = request.files.get('face_img')
    
    if file:
        file_path = os.path.join(FACES_FOLDER, f"{data['id_num']}.jpg")
        file.save(file_path)
    
    data['is_blocked'] = "0"
    data['expiry'] = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    users_table.insert(data)
    
    notify_admin(f"🆕 <b>إضافة مواطن جديد</b>\n👤: {data['fname_ar']} {data['lname_ar']}\n🆔: {data['id_num']}")
    return redirect(url_for('admin_dashboard'))

@app.route('/api/update_user/<id_num>', methods=['POST'])
def api_update_user(id_num):
    User = Query()
    new_data = request.form.to_dict()
    users_table.update(new_data, User.id_num == id_num)
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # التشغيل محلياً أو على Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
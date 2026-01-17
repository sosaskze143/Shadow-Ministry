import os
import json
import base64
import asyncio
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
from tinydb import TinyDB, Query
import telegram
import cv2
import numpy as np

app = Flask(__name__)
app.secret_key = "SHADOW_MINISTRY_SUPREME_KEY_2026"
app.permanent_session_lifetime = timedelta(minutes=15)

# --- 1. ميكانيكية الإنشاء التلقائي للمجلدات المطلوبة ---
def initialize_system():
    required_folders = [
        'static/faces',      # صور البصمة الحيوية
        'static/uploads',    # المرفقات العامة
        'static/css',        # التنسيق
        'static/js',         # البرمجيات
        'static/images'      # الشعارات
    ]
    for folder in required_folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"✔️ Created folder: {folder}")

initialize_system()

# --- إعدادات قواعد البيانات والملفات ---
DB_FILE = 'ministry_database.json'
db = TinyDB(DB_FILE)
users_table = db.table('users')
FACES_FOLDER = os.path.join('static', 'faces')

# --- إعدادات الربط الخارجي ---
TELEGRAM_TOKEN = "8415250551:AAEv6B1Evhc_NNKhH1o76PBUl1UNVMYVT2U"
ADMIN_CHAT_ID = "8338737071"

# --- 2. دوال الأمان والربط السيادي ---
async def send_tg_msg(text):
    try:
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=text, parse_mode='HTML')
    except Exception as e: 
        print(f"TG Error: {e}")

def notify(msg):
    try:
        # لتجنب مشاكل الـ Event Loop في Flask
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_tg_msg(msg))
        loop.close()
    except Exception as e:
        print(f"Notify Error: {e}")

def verify_face(stored_id, captured_base64):
    try:
        # معالجة الصورة القادمة من المتصفح
        encoded_data = captured_base64.split(',')[1]
        nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
        img_captured = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        
        # جلب الصورة الأصلية المخزنة
        stored_path = os.path.join(FACES_FOLDER, f"{stored_id}.jpg")
        img_stored = cv2.imread(stored_path, cv2.IMREAD_GRAYSCALE)
        
        if img_stored is None: return False
        
        # معالجة الصور للمطابقة
        img_captured = cv2.resize(img_captured, (250, 250))
        img_stored = cv2.resize(img_stored, (250, 250))
        
        # المطابقة باستخدام خوارزمية النسيج (Correlation Coefficient)
        res = cv2.matchTemplate(img_captured, img_stored, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        
        return max_val > 0.65 # نسبة نجاح المطابقة 65% فأعلى
    except:
        return False

# --- 3. المسارات العامة والـ PWA ---

@app.route('/')
def index(): 
    return render_template('index.html')

@app.route('/sw.js')
def sw(): 
    return send_from_directory('.', 'sw.js')

@app.route('/manifest.json')
def manifest():
    return send_from_directory('.', 'manifest.json')

# --- 4. بوابة المواطن ---

@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        id_num = request.form.get('id_number')
        pw = request.form.get('password')
        user = users_table.get(Query().id_num == id_num)
        if user and user['pw'] == pw:
            if user.get('is_blocked') == "1": 
                return render_template('blocked.html')
            session['temp_id'] = id_num
            return redirect(url_for('face_verify'))
    return render_template('user_login.html')

@app.route('/face_verify')
def face_verify(): 
    return render_template('face_verify.html')

@app.route('/api/verify_face', methods=['POST'])
def api_verify_face():
    data = request.json
    temp_id = session.get('temp_id')
    if not temp_id or not data: return jsonify({"status": "error"})
    
    if verify_face(temp_id, data['image']):
        session.permanent = True
        session['user_id'] = temp_id
        notify(f"🔓 <b>دخول ناجح</b>\nالمواطن: {temp_id}\n📅: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        return jsonify({"status": "success"})
    return jsonify({"status": "fail"})

@app.route('/user_home')
def user_home():
    if 'user_id' not in session: return redirect('/')
    u = users_table.get(Query().id_num == session.get('user_id'))
    return render_template('user_home.html', user=u)

@app.route('/my_data')
def my_data():
    if 'user_id' not in session: return redirect('/')
    u = users_table.get(Query().id_num == session.get('user_id'))
    return render_template('my_data.html', user=u)

@app.route('/sites')
def sites(): 
    if 'user_id' not in session: return redirect('/')
    return render_template('sites.html')

# --- 5. بوابة الإدارة والسيطرة ---

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        # نظام دخول الأدمن الافتراضي
        if request.form.get('username') == 'admin' and request.form.get('password') == 'admin':
            return render_template('admin_otp.html')
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html', users=users_table.all())

@app.route('/admin/add_user')
def add_user_page(): 
    return render_template('add_user.html')

@app.route('/api/add_user', methods=['POST'])
def api_add_user():
    data = request.form.to_dict()
    file = request.files.get('face_img')
    if file: 
        file.save(os.path.join(FACES_FOLDER, f"{data['id_num']}.jpg"))
    
    data['is_blocked'] = "0"
    data['expiry'] = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
    users_table.insert(data)
    
    notify(f"🆕 <b>مواطن جديد</b>\n👤: {data.get('fname_ar')} {data.get('lname_ar')}\n🆔: {data['id_num']}")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit_user/<id_num>')
def edit_user(id_num):
    u = users_table.get(Query().id_num == id_num)
    return render_template('edit_user.html', user=u)

@app.route('/api/update_user/<id_num>', methods=['POST'])
def api_update_user(id_num):
    users_table.update(request.form.to_dict(), Query().id_num == id_num)
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/notifications')
def admin_notifications(): 
    return render_template('admin_notifications.html')

@app.route('/api/send_broadcast', methods=['POST'])
def api_send_broadcast():
    msg = request.form.get('message')
    reg = request.form.get('target_region')
    notify(f"📢 <b>تعميم رسمي ({reg})</b>\n{msg}")
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# --- 6. التشغيل النهائي ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

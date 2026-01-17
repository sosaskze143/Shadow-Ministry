import os
import json
import base64
import random
import requests
import cv2
import numpy as np
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
from tinydb import TinyDB, Query

app = Flask(__name__)
app.secret_key = "SHADOW_MINISTRY_SUPREME_VAULT_2026"

# إعدادات الجلسة (Session) - خروج بعد 10 دقائق من الخمول
app.permanent_session_lifetime = timedelta(minutes=10)

# --- 1. الإعدادات والبيانات السيادية ---
TELEGRAM_TOKEN = "8415250551:AAEv6B1Evhc_NNKhH1o76PBUl1UNVMYVT2U"
ADMIN_CHAT_ID = "8338737071"
EMAIL_USER = "azlal.gov@gmail.com"
EMAIL_PASS = "mhhuliujcrqkzccg"

db = TinyDB('shadow_ministry.json')
users_table = db.table('users')
FACES_FOLDER = 'static/faces'

# إنشاء المجلدات إذا لم تكن موجودة
for folder in ['static/faces', 'static/css', 'static/js', 'static/images']:
    if not os.path.exists(folder): os.makedirs(folder)

# --- 2. دوال التواصل والأمن ---

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={'chat_id': ADMIN_CHAT_ID, 'text': msg, 'parse_mode': 'HTML'}, timeout=5)
    except: pass

def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
    except Exception as e: print(f"Email Error: {e}")

def verify_face_match(stored_id, captured_image_b64):
    try:
        # تحويل الصورة الملتقطة من الكاميرا
        header, encoded = captured_image_b64.split(",", 1)
        data = base64.b64decode(encoded)
        nparr = np.frombuffer(data, np.uint8)
        img_captured = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        
        # جلب الصورة الأصلية المخزنة للمستخدم
        stored_path = os.path.join(FACES_FOLDER, f"{stored_id}.jpg")
        img_stored = cv2.imread(stored_path, cv2.IMREAD_GRAYSCALE)
        
        if img_stored is None: return False
        
        # مطابقة هندسية (Resize & Match)
        img_captured = cv2.resize(img_captured, (300, 300))
        img_stored = cv2.resize(img_stored, (300, 300))
        res = cv2.matchTemplate(img_captured, img_stored, cv2.TM_CCOEFF_NORMED)
        return cv2.minMaxLoc(res)[1] > 0.70 # نسبة دقة 70%
    except: return False

# --- 3. مسارات بوابة الدخول (المواطن) ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        identifier = request.form.get('identifier') # جوال أو هوية
        pw = request.form.get('password')
        User = Query()
        user = users_table.get((User.id_num == identifier) | (User.phone == identifier))
        
        if user and user['password'] == pw:
            if user.get('blocked', False):
                return render_template('blocked.html')
            session['pre_verify_id'] = user['id_num']
            return redirect(url_for('face_verify'))
        return render_template('user_login.html', error="خطأ في البيانات")
    return render_template('user_login.html')

@app.route('/face_verify')
def face_verify():
    if 'pre_verify_id' not in session: return redirect('/')
    return render_template('face_verify.html')

@app.route('/api/process_face', methods=['POST'])
def process_face():
    data = request.json
    id_num = session.get('pre_verify_id')
    if verify_face_match(id_num, data['image']):
        session.permanent = True
        session['user_id'] = id_num
        # إرسال تلجرام عند الدخول
        ip = request.remote_addr
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        send_telegram(f"🔓 <b>دخول جديد</b>\nالمواطن: {id_num}\nالتوقيت: {now}\nIP: {ip}")
        return jsonify({"status": "success"})
    return jsonify({"status": "fail"})

# --- 4. لوحة تحكم المواطن ---

@app.route('/user_home')
def user_home():
    if 'user_id' not in session: return redirect('/')
    user = users_table.get(Query().id_num == session['user_id'])
    
    # تحديث تلقائي لتاريخ انتهاء البطاقة
    expiry_date = datetime.strptime(user['expiry'], "%Y-%m-%d")
    if datetime.now() > expiry_date:
        new_expiry = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        users_table.update({'expiry': new_expiry}, Query().id_num == user['id_num'])
        user['expiry'] = new_expiry
        
    return render_template('user_home.html', user=user)

@app.route('/my_data')
def my_data():
    if 'user_id' not in session: return redirect('/')
    user = users_table.get(Query().id_num == session['user_id'])
    return render_template('my_data.html', user=user)

@app.route('/sites')
def sites():
    return render_template('sites.html')

# --- 5. بوابة الإدارة (المشرف) ---

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('username') == 'admin' and request.form.get('password') == 'admin':
            otp = random.randint(100000, 999999)
            session['admin_otp'] = str(otp)
            # إرسال الرمز للرقم المحدد في الطلب
            send_telegram(f"🔐 رمز التحقق للمشرف: {otp}")
            return render_template('admin_otp.html')
    return render_template('admin_login.html')

@app.route('/admin_verify_otp', methods=['POST'])
def admin_verify_otp():
    if request.form.get('otp') == session.get('admin_otp'):
        session['admin_logged_in'] = True
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'): return redirect('/')
    users = users_table.all()
    return render_template('admin_dashboard.html', users=users)

@app.route('/admin/add_user', methods=['POST'])
def api_add_user():
    data = request.form.to_dict()
    # حفظ صورة الوجه
    face_img = request.files.get('face_image')
    if face_img:
        face_img.save(os.path.join(FACES_FOLDER, f"{data['id_num']}.jpg"))
    
    data['blocked'] = False
    data['expiry'] = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d") # سنة افتراضية
    users_table.insert(data)
    
    # إرسال بيانات الدخول
    msg = f"مرحباً بك في وزارة الظلال\nهويتك: {data['id_num']}\nكلمة المرور: {data['password']}"
    send_telegram(f"🆕 تم إضافة مستخدم جديد:\n{msg}")
    send_email(data['email'], "بيانات دخول وزارة الظلال", msg)
    
    return redirect(url_for('admin_dashboard'))

# --- 6. نظام الإشعارات المركزي ---

@app.route('/admin/send_broadcast', methods=['POST'])
def send_broadcast():
    target_type = request.form.get('type') # person, region, job, edu, gender
    content = request.form.get('message')
    platform = request.form.get('platform') # telegram, email, pwa
    
    query = Query()
    targets = []
    
    if target_type == 'all': targets = users_table.all()
    elif target_type == 'region': targets = users_table.search(query.region == request.form.get('target_val'))
    # ... إضافة باقي الفلاتر هنا
    
    for t in targets:
        if 'telegram' in platform: send_telegram(f"📢 إشعار رسمي:\n{content}")
        if 'email' in platform: send_email(t['email'], "إشعار من وزارة الظلال", content)
        
    return jsonify({"status": "sent"})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

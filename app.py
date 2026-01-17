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
app.permanent_session_lifetime = timedelta(minutes=10)

# --- الإعدادات السيادية ---
TELEGRAM_TOKEN = "8415250551:AAEv6B1Evhc_NNKhH1o76PBUl1UNVMYVT2U"
ADMIN_CHAT_ID = "8338737071"
EMAIL_USER = "azlal.gov@gmail.com"
EMAIL_PASS = "mhhuliujcrqkzccg"

db = TinyDB('shadow_db.json')
users_table = db.table('users')
FACES_FOLDER = 'static/faces'

# ضمان وجود المجلدات
for folder in [FACES_FOLDER, 'static/css', 'static/js', 'static/images']:
    if not os.path.exists(folder): os.makedirs(folder)

# --- دوال التواصل (تليجرام + بريد) ---
def send_tg(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={'chat_id': ADMIN_CHAT_ID, 'text': msg, 'parse_mode': 'HTML'}, timeout=5)
    except: pass

def send_mail(to_email, subject, body):
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

# --- معالجة الوجه ---
def verify_face(stored_id, captured_b64):
    try:
        header, encoded = captured_b64.split(",", 1)
        data = base64.b64decode(encoded)
        nparr = np.frombuffer(data, np.uint8)
        img_cap = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        
        stored_path = os.path.join(FACES_FOLDER, f"{stored_id}.jpg")
        img_stored = cv2.imread(stored_path, cv2.IMREAD_GRAYSCALE)
        
        if img_stored is None: return False
        img_cap = cv2.resize(img_cap, (300, 300))
        img_stored = cv2.resize(img_stored, (300, 300))
        res = cv2.matchTemplate(img_cap, img_stored, cv2.TM_CCOEFF_NORMED)
        return cv2.minMaxLoc(res)[1] > 0.70
    except: return False

# --- المسارات ---
@app.route('/')
def index(): return render_template('index.html')

# دخول المواطن
@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        ident = request.form.get('identifier')
        pw = request.form.get('password')
        U = Query()
        user = users_table.get((U.id_num == ident) | (U.phone == ident))
        
        if user and user['password'] == pw:
            if user.get('blocked'): return render_template('blocked.html')
            session['pre_id'] = user['id_num']
            return redirect(url_for('face_verify'))
        return render_template('user_login.html', error="بيانات خاطئة")
    return render_template('user_login.html')

@app.route('/face_verify')
def face_verify(): return render_template('face_verify.html')

@app.route('/api/process_face', methods=['POST'])
def api_face():
    data = request.json
    uid = session.get('pre_id')
    if verify_face(uid, data['image']):
        session.permanent = True
        session['user_id'] = uid
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        send_tg(f"🔓 <b>دخول ناجح</b>\nالهوية: {uid}\nالوقت: {now}\nIP: {request.remote_addr}")
        return jsonify({"status": "success"})
    return jsonify({"status": "fail"})

@app.route('/user_home')
def user_home():
    if 'user_id' not in session: return redirect('/')
    user = users_table.get(Query().id_num == session['user_id'])
    # تجديد تلقائي للبطاقة المنتهية
    exp = datetime.strptime(user['expiry'], "%Y-%m-%d")
    if datetime.now() > exp:
        new_exp = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        users_table.update({'expiry': new_exp}, Query().id_num == user['id_num'])
        user['expiry'] = new_exp
    return render_template('user_home.html', user=user)

# --- إدارة المشرف ---
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('username') == 'admin' and request.form.get('password') == 'admin':
            otp = str(random.randint(100000, 999999))
            session['admin_otp'] = otp
            send_tg(f"🔐 رمز التحقق للمشرف: <code>{otp}</code>")
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
    return render_template('admin_dashboard.html', users=users_table.all())

@app.route('/admin/add_user', methods=['GET', 'POST'])
def admin_add_user():
    if not session.get('admin_logged_in'): return redirect('/')
    if request.method == 'POST':
        data = request.form.to_dict()
        file = request.files.get('face_image')
        if file: file.save(os.path.join(FACES_FOLDER, f"{data['id_num']}.jpg"))
        data['blocked'] = False
        data['expiry'] = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        users_table.insert(data)
        # إرسال البيانات فور الإضافة
        info = f"هويتك: {data['id_num']}\nكلمة المرور: {data['password']}\nمعرف البصمة: {data['fingerprint_id']}"
        send_tg(f"🆕 <b>مواطن جديد</b>\n{info}")
        send_mail(data['email'], "بيانات دخول وزارة الظلال", info)
        return redirect(url_for('admin_dashboard'))
    return render_template('add_user.html')

@app.route('/admin/toggle_block/<id_num>', methods=['POST'])
def toggle_block(id_num):
    user = users_table.get(Query().id_num == id_num)
    new_state = not user.get('blocked', False)
    users_table.update({'blocked': new_state}, Query().id_num == id_num)
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/send_credentials/<id_num>', methods=['POST'])
def send_creds(id_num):
    u = users_table.get(Query().id_num == id_num)
    info = f"بيانات دخولك:\nالهوية: {u['id_num']}\nالكلمة: {u['password']}\nالبصمة: {u['fingerprint_id']}"
    send_tg(info)
    send_mail(u['email'], "تذكير ببيانات الدخول", info)
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_user/<id_num>', methods=['POST'])
def delete_user(id_num):
    users_table.remove(Query().id_num == id_num)
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/send_broadcast', methods=['POST'])
def broadcast():
    t_type = request.form.get('target_type')
    t_val = request.form.get('target_val')
    msg = request.form.get('message')
    plats = request.form.getlist('platforms')
    
    U = Query()
    if t_type == 'all': targets = users_table.all()
    elif t_type == 'person': targets = users_table.search(U.id_num == t_val)
    elif t_type == 'region': targets = users_table.search(U.region == t_val)
    elif t_type == 'job': targets = users_table.search(U.job_cat == t_val)
    elif t_type == 'edu': targets = users_table.search(U.edu_level == t_val)
    elif t_type == 'gender': targets = users_table.search(U.gender == t_val)
    
    for t in targets:
        if 'telegram' in plats: send_tg(f"📢 <b>إشعار رسمي:</b>\n{msg}")
        if 'email' in plats: send_mail(t['email'], "إشعار من وزارة الظلال", msg)
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

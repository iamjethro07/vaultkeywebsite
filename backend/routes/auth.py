from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
import bcrypt, re, random, string, smtplib, os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from db import query

auth_bp = Blueprint('auth', __name__)

def hash_pw(p): return bcrypt.hashpw(p[:72].encode(), bcrypt.gensalt()).decode()
def check_pw(p, h): return bcrypt.checkpw(p[:72].encode(), h.encode())
def gen_otp(): return ''.join(random.choices(string.digits, k=6))
def utcnow(): return datetime.now(timezone.utc)

def send_email(to_email, subject, html_body):
    smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    smtp_user = os.getenv('SMTP_USER', '')
    smtp_pass = os.getenv('SMTP_PASS', '')
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f'VaultKey <{smtp_user}>'
    msg['To'] = to_email
    msg.attach(MIMEText(html_body, 'html'))
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_email, msg.as_string())


@auth_bp.route('/signup', methods=['POST'])
def signup():
    d = request.get_json(silent=True) or {}
    username = (d.get('username') or '').strip()
    email    = (d.get('email')    or '').strip().lower()
    password = (d.get('password') or '')
    if not username or not email or not password:
        return jsonify(error='All fields required.'), 400
    if len(password) < 8:
        return jsonify(error='Password must be at least 8 characters.'), 400
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return jsonify(error='Invalid email.'), 400
    if query('SELECT id FROM users WHERE username=%s', (username,), one=True):
        return jsonify(error='Username already taken.'), 409
    if query('SELECT id FROM users WHERE email=%s', (email,), one=True):
        return jsonify(error='Email already registered.'), 409
    row = query(
        'INSERT INTO users (username,email,password_hash) VALUES (%s,%s,%s) RETURNING id',
        (username, email, hash_pw(password)), commit=True
    )
    uid = row['id']
    return jsonify(
        message='Account created!',
        user={'id': uid, 'username': username, 'email': email},
        access_token=create_access_token(identity=str(uid)),
        refresh_token=create_refresh_token(identity=str(uid))
    ), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    d = request.get_json(silent=True) or {}
    email    = (d.get('email')    or '').strip().lower()
    password = (d.get('password') or '')
    if not email or not password:
        return jsonify(error='Email and password required.'), 400
    user = query('SELECT * FROM users WHERE email=%s', (email,), one=True)
    if not user or not check_pw(password, user['password_hash']):
        return jsonify(error='Invalid email or password.'), 401
    return jsonify(
        message='Login successful.',
        user={'id': user['id'], 'username': user['username'], 'email': user['email']},
        access_token=create_access_token(identity=str(user['id'])),
        refresh_token=create_refresh_token(identity=str(user['id']))
    ), 200


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    d = request.get_json(silent=True) or {}
    email = (d.get('email') or '').strip().lower()
    if not email:
        return jsonify(error='Email is required.'), 400
    user = query('SELECT id, username FROM users WHERE email=%s', (email,), one=True)
    if not user:
        return jsonify(message='If that email exists, an OTP has been sent.'), 200
    otp = gen_otp()
    expires_at = utcnow() + timedelta(minutes=10)
    query('DELETE FROM password_resets WHERE user_id=%s', (user['id'],), commit=True)
    query('INSERT INTO password_resets (user_id,otp,expires_at) VALUES (%s,%s,%s)',
          (user['id'], otp, expires_at), commit=True)
    try:
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;background:#0d0d14;color:#f1f1f8;padding:32px;border-radius:12px;border:1px solid #252535">
          <h2 style="color:#00d9a3;margin-bottom:4px">🔐 VaultKey</h2>
          <p style="color:#6b6b85;font-size:12px;margin-bottom:24px;letter-spacing:.1em">PASSWORD RESET</p>
          <p>Hi <strong>{user['username']}</strong>,</p>
          <p style="margin:16px 0;color:#a0a0b8">Use the OTP below to reset your master password. It expires in <strong style="color:#f1f1f8">10 minutes</strong>.</p>
          <div style="background:#1a1a28;border:2px solid #00d9a3;border-radius:12px;padding:28px;text-align:center;margin:28px 0">
            <p style="color:#6b6b85;font-size:11px;letter-spacing:.15em;margin-bottom:12px">YOUR ONE-TIME PASSWORD</p>
            <div style="font-size:40px;font-weight:700;letter-spacing:14px;color:#00d9a3;font-family:monospace">{otp}</div>
          </div>
          <p style="font-size:12px;color:#6b6b85;line-height:1.6">If you did not request a password reset, please ignore this email.</p>
          <hr style="border:none;border-top:1px solid #252535;margin:24px 0"/>
          <p style="font-size:11px;color:#444;text-align:center">VaultKey — Zero-Knowledge Password Manager</p>
        </div>
        """
        send_email(email, '🔐 VaultKey — Your Password Reset OTP', html)
    except Exception as e:
        print(f'Email send error: {e}')
        return jsonify(error='Failed to send email. Check SMTP settings.'), 500
    return jsonify(message='OTP sent to your email.'), 200


@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    d = request.get_json(silent=True) or {}
    email = (d.get('email') or '').strip().lower()
    otp   = (d.get('otp')   or '').strip()
    if not email or not otp:
        return jsonify(error='Email and OTP required.'), 400
    user = query('SELECT id FROM users WHERE email=%s', (email,), one=True)
    if not user:
        return jsonify(error='Invalid OTP.'), 400
    record = query('SELECT * FROM password_resets WHERE user_id=%s AND otp=%s',
                   (user['id'], otp), one=True)
    if not record:
        return jsonify(error='Invalid OTP.'), 400
    expires = record['expires_at']
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if utcnow() > expires:
        query('DELETE FROM password_resets WHERE user_id=%s', (user['id'],), commit=True)
        return jsonify(error='OTP expired. Please request a new one.'), 400
    query('UPDATE password_resets SET verified=TRUE WHERE user_id=%s', (user['id'],), commit=True)
    return jsonify(message='OTP verified.'), 200


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    d = request.get_json(silent=True) or {}
    email        = (d.get('email')    or '').strip().lower()
    otp          = (d.get('otp')      or '').strip()
    new_password = (d.get('password') or '')
    if not email or not otp or not new_password:
        return jsonify(error='All fields required.'), 400
    if len(new_password) < 8:
        return jsonify(error='Password must be at least 8 characters.'), 400
    user = query('SELECT id FROM users WHERE email=%s', (email,), one=True)
    if not user:
        return jsonify(error='Invalid request.'), 400
    record = query('SELECT * FROM password_resets WHERE user_id=%s AND otp=%s AND verified=TRUE',
                   (user['id'], otp), one=True)
    if not record:
        return jsonify(error='OTP not verified.'), 400
    expires = record['expires_at']
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if utcnow() > expires:
        query('DELETE FROM password_resets WHERE user_id=%s', (user['id'],), commit=True)
        return jsonify(error='OTP expired. Please start again.'), 400
    query('UPDATE users SET password_hash=%s WHERE id=%s',
          (hash_pw(new_password), user['id']), commit=True)
    query('DELETE FROM password_resets WHERE user_id=%s', (user['id'],), commit=True)
    return jsonify(message='Password reset successfully! You can now log in.'), 200


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    return jsonify(access_token=create_access_token(identity=get_jwt_identity())), 200


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    return jsonify(message='Logged out.'), 200
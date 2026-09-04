import os
import datetime
import random
import string
from functools import wraps

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import HTTPException
from marshmallow import ValidationError
from sqlalchemy import or_
import jwt

from config import config_by_name
from schemas import (
    ma,
    register_schema,
    login_schema,
    forgot_password_schema,
    verify_registration_schema,
    reset_password_schema,
    dashboard_query_schema
)

# Select environment configuration (defaults to development)
env_name = os.getenv('FLASK_ENV', 'development')
config_cls = config_by_name.get(env_name, config_by_name['default'])

app = Flask(__name__)
app.config.from_object(config_cls)
config_cls.init_app(app)

# Initialize Marshmallow extension with Flask app
ma.init_app(app)

# --- Flask-Mail Setup ---
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() in ['true', '1', 't']
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

mail = Mail(app)

# --- CORS Setup ---
CORS(
    app,
    resources={
        r"/*": {
            "origins": [
                "http://localhost:5174",
                "http://localhost:5173",
                "http://127.0.0.1:5174",
                "http://127.0.0.1:5173",
                "https://auth-frontend-ibum.onrender.com",
            ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
        }
    },
    supports_credentials=True
)

db = SQLAlchemy(app)

# Database Model
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # OTP / Verification Additions
    is_verified = db.Column(db.Boolean, default=False)
    otp = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Create tables automatically on startup
with app.app_context():
    db.create_all()

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))


# =====================================================================
# 🛡️ GLOBAL ERROR HANDLERS (Forces JSON output everywhere)
# =====================================================================

# 1. Intercept Marshmallow validation failures automatically
@app.errorhandler(ValidationError)
def handle_marshmallow_validation_error(err):
    return jsonify({
        'status': 'error',
        'message': 'Validation failed',
        'errors': err.messages
    }), 400

# 2. Intercept generic HTTP Exceptions (404, 405, etc.) and return strictly JSON
@app.errorhandler(HTTPException)
def handle_http_exception(e):
    return jsonify({
        'status': 'error',
        'message': e.description
    }), e.code

# 3. Intercept uncaught internal server errors (500)
@app.errorhandler(Exception)
def handle_unexpected_error(e):
    app.logger.error(f"Unhandled Exception: {str(e)}")
    return jsonify({
        'status': 'error',
        'message': 'An internal server error occurred.'
    }), 500


# =====================================================================
# 🔐 JWT MIDDLEWARE DECORATOR
# =====================================================================
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            parts = auth_header.split(" ")
            if len(parts) == 2 and parts[0] == 'Bearer':
                token = parts[1]

        if not token:
            return jsonify({'message': 'Authorization token is missing!'}), 401

        try:
            secret_key = app.config.get('JWT_SECRET_KEY', app.config['SECRET_KEY'])
            data = jwt.decode(token, secret_key, algorithms=["HS256"])

            if data.get('type') != 'access':
                return jsonify({'message': 'Invalid token type for route access.'}), 401

            current_user = db.session.get(User, data['user_id'])

            if not current_user:
                return jsonify({'message': 'User no longer exists.'}), 401
                
            if not current_user.is_verified:
                return jsonify({'message': 'Account email is unverified.'}), 403

        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token!'}), 401

        return f(current_user, *args, **kwargs)

    return decorated


# =====================================================================
# 🚀 API ROUTES
# =====================================================================

# 0️⃣ Health Check & Root Routes (Prevents 404 on direct URL navigation)
@app.route('/', methods=['GET'])
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'success',
        'message': 'Flask Authentication API is up and running!'
    }), 200


# 1️⃣ Register Route
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = register_schema.load(request.get_json())

    if User.query.filter((User.email == data['email']) | (User.username == data['username'])).first():
        return jsonify({'message': 'User with this email or username already exists'}), 409

    otp = generate_otp()
    otp_expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10)

    new_user = User(
        username=data['username'], 
        email=data['email'],
        otp=otp,
        otp_expiry=otp_expiry,
        is_verified=False
    )
    new_user.set_password(data['password'])

    try:
        db.session.add(new_user)
        db.session.commit()

        msg = Message("Verify Your Account Registration", recipients=[new_user.email])
        msg.body = f"Your account is being created. Use this code to complete your registration: {otp}"
        mail.send(msg)

        return jsonify({'message': 'User registered. Please check your email for the verification code.'}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error creating user or sending mail', 'error': str(e)}), 500


# 2️⃣ Verify Registration OTP Route
@app.route('/api/auth/verify-registration', methods=['POST'])
def verify_registration():
    data = verify_registration_schema.load(request.get_json())
    email = data['email']
    otp_input = data['otp']

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({'message': 'User not found'}), 404

    if user.is_verified:
        return jsonify({'message': 'Account is already verified'}), 400

    now = datetime.datetime.now(datetime.timezone.utc)
    if user.otp != otp_input or (user.otp_expiry and user.otp_expiry.replace(tzinfo=datetime.timezone.utc) < now):
        return jsonify({'message': 'Incorrect or expired OTP code'}), 400

    user.is_verified = True
    user.otp = None
    user.otp_expiry = None
    db.session.commit()

    return jsonify({'message': 'Email verified successfully! You can now login.'}), 200


# 3️⃣ Login Route
@app.route('/api/auth/login', methods=['POST'])
def login():
    payload = request.get_json()
    if not payload:
        return jsonify({'message': 'Missing JSON request body'}), 400

    data = login_schema.load(payload)

    user = User.query.filter_by(email=data['email']).first()

    if not user or not user.check_password(data['password']):
        return jsonify({'message': 'Invalid email or password'}), 401

    if not user.is_verified:
        return jsonify({'message': 'Account unverified. Please verify your email first.'}), 403

    secret_key = app.config.get('JWT_SECRET_KEY', app.config['SECRET_KEY'])
    access_expires = app.config.get('JWT_ACCESS_TOKEN_EXPIRES', datetime.timedelta(minutes=15))
    refresh_expires = app.config.get('JWT_REFRESH_TOKEN_EXPIRES', datetime.timedelta(days=7))

    access_payload = {
        'user_id': user.id,
        'type': 'access',
        'exp': datetime.datetime.now(datetime.timezone.utc) + access_expires
    }
    access_token = jwt.encode(access_payload, secret_key, algorithm='HS256')

    refresh_payload = {
        'user_id': user.id,
        'type': 'refresh',
        'exp': datetime.datetime.now(datetime.timezone.utc) + refresh_expires
    }
    refresh_token = jwt.encode(refresh_payload, secret_key, algorithm='HS256')

    return jsonify({
        'message': 'Login successful',
        'token': access_token,
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_verified': user.is_verified
        }
    }), 200


# 4️⃣ Request Password Reset OTP Route
@app.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    data = forgot_password_schema.load(request.get_json())
    email = data['email']

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({'message': 'If this email exists, an OTP has been sent.'}), 200

    otp = generate_otp()
    user.otp = otp
    user.otp_expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10)
    db.session.commit()

    try:
        msg = Message("Password Reset Verification Code", recipients=[user.email])
        msg.body = f"You requested a password reset. Use this code to update your password: {otp}"
        mail.send(msg)
    except Exception as e:
        print(f"\n--- MAIL SENDING FAILED: {e} ---\n")
        return jsonify({'message': 'Error sending mail', 'error': str(e)}), 500

    return jsonify({'message': 'If this email exists, an OTP has been sent.'}), 200


# 5️⃣ Reset Password Route
@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    data = reset_password_schema.load(request.get_json())
    email = data['email']
    otp_input = data['otp']
    new_password = data['new_password']

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({'message': 'Invalid details'}), 400

    now = datetime.datetime.now(datetime.timezone.utc)
    if user.otp != otp_input or (user.otp_expiry and user.otp_expiry.replace(tzinfo=datetime.timezone.utc) < now):
        return jsonify({'message': 'Incorrect or expired OTP code'}), 400

    user.set_password(new_password)
    user.otp = None
    user.otp_expiry = None
    db.session.commit()

    return jsonify({'message': 'Password reset successfully! You can now log in.'}), 200


# 6️⃣ Token Refresh Route
@app.route('/api/auth/refresh', methods=['POST'])
def refresh():
    data = request.get_json() or {}
    refresh_token = data.get('refresh_token')

    if not refresh_token:
        return jsonify({'message': 'Refresh token is missing'}), 401

    try:
        secret_key = app.config.get('JWT_SECRET_KEY', app.config['SECRET_KEY'])
        payload = jwt.decode(refresh_token, secret_key, algorithms=["HS256"])

        if payload.get('type') != 'refresh':
            return jsonify({'message': 'Invalid token type'}), 401

        access_expires = app.config.get('JWT_ACCESS_TOKEN_EXPIRES', datetime.timedelta(minutes=15))
        new_access_payload = {
            'user_id': payload['user_id'],
            'type': 'access',
            'exp': datetime.datetime.now(datetime.timezone.utc) + access_expires
        }
        new_access_token = jwt.encode(new_access_payload, secret_key, algorithm='HS256')

        return jsonify({'access_token': new_access_token, 'token': new_access_token}), 200

    except jwt.ExpiredSignatureError:
        return jsonify({'message': 'Refresh token expired. Please log in again.'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'message': 'Invalid refresh token'}), 401


# 7️⃣ Protected User Profile Route
@app.route('/api/auth/me', methods=['GET'])
@token_required
def get_current_user_profile(current_user):
    return jsonify({
        'user': {
            'id': current_user.id,
            'username': current_user.username,
            'email': current_user.email,
            'is_verified': current_user.is_verified
        }
    }), 200


# 8️⃣ Dashboard Users Directory (Pagination + Search + Filtering)
@app.route('/api/dashboard/users', methods=['GET'])
@token_required
def get_dashboard_users(current_user):
    args = dashboard_query_schema.load(request.args)
    
    page = args['page']
    per_page = args['per_page']
    search_query = args['search'].strip()
    status_filter = args['status'].strip().lower()

    query = User.query

    if search_query:
        query = query.filter(
            or_(
                User.username.ilike(f"%{search_query}%"),
                User.email.ilike(f"%{search_query}%")
            )
        )

    if status_filter == 'verified':
        query = query.filter(User.is_verified == True)
    elif status_filter == 'unverified':
        query = query.filter(User.is_verified == False)

    query = query.order_by(User.id.desc())
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)

    return jsonify({
        'users': [{
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'is_verified': u.is_verified
        } for u in pagination.items],
        'pagination': {
            'current_page': pagination.page,
            'total_pages': pagination.pages,
            'total_items': pagination.total,
            'per_page': pagination.per_page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    }), 

@app.errorhandler(500)
def handle_500_error(e):
    response = jsonify({
        "status": "error",
        "message": "An internal server error occurred.",
        "details": str(e)
    })
    # Manually ensure CORS header is present on 500 errors
    response.headers.add("Access-Control-Allow-Origin", "https://auth-frontend-ibum.onrender.com")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response, 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
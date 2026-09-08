import os
import random
import string
import traceback
from datetime import datetime, timedelta, timezone
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
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

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

# Initialize Flask App
app = Flask(__name__)

# Select Environment Configuration
env_name = os.getenv('FLASK_ENV', 'development')
config_cls = config_by_name.get(env_name, config_by_name['default'])
app.config.from_object(config_cls)

# Database Setup
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI') or os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Flask-Mail Configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
<<<<<<< HEAD
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 2525))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() in ['true', '1', 't']
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False').lower() in ['true', '1', 't']
=======
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 465))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'False').lower() in ['true', '1', 't']
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'True').lower() in ['true', '1', 't']
>>>>>>> a80b1a3d68dacfb6d7bffdb23a71f44fe414e690
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER') or os.getenv('MAIL_USERNAME')

# Initialize Extensions
ma.init_app(app)
mail = Mail(app)

# CORS Setup
ALLOWED_ORIGINS = [
    "http://localhost:5176",
    "http://localhost:5174",
    "http://localhost:5173",
    "http://127.0.0.1:5176",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5173",
    "https://auth-frontend-ibum.onrender.com",
]

CORS(
    app,
    resources={
        r"/*": {
            "origins": ALLOWED_ORIGINS,
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
    
    is_verified = db.Column(db.Boolean, default=False)
    otp = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)

    reset_otp = db.Column(db.String(6), nullable=True)
    reset_otp_expiry = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

with app.app_context():
    db.create_all()

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

<<<<<<< HEAD
# Error Handlers
=======
def make_cors_response(data, status_code=200):
    """Helper to attach explicit CORS headers to error handlers"""
    response = jsonify(data)
    origin = request.headers.get('Origin')
    allowed_origins = [
        "http://localhost:5174",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5173",
        "https://auth-frontend-ibum.onrender.com",
    ]
    if origin in allowed_origins:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response, status_code


# =====================================================================
# 🛡️ GLOBAL ERROR HANDLERS (Guarantees CORS + JSON output)
# =====================================================================

>>>>>>> a80b1a3d68dacfb6d7bffdb23a71f44fe414e690
@app.errorhandler(ValidationError)
def handle_marshmallow_validation_error(err):
    return make_cors_response({
        'status': 'error',
        'message': 'Validation failed',
        'errors': err.messages
    }, 400)

@app.errorhandler(HTTPException)
def handle_http_exception(e):
    return make_cors_response({
        'status': 'error',
        'message': e.description
    }, e.code)

@app.errorhandler(Exception)
def handle_unexpected_error(e):
    app.logger.error(f"Unhandled Exception: {str(e)}")
<<<<<<< HEAD
    origin = request.headers.get('Origin')
    response = jsonify({
        'status': 'error',
        'message': 'An internal server error occurred.',
        'details': str(e)
    })
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response, 500
=======
    return make_cors_response({
        'status': 'error',
        'message': 'An internal server error occurred.',
        'details': str(e)
    }, 500)
>>>>>>> a80b1a3d68dacfb6d7bffdb23a71f44fe414e690

# Middleware
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

<<<<<<< HEAD
# Routes
=======

# =====================================================================
# 🚀 API ROUTES
# =====================================================================

>>>>>>> a80b1a3d68dacfb6d7bffdb23a71f44fe414e690
@app.route('/', methods=['GET'])
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'success',
        'message': 'Flask Authentication API is up and running!'
    }), 200

@app.route('/api/auth/register', methods=['POST'])
def register():
<<<<<<< HEAD
    try:
        data = register_schema.load(request.get_json())
    except Exception as val_err:
        return jsonify({'message': 'Validation failed', 'errors': str(val_err)}), 400
=======
    payload = request.get_json()
    if not payload:
        return jsonify({'message': 'Missing JSON request body'}), 400

    data = register_schema.load(payload)
>>>>>>> a80b1a3d68dacfb6d7bffdb23a71f44fe414e690

    if User.query.filter((User.email == data['email']) | (User.username == data['username'])).first():
        return jsonify({'message': 'User with this email or username already exists'}), 409

    otp = generate_otp()
    otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=10)

    print(f"\n==========================================", flush=True)
    print(f"🔑 LOCAL REGISTRATION OTP FOR {data['email']}: {otp}", flush=True)
    print(f"==========================================\n", flush=True)

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
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error saving user to database', 'error': str(e)}), 500

<<<<<<< HEAD
        try:
            msg = Message(
                subject="Verify Your Account Registration",
                sender=("Authentication Service", app.config['MAIL_USERNAME']),
                recipients=[new_user.email],
                body=f"Your verification code is: {otp}",
            )
            mail.send(msg)
            print("✅ Email sent successfully!", flush=True)
        except Exception as mail_err:
            print(f"⚠️ SMTP Delivery Failed (Logged to console): {str(mail_err)}", flush=True)

        return jsonify({
            'message': 'Registration successful',
            'otp': otp
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error creating user', 'error': str(e)}), 500
=======
    email_sent = False
    try:
        msg = Message("Verify Your Account Registration", recipients=[new_user.email])
        msg.body = f"Your account is being created. Use this code to complete your registration: {otp}"
        mail.send(msg)
        email_sent = True
        print(f"SUCCESS: Email delivered to {new_user.email}")
    except Exception as e:
        print("\n" + "="*50)
        print("--- RENDER MAIL DELIVERY FAILED (FALLBACK) ---")
        print(f"User Email : {new_user.email}")
        print(f"YOUR OTP   : {otp}")
        print(f"SMTP Error : {e}")
        print("="*50 + "\n")

    return jsonify({
        'message': 'User registered. Please check your email or server logs for the verification code.',
        'email_sent': email_sent
    }), 201
>>>>>>> a80b1a3d68dacfb6d7bffdb23a71f44fe414e690

@app.route('/api/auth/verify-registration', methods=['POST'])
def verify_registration():
    payload = request.get_json()
    if not payload:
        return jsonify({'message': 'Missing JSON request body'}), 400

    data = verify_registration_schema.load(payload)
    email = data['email']
    otp_input = data['otp']

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({'message': 'User not found'}), 404

    if user.is_verified:
        return jsonify({'message': 'Account is already verified'}), 400

<<<<<<< HEAD
    now = datetime.now(timezone.utc)
    user_otp_expiry = user.otp_expiry.replace(tzinfo=timezone.utc) if user.otp_expiry and user.otp_expiry.tzinfo is None else user.otp_expiry

    if user.otp != otp_input or (user_otp_expiry and user_otp_expiry < now):
=======
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Safe timezone conversion for DB datetimes
    expiry = user.otp_expiry
    if expiry and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=datetime.timezone.utc)

    if user.otp != otp_input or (expiry and expiry < now):
>>>>>>> a80b1a3d68dacfb6d7bffdb23a71f44fe414e690
        return jsonify({'message': 'Incorrect or expired OTP code'}), 400

    user.is_verified = True
    user.otp = None
    user.otp_expiry = None
    db.session.commit()

    return jsonify({'message': 'Email verified successfully! You can now login.'}), 200

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
    access_expires = app.config.get('JWT_ACCESS_TOKEN_EXPIRES', timedelta(minutes=15))
    refresh_expires = app.config.get('JWT_REFRESH_TOKEN_EXPIRES', timedelta(days=7))

    access_token = jwt.encode({'user_id': user.id, 'type': 'access', 'exp': datetime.now(timezone.utc) + access_expires}, secret_key, algorithm='HS256')
    refresh_token = jwt.encode({'user_id': user.id, 'type': 'refresh', 'exp': datetime.now(timezone.utc) + refresh_expires}, secret_key, algorithm='HS256')

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

@app.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
<<<<<<< HEAD
    payload = request.get_json() or {}
    data = forgot_password_schema.load(payload)
    email = data.get('email', '').strip().lower()
=======
    payload = request.get_json()
    if not payload:
        return jsonify({'message': 'Missing JSON request body'}), 400

    data = forgot_password_schema.load(payload)
    email = data['email']
>>>>>>> a80b1a3d68dacfb6d7bffdb23a71f44fe414e690

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"message": "If an account exists, an OTP has been sent."}), 200

    otp = generate_otp()
    user.reset_otp = otp
    user.reset_otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=10)
    db.session.commit()

    try:
        msg = Message(subject="Your Password Reset OTP", recipients=[email], body=f"Your OTP code is {otp}.")
        mail.send(msg)
<<<<<<< HEAD
        return jsonify({"message": "OTP sent to your email successfully"}), 200
    except Exception as e:
        print(f"⚠️ SMTP Delivery Failed: {str(e)}", flush=True)
        print(f"🔑 LOCAL DEV FALLBACK OTP FOR {email}: {otp}", flush=True)
        return jsonify({"message": "OTP generated", "fallback_otp": otp}), 200
=======
        print(f"SUCCESS: Reset OTP delivered to {user.email}")
    except Exception as e:
        print("\n" + "="*50)
        print("--- RENDER MAIL DELIVERY FAILED (FORGOT PASSWORD) ---")
        print(f"User Email : {user.email}")
        print(f"YOUR OTP   : {otp}")
        print(f"SMTP Error : {e}")
        print("="*50 + "\n")
>>>>>>> a80b1a3d68dacfb6d7bffdb23a71f44fe414e690

@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
<<<<<<< HEAD
    payload = request.get_json() or {}
    data = reset_password_schema.load(payload)
    email = data.get('email', '').strip().lower()
    incoming_otp = str(data.get('otp', '')).strip()
    new_password = data.get('new_password', '').strip()
=======
    payload = request.get_json()
    if not payload:
        return jsonify({'message': 'Missing JSON request body'}), 400

    data = reset_password_schema.load(payload)
    email = data['email']
    otp_input = data['otp']
    new_password = data['new_password']
>>>>>>> a80b1a3d68dacfb6d7bffdb23a71f44fe414e690

    user = User.query.filter_by(email=email).first()
    if not user or not user.reset_otp or str(user.reset_otp).strip() != incoming_otp:
        return jsonify({"message": "Incorrect or invalid OTP code"}), 400

<<<<<<< HEAD
    if user.reset_otp_expiry:
        expiry = user.reset_otp_expiry.replace(tzinfo=timezone.utc) if user.reset_otp_expiry.tzinfo is None else user.reset_otp_expiry
        if datetime.now(timezone.utc) > expiry:
            return jsonify({"message": "OTP has expired."}), 400
=======
    if not user:
        return jsonify({'message': 'Invalid details'}), 400

    now = datetime.datetime.now(datetime.timezone.utc)
    expiry = user.otp_expiry
    if expiry and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=datetime.timezone.utc)

    if user.otp != otp_input or (expiry and expiry < now):
        return jsonify({'message': 'Incorrect or expired OTP code'}), 400
>>>>>>> a80b1a3d68dacfb6d7bffdb23a71f44fe414e690

    user.set_password(new_password)
    user.reset_otp = None
    user.reset_otp_expiry = None
    db.session.commit()

    return jsonify({"message": "Password reset successfully."}), 200

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

@app.route('/api/dashboard/users', methods=['GET'])
@token_required
def get_dashboard_users(current_user):
    args = dashboard_query_schema.load(request.args)
    page, per_page = args['page'], args['per_page']
    search_query, status_filter = args['search'].strip(), args['status'].strip().lower()

    query = User.query
    if search_query:
        query = query.filter(or_(User.username.ilike(f"%{search_query}%"), User.email.ilike(f"%{search_query}%")))

    if status_filter == 'verified':
        query = query.filter(User.is_verified == True)
    elif status_filter == 'unverified':
        query = query.filter(User.is_verified == False)

    pagination = db.paginate(query.order_by(User.id.desc()), page=page, per_page=per_page, error_out=False)

    return jsonify({
        'users': [{'id': u.id, 'username': u.username, 'email': u.email, 'is_verified': u.is_verified} for u in pagination.items],
        'pagination': {
            'current_page': pagination.page,
            'total_pages': pagination.pages,
            'total_items': pagination.total,
            'per_page': pagination.per_page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    }), 200
<<<<<<< HEAD
=======

>>>>>>> a80b1a3d68dacfb6d7bffdb23a71f44fe414e690

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
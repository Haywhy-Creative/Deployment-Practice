import os
import random
import string
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

# Load environment variables
load_dotenv()

# Select environment configuration (defaults to development)
env_name = os.getenv('FLASK_ENV', 'development')
config_cls = config_by_name.get(env_name, config_by_name['default'])

app = Flask(__name__)
app.config.from_object(config_cls)
config_cls.init_app(app)
# Database Configuration Overrides
db_url = os.getenv('SQLALCHEMY_DATABASE_URI') or os.getenv('DATABASE_URL') or app.config.get('SQLALCHEMY_DATABASE_URI')

# Render compatibility fix for SQLAlchemy 2.0+ (Converts postgres:// to postgresql://)
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Mail Configuration Overrides
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', app.config.get('MAIL_SERVER', 'smtp.gmail.com'))
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', app.config.get('MAIL_PORT', 2525)))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() in ['true', '1', 't']
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False').lower() in ['true', '1', 't']
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = (
    os.getenv('MAIL_DEFAULT_SENDER') or os.getenv('MAIL_USERNAME')
)

# Initialize Extensions
ma.init_app(app)
mail = Mail(app)
db = SQLAlchemy(app)

# --- CORS Setup ---
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

# 🚨 DEBUG: Verify variables loaded on startup
print("=" * 50)
print("MAIL_USERNAME loaded:", app.config['MAIL_USERNAME'])
print("MAIL_PASSWORD loaded:", "YES (Set)" if app.config['MAIL_PASSWORD'] else "NO (Missing/None)")
print("MAIL_DEFAULT_SENDER:", app.config['MAIL_DEFAULT_SENDER'])
print("DATABASE URI loaded:", "YES" if app.config['SQLALCHEMY_DATABASE_URI'] else "NO (Missing!)")
print("=" * 50)


# --- Database Model ---
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # Registration Verification Fields
    is_verified = db.Column(db.Boolean, default=False)
    otp = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)

    # Password Reset Fields
    reset_otp = db.Column(db.String(6), nullable=True)
    reset_otp_expiry = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


with app.app_context():
    try:
        db.create_all()
        
        # Explicitly patch all OTP and user fields into existing Render PostgreSQL schema
        with db.engine.connect() as conn:
            conn.execute(db.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS otp VARCHAR(6);"))
            conn.execute(db.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_expiry TIMESTAMP;"))
            conn.execute(db.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_otp VARCHAR(6);"))
            conn.execute(db.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_otp_expiry TIMESTAMP;"))
            conn.execute(db.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;"))
            conn.commit()
            
        print("✅ Database schema fully aligned and verified!")
    except Exception as e:
        print(f"⚠️ Schema check note: {str(e)}")
def generate_otp():
    return ''.join(random.choices(string.digits, k=6))


# =====================================================================
# 🛡️ GLOBAL ERROR HANDLERS
# =====================================================================

@app.errorhandler(ValidationError)
def handle_marshmallow_validation_error(err):
    return jsonify({
        'status': 'error',
        'message': 'Validation failed',
        'errors': err.messages
    }), 400


@app.errorhandler(HTTPException)
def handle_http_exception(e):
    return jsonify({
        'status': 'error',
        'message': e.description
    }), e.code


@app.errorhandler(Exception)
def handle_unexpected_error(e):
    app.logger.error(f"Unhandled Exception: {str(e)}")
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

@app.route('/', methods=['GET'])
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'success',
        'message': 'Flask Authentication API is up and running!'
    }), 200


@app.route('/api/auth/register', methods=['POST'])
def register():
    print("\n" + "!"*50, flush=True)
    print("➡️ REGISTER ROUTE HIT!", flush=True)
    print("Payload received:", request.get_json(), flush=True)
    print("!"*50 + "\n", flush=True)

    try:
        data = register_schema.load(request.get_json())
    except Exception as val_err:
        print(f"❌ MARSHMALLOW VALIDATION ERROR: {val_err}", flush=True)
        return jsonify({'message': 'Validation failed', 'errors': str(val_err)}), 400

    if User.query.filter((User.email == data['email']) | (User.username == data['username'])).first():
        print("⚠️ USER ALREADY EXISTS IN DATABASE", flush=True)
        return jsonify({'message': 'User with this email or username already exists'}), 409

    otp = generate_otp()
    otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=10)

    print("\n" + "="*50, flush=True)
    print(f"🔑 GENERATED OTP FOR {data['email']}: {otp}", flush=True)
    print("="*50 + "\n", flush=True)

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
        print("✅ USER SAVED TO DATABASE", flush=True)

        try:
            msg = Message(
                subject="Verify Your Account Registration",
                sender=(
                    "Authentication Service",
                    app.config['MAIL_USERNAME'],
                ),
                recipients=[new_user.email],
                body=f"Your verification code is: {otp}",
            )
            mail.send(msg)
            print("✅ Email sent successfully!", flush=True)
        except Exception as mail_err:
            import traceback
            print("\n" + "❌"*25, flush=True)
            print(f"⚠️ SMTP MAIL ERROR: {str(mail_err)}", flush=True)
            print("FULL MAIL TRACEBACK:", flush=True)
            traceback.print_exc()
            print("❌"*25 + "\n", flush=True)

        return jsonify({
            'message': 'Registration successful',
            'otp': otp
        }), 201

    except Exception as e:
        db.session.rollback()
        import traceback
        print("❌ DATABASE / SERVER ERROR:", flush=True)
        traceback.print_exc()
        return jsonify({'message': 'Error creating user', 'error': str(e)}), 500


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

    now = datetime.now(timezone.utc)
    user_otp_expiry = user.otp_expiry.replace(tzinfo=timezone.utc) if user.otp_expiry and user.otp_expiry.tzinfo is None else user.otp_expiry

    if user.otp != otp_input or (user_otp_expiry and user_otp_expiry < now):
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

    access_payload = {
        'user_id': user.id,
        'type': 'access',
        'exp': datetime.now(timezone.utc) + access_expires
    }
    access_token = jwt.encode(access_payload, secret_key, algorithm='HS256')

    refresh_payload = {
        'user_id': user.id,
        'type': 'refresh',
        'exp': datetime.now(timezone.utc) + refresh_expires
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


@app.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    payload = request.get_json() or {}
    data = forgot_password_schema.load(payload)
    email = data.get('email', '').strip().lower()

    user = User.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({"message": "If an account exists, an OTP has been sent."}), 200

    otp = generate_otp()
    expiry = datetime.now(timezone.utc) + timedelta(minutes=10)

    user.reset_otp = otp
    user.reset_otp_expiry = expiry
    db.session.commit()

    try:
        msg = Message(
            subject="Your Password Reset OTP",
            recipients=[email],
            body=f"Your OTP code is {otp}. It will expire in 10 minutes."
        )
        mail.send(msg)
        return jsonify({"message": "OTP sent to your email successfully"}), 200

    except Exception as e:
        print(f"⚠️ SMTP Delivery Failed: {str(e)}")
        print(f"🔑 LOCAL DEV FALLBACK OTP FOR {email}: {otp}")
        
        return jsonify({
            "message": "OTP generated (check server terminal logs if email didn't arrive)",
            "fallback_otp": otp
        }), 200


@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    payload = request.get_json() or {}
    data = reset_password_schema.load(payload)
    
    email = data.get('email', '').strip().lower()
    incoming_otp = str(data.get('otp', '')).strip()
    new_password = data.get('new_password', '').strip()

    user = User.query.filter_by(email=email).first()

    if not user or not user.reset_otp:
        return jsonify({"message": "Invalid request or token expired"}), 400

    stored_otp = str(user.reset_otp).strip()

    if stored_otp != incoming_otp:
        return jsonify({"message": "Incorrect or invalid OTP code"}), 400

    if user.reset_otp_expiry:
        current_time = datetime.now(timezone.utc)
        expiry_time = user.reset_otp_expiry
        if expiry_time.tzinfo is None:
            expiry_time = expiry_time.replace(tzinfo=timezone.utc)

        if current_time > expiry_time:
            return jsonify({"message": "OTP has expired. Please request a new one."}), 400

    user.set_password(new_password)
    user.reset_otp = None
    user.reset_otp_expiry = None
    db.session.commit()

    return jsonify({"message": "Password reset successfully. You can now login."}), 200


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
    }), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
import jwt
from functools import wraps
from flask import request, jsonify, current_app

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Import db and User inside decorator to prevent circular imports
        from app import db, User

        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            parts = auth_header.split(" ")
            if len(parts) == 2 and parts[0] == 'Bearer':
                token = parts[1]

        if not token:
            return jsonify({'message': 'Authorization token is missing!'}), 401

        try:
            # Use JWT_SECRET_KEY if set, otherwise fallback to SECRET_KEY
            secret_key = current_app.config.get('JWT_SECRET_KEY', current_app.config['SECRET_KEY'])
            data = jwt.decode(token, secret_key, algorithms=["HS256"])

            # 1️⃣ Verify token type is strictly 'access'
            if data.get('type') != 'access':
                return jsonify({'message': 'Invalid token type for route access.'}), 401

            # SQLAlchemy 2.0 modern lookup method
            current_user = db.session.get(User, data['user_id'])

            if not current_user:
                return jsonify({'message': 'User no longer exists'}), 401

            # 2️⃣ OTP Check: Block access if the user's email is not verified yet
            if not current_user.is_verified:
                return jsonify({'message': 'Account email is unverified. Please verify your OTP.'}), 403

        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401

        return f(current_user, *args, **kwargs)

    return decorated
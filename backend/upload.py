import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from werkzeug.exceptions import RequestEntityTooLarge

load_dotenv()

app = Flask(__name__)

# --- Configurations ---
app.config["MAX_CONTENT_LENGTH"] = int(
    os.getenv("MAX_CONTENT_LENGTH", 5 * 1024 * 1024)
)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/file_uploads",
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# --- Global Error Handlers ---
@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    max_mb = app.config["MAX_CONTENT_LENGTH"] / (1024 * 1024)
    return jsonify({
        "error": f"File size exceeds the maximum allowed limit of {max_mb:.1f}MB."
    }), 413


@app.errorhandler(404)
def handle_404_error(e):
    return jsonify({"error": "Resource not found"}), 404


@app.errorhandler(500)
def handle_500_error(e):
    return jsonify({"error": "An internal server error occurred"}), 500


# --- Database Model ---
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    avatar_url = db.Column(db.String(255), nullable=True)
    avatar_public_id = db.Column(db.String(255), nullable=True)


with app.app_context():
    db.create_all()


# --- API Routes ---

@app.route("/api/users", methods=["POST"])
def create_user():
    """Helper route to create test users."""
    data = request.get_json() or {}
    if not data.get("name"):
        return jsonify({"error": "Name field is required"}), 400

    new_user = User(name=data["name"])
    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"id": new_user.id, "name": new_user.name}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to create user: {str(e)}"}), 500


@app.route('/api/users/<int:user_id>/avatar', methods=['POST'])
def upload_user_avatar(user_id):
    user = db.get_or_404(User, user_id)

    # 1. Check if payload contains file
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400

    file = request.files['file']

    # 2. Check if file is selected
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # 3. Validate file extension
    if not allowed_file(file.filename):
        return jsonify({
            'error': f'Invalid file type. Allowed formats: {", ".join(ALLOWED_EXTENSIONS)}'
        }), 400

    # 4. Upload to Cloudinary & update database safely
    try:
        # Optional: Clean up existing Cloudinary image before uploading a new one
        if user.avatar_public_id:
            cloudinary.uploader.destroy(user.avatar_public_id)

        upload_result = cloudinary.uploader.upload(
            file, 
            folder="user_avatars"
        )

        user.avatar_url = upload_result.get('secure_url')
        user.avatar_public_id = upload_result.get('public_id')
        db.session.commit()

        return jsonify({
            'message': 'Avatar uploaded successfully',
            'user': {
                'id': user.id,
                'name': user.name,
                'avatar_url': user.avatar_url,
                'avatar_public_id': user.avatar_public_id
            }
        }), 200

    except cloudinary.exceptions.Error as e:
        return jsonify({'error': f'Cloudinary upload failed: {str(e)}'}), 502
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database or server error: {str(e)}'}), 500


@app.route("/api/users/<int:user_id>/avatar", methods=["DELETE"])
def delete_user_avatar(user_id):
    user = db.get_or_404(User, user_id)

    if not user.avatar_public_id:
        return jsonify({"error": "User does not have an active avatar"}), 400

    try:
        # 1. Remove file from Cloudinary
        cloudinary.uploader.destroy(user.avatar_public_id)

        # 2. Clear fields in PostgreSQL
        user.avatar_url = None
        user.avatar_public_id = None
        db.session.commit()

        return jsonify({"message": "Avatar deleted successfully"}), 200

    except cloudinary.exceptions.Error as e:
        return jsonify({"error": f"Cloudinary deletion failed: {str(e)}"}), 502
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Deletion failed: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)
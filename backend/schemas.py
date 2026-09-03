# schemas.py
from flask_marshmallow import Marshmallow
from marshmallow import fields, validate

ma = Marshmallow()

# 1️⃣ User Registration Schema
class RegisterSchema(ma.Schema):
    username = fields.String(
        required=True, 
        validate=validate.Length(min=3, max=30, error="Username must be between 3 and 30 characters.")
    )
    email = fields.Email(required=True, error_messages={"invalid": "Invalid email format."})
    password = fields.String(
        required=True, 
        validate=validate.Length(min=6, error="Password must be at least 6 characters long.")
    )

# 2️⃣ User Login Schema
class LoginSchema(ma.Schema):
    email = fields.Email(required=True, error_messages={"invalid": "Invalid email format."})
    password = fields.String(required=True)

# 3️⃣ Request OTP / Forgot Password Schema
class ForgotPasswordSchema(ma.Schema):
    email = fields.Email(required=True, error_messages={"invalid": "Please provide a valid email address."})

# 4️⃣ Verify Registration OTP Schema
class VerifyRegistrationSchema(ma.Schema):
    email = fields.Email(required=True, error_messages={"invalid": "Invalid email format."})
    otp = fields.String(
        required=True, 
        validate=validate.Length(equal=6, error="OTP code must be exactly 6 digits.")
    )

# 5️⃣ Reset Password Schema
class ResetPasswordSchema(ma.Schema):
    email = fields.Email(required=True, error_messages={"invalid": "Invalid email format."})
    otp = fields.String(
        required=True, 
        validate=validate.Length(equal=6, error="OTP code must be exactly 6 digits.")
    )
    new_password = fields.String(
        required=True, 
        validate=validate.Length(min=6, error="New password must be at least 6 characters long.")
    )

# 6️⃣ Dashboard Query Parameters Schema (Pagination, Search & Filter)
class DashboardQuerySchema(ma.Schema):
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Int(load_default=5, validate=validate.Range(min=1, max=100))
    search = fields.String(load_default="")
    status = fields.String(load_default="all")

# Instantiate schemas for easy import
register_schema = RegisterSchema()
login_schema = LoginSchema()
forgot_password_schema = ForgotPasswordSchema()
verify_registration_schema = VerifyRegistrationSchema()
reset_password_schema = ResetPasswordSchema()
dashboard_query_schema = DashboardQuerySchema()
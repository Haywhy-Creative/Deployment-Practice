import os
from datetime import timedelta
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
# Load environment variables from .env file
load_dotenv(os.path.join(basedir, '.env'))

def fix_postgres_uri(uri):
    """Ensures PostgreSQL URLs starting with 'postgres://' are converted to 'postgresql://'."""
    if uri and uri.startswith("postgres://"):
        return uri.replace("postgres://", "postgresql://", 1)
    return uri


class Config:
    """Base shared settings."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-fallback-secret-key-change-me')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT Configuration Constants
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)

    # 🆕 Mail Configuration Constants
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() in ['true', '1', 't']
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME'))

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    """Development settings."""
    DEBUG = True
    # Default to Vite local dev server (http://localhost:5173) or allow all '*'
    CORS_ORIGIN = os.getenv('CORS_ORIGIN', 'http://localhost:5173')
    
    # Safe local PostgreSQL fallback if DATABASE_URL is omitted in local .env
    DEFAULT_LOCAL_DB = 'postgresql://postgres:postgres@localhost:5432/auth_db'
    SQLALCHEMY_DATABASE_URI = fix_postgres_uri(os.getenv('DATABASE_URL', DEFAULT_LOCAL_DB))


class ProductionConfig(Config):
    """Production settings."""
    DEBUG = False
    CORS_ORIGIN = os.getenv('CORS_ORIGIN', '*')
    
    raw_db_url = os.getenv('DATABASE_URL')
    SQLALCHEMY_DATABASE_URI = fix_postgres_uri(raw_db_url)

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Enforce critical env vars in production startup
        assert os.getenv('DATABASE_URL'), "CRITICAL ERROR: DATABASE_URL is missing in environment!"
        assert os.getenv('SECRET_KEY') and os.getenv('SECRET_KEY') != 'dev-fallback-secret-key-change-me', \
            "CRITICAL ERROR: A secure SECRET_KEY must be defined in production environment!"
            
        # 🆕 Production Mail Checks
        assert os.getenv('MAIL_USERNAME'), "CRITICAL ERROR: MAIL_USERNAME is missing in production environment!"
        assert os.getenv('MAIL_PASSWORD'), "CRITICAL ERROR: MAIL_PASSWORD is missing in production environment!"


# Map FLASK_ENV values to config classes
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
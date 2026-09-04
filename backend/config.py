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

    # Mail Configuration Constants
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    # Default to 465 (SSL) if 587 (TLS) fails on Render
    MAIL_PORT = int(os.getenv('MAIL_PORT', 465))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'False').lower() in ['true', '1', 't']
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'True').lower() in ['true', '1', 't']
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME'))

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    """Development settings."""
    DEBUG = True
    CORS_ORIGIN = os.getenv('CORS_ORIGIN', 'http://localhost:5173')
    
    DEFAULT_LOCAL_DB = 'postgresql://postgres:postgres@localhost:5432/auth_db'
    SQLALCHEMY_DATABASE_URI = fix_postgres_uri(os.getenv('DATABASE_URL', DEFAULT_LOCAL_DB))


class ProductionConfig(Config):
    """Production settings."""
    DEBUG = False
    CORS_ORIGIN = os.getenv('CORS_ORIGIN', '*')

    # Safely evaluate DATABASE_URL with SQLite fallback to prevent crash if env is missing
    raw_db_url = os.getenv('DATABASE_URL')
    SQLALCHEMY_DATABASE_URI = fix_postgres_uri(raw_db_url) if raw_db_url else 'sqlite:///' + os.path.join(basedir, 'prod_fallback.db')

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Soft validation: Log warnings instead of crashing app on start
        if not os.getenv('DATABASE_URL'):
            app.logger.warning("WARNING: DATABASE_URL is missing in production environment!")
            
        if not os.getenv('MAIL_USERNAME') or not os.getenv('MAIL_PASSWORD'):
            app.logger.warning("WARNING: MAIL credentials are missing in production! Email sending will fail.")


# Map FLASK_ENV or APP_ENV values to config classes
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': ProductionConfig  # Set default to production for hosted platforms
}
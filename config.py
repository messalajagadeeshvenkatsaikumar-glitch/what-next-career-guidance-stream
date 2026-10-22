import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def get_required_env(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f'Environment variable {name} is required. Copy .env.example to .env and set it.')
    return value


class Config:
    SECRET_KEY = get_required_env('SECRET_KEY')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in {'1', 'true', 'yes', 'on'}
    PORT = int(os.environ.get('PORT', '5000'))
    MAIN_SITE_URL = os.environ.get('MAIN_SITE_URL', 'http://localhost:5000')
    ADMIN_SITE_URL = os.environ.get('ADMIN_SITE_URL', '').rstrip('/')
    CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', MAIN_SITE_URL)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get(
        'SESSION_COOKIE_SECURE', 'True' if not DEBUG else 'False'
    ).lower() in {'1', 'true', 'yes', 'on'}
    MYSQL_HOST = get_required_env('MYSQL_HOST')
    MYSQL_PORT = int(get_required_env('MYSQL_PORT'))
    MYSQL_USER = get_required_env('MYSQL_USER')
    MYSQL_PASSWORD = get_required_env('MYSQL_PASSWORD')
    MYSQL_DATABASE = get_required_env('MYSQL_DATABASE')
    MYSQL_SSL_MODE = os.environ.get('MYSQL_SSL_MODE', 'REQUIRED')
    MYSQL_SSL_CA = os.environ.get('MYSQL_SSL_CA')
    DB_AUTO_INIT = os.environ.get('DB_AUTO_INIT', 'False').lower() in {'1', 'true', 'yes', 'on'}
    SMTP_HOST = os.environ.get('SMTP_HOST')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
    SMTP_USER = os.environ.get('SMTP_USER')
    SMTP_PASS = os.environ.get('SMTP_PASS')
    SMTP_FROM_EMAIL = os.environ.get('SMTP_FROM_EMAIL')
    SMTP_FROM_NAME = os.environ.get('SMTP_FROM_NAME', 'WHAT NEXT? Team')
    SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'True').lower() in {'1', 'true', 'yes', 'on'}
    SMTP_USE_SSL = os.environ.get('SMTP_USE_SSL', 'False').lower() in {'1', 'true', 'yes', 'on'}
    SMTP_TIMEOUT_SECONDS = int(os.environ.get('SMTP_TIMEOUT_SECONDS', '10'))

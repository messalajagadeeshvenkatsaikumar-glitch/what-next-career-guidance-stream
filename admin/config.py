import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent


def resolve_ssl_ca(value):
    if not value:
        return None

    ca_path = Path(value)
    if ca_path.is_absolute():
        return str(ca_path)

    for base_dir in (Path.cwd(), PROJECT_ROOT, BASE_DIR, PROJECT_ROOT.parent):
        candidate = base_dir / ca_path
        if candidate.is_file():
            return str(candidate)

    return str(ca_path)


def get_required_env(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Environment variable {name} is required. Copy .env.example to .env and set it."
        )
    return value


class Config:
    SECRET_KEY = get_required_env('SECRET_KEY')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in {'1', 'true', 'yes', 'on'}

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False

    MYSQL_HOST = get_required_env('MYSQL_HOST')
    MYSQL_PORT = int(get_required_env('MYSQL_PORT'))
    MYSQL_USER = get_required_env('MYSQL_USER')
    MYSQL_PASSWORD = get_required_env('MYSQL_PASSWORD')
    MYSQL_DATABASE = get_required_env('MYSQL_DATABASE')

    MYSQL_SSL_MODE = get_required_env('MYSQL_SSL_MODE')
    MYSQL_SSL_CA = resolve_ssl_ca(os.environ.get('MYSQL_SSL_CA'))
    DB_AUTO_INIT = os.environ.get('DB_AUTO_INIT', 'False').lower() in {'1', 'true', 'yes', 'on'}
    PORT = int(os.environ.get('ADMIN_PORT', '5002'))

    ADMIN_USERNAME = get_required_env('ADMIN_USERNAME')
    ADMIN_PASSWORD = get_required_env('ADMIN_PASSWORD')

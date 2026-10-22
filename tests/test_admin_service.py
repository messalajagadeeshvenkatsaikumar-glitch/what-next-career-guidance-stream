import importlib

import mysql.connector


class FakeCursor:
    def __init__(self):
        self.closed = False

    def execute(self, statement):
        assert statement == 'SELECT 1'

    def fetchone(self):
        return (1,)

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self):
        self.cursor_instance = FakeCursor()
        self.closed = False

    def cursor(self):
        return self.cursor_instance

    def close(self):
        self.closed = True


def load_admin_app(monkeypatch):
    for name, value in {
        'SECRET_KEY': 'test-secret',
        'MYSQL_HOST': 'managed-db.example',
        'MYSQL_PORT': '27920',
        'MYSQL_USER': 'avnadmin',
        'MYSQL_PASSWORD': 'test-password',
        'MYSQL_DATABASE': 'defaultdb',
        'MYSQL_SSL_MODE': 'REQUIRED',
        'ADMIN_USERNAME': 'admin',
        'ADMIN_PASSWORD': 'test-admin-password',
    }.items():
        monkeypatch.setenv(name, value)

    import admin.config as config_module
    importlib.reload(config_module)
    app_module = importlib.import_module('admin.admin_site.app')
    return importlib.reload(app_module)


def test_admin_health_reports_shared_database_connection(monkeypatch):
    app_module = load_admin_app(monkeypatch)
    assert app_module.mysql_config()['host'] == 'managed-db.example'
    connection = FakeConnection()
    monkeypatch.setattr(
        app_module.mysql.connector,
        'connect',
        lambda **_kwargs: connection,
    )

    response = app_module.app.test_client().get('/health')

    assert response.status_code == 200
    assert response.get_json() == {'status': 'ok', 'database': 'connected'}
    assert connection.cursor_instance.closed is True
    assert connection.closed is True


def test_admin_health_reports_database_connection_failure(monkeypatch):
    app_module = load_admin_app(monkeypatch)

    def fail_to_connect(**_kwargs):
        raise mysql.connector.Error('database unavailable')

    monkeypatch.setattr(app_module.mysql.connector, 'connect', fail_to_connect)

    response = app_module.app.test_client().get('/health')

    assert response.status_code == 503
    assert response.get_json() == {'status': 'error', 'database': 'disconnected'}

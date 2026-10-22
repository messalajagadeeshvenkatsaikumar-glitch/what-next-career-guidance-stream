import importlib

import pytest

import email_service
import migrations


def test_smtp_delivery_uses_server_side_tls_and_never_exposes_credentials(monkeypatch):
    calls = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            calls.append(('connect', host, port, timeout))

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def starttls(self):
            calls.append(('starttls',))

        def login(self, username, password):
            calls.append(('login', username, password))

        def send_message(self, message):
            calls.append(('send', message['To'], message['Subject'], message.get_content()))

    monkeypatch.setattr(email_service.smtplib, 'SMTP', FakeSMTP)
    config = {
        'SMTP_HOST': 'smtp.example.test', 'SMTP_PORT': 587,
        'SMTP_USER': 'mailer', 'SMTP_PASS': 'not-in-a-response',
        'SMTP_FROM_EMAIL': 'no-reply@example.test', 'SMTP_FROM_NAME': 'WHAT NEXT?',
        'SMTP_USE_TLS': True, 'SMTP_USE_SSL': False, 'SMTP_TIMEOUT_SECONDS': 7,
    }

    email_service.send_email(
        config, 'student@example.test', 'Test message', 'Test body'
    )

    assert calls[0] == ('connect', 'smtp.example.test', 587, 7)
    assert ('starttls',) in calls
    assert ('login', 'mailer', 'not-in-a-response') in calls
    assert calls[-1][1:3] == ('student@example.test', 'Test message')
    assert 'Test body' in calls[-1][3]


def test_email_headers_reject_newline_injection():
    with pytest.raises(ValueError):
        email_service.send_email(
            {'SMTP_HOST': 'smtp.example.test', 'SMTP_PORT': 587, 'SMTP_FROM_EMAIL': 'noreply@example.test'},
            'student@example.test\nBcc: attacker@example.test', 'Hello', 'Body',
        )


def test_additive_migration_creates_only_admin_reply_structures():
    class Cursor:
        def __init__(self, row=None):
            self.row = row

        def fetchone(self):
            return self.row

    class FakeDatabase:
        def __init__(self):
            self.calls = []
            self.committed = False

        def execute(self, statement, params=()):
            self.calls.append((statement, params))
            if 'FROM schema_migrations' in statement:
                return Cursor(None)
            if 'FROM information_schema.columns' in statement:
                return Cursor(None)
            return Cursor()

        def commit(self):
            self.committed = True

    db = FakeDatabase()
    assert migrations.apply_migrations(db) is True
    statements = '\n'.join(statement for statement, _params in db.calls)
    assert 'ALTER TABLE feedback ADD COLUMN status' in statements
    assert 'CREATE TABLE IF NOT EXISTS contact_message_replies' in statements
    assert db.committed is True


def test_additive_migration_repairs_missing_columns_when_already_recorded():
    class Cursor:
        def __init__(self, row=None):
            self.row = row

        def fetchone(self):
            return self.row

    class FakeDatabase:
        def __init__(self):
            self.calls = []
            self.committed = False

        def execute(self, statement, params=()):
            self.calls.append((statement, params))
            if 'FROM schema_migrations' in statement:
                return Cursor({'1': 1})
            if 'FROM information_schema.columns' in statement:
                return Cursor(None)
            return Cursor()

        def commit(self):
            self.committed = True

    db = FakeDatabase()
    assert migrations.apply_migrations(db) is False

    statements = [statement for statement, _params in db.calls]
    assert any('ALTER TABLE feedback ADD COLUMN status' in statement for statement in statements)
    assert not any('INSERT INTO schema_migrations' in statement for statement in statements)
    assert db.committed is True


def test_login_page_only_offers_sign_in(monkeypatch):
    for name, value in {
        'SECRET_KEY': 'test-secret', 'MYSQL_HOST': 'managed-db.example', 'MYSQL_PORT': '3306',
        'MYSQL_USER': 'app', 'MYSQL_PASSWORD': 'test-password', 'MYSQL_DATABASE': 'career',
        'MYSQL_SSL_MODE': 'REQUIRED', 'ADMIN_SITE_URL': 'https://admin.example.test',
    }.items():
        monkeypatch.setenv(name, value)
    import app as app_module
    importlib.reload(app_module)
    logout_rule = next(rule for rule in app_module.app.url_map.iter_rules() if rule.rule == '/logout')
    assert logout_rule.methods == {'POST', 'OPTIONS'}
    monkeypatch.setitem(app_module.app.config, 'DB_INITIALIZED', True)
    client = app_module.app.test_client()
    login_response = client.get('/login')
    assert login_response.status_code == 200
    assert login_response.data.count(b'<form') == 1
    assert b'action="/login"' in login_response.data
    with app_module.app.test_request_context('/logout', method='POST', data={'csrf_token': 'expected'}):
        app_module.session['_csrf_token'] = 'expected'
        app_module.session['user_id'] = 123
        response = app_module.app.view_functions['logout']()
        assert response.status_code == 302
        assert 'user_id' not in app_module.session

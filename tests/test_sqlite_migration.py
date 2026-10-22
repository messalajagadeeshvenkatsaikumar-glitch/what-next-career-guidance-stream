from pathlib import Path

import db


class FakeCursor:
    def __init__(self):
        self.closed = False
        self.executed = None

    def execute(self, sql, params=()):
        self.executed = (sql, params)

    def fetchone(self):
        return {'1': 1}

    def fetchall(self):
        return [{'table_name': name} for name in db.REQUIRED_TABLES]

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self):
        self.cursor_instance = FakeCursor()
        self.closed = False

    def cursor(self, dictionary=False):
        assert dictionary is True
        return self.cursor_instance

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        self.closed = True


def test_mysql_config_reads_managed_database_environment(monkeypatch, tmp_path):
    ca_file = tmp_path / 'ca.pem'
    ca_file.write_text('test certificate', encoding='utf-8')
    monkeypatch.setenv('MYSQL_HOST', 'managed-db.example')
    monkeypatch.setenv('MYSQL_PORT', '27920')
    monkeypatch.setenv('MYSQL_USER', 'avnadmin')
    monkeypatch.setenv('MYSQL_PASSWORD', 'test-password')
    monkeypatch.setenv('MYSQL_DATABASE', 'defaultdb')
    monkeypatch.setenv('MYSQL_SSL_MODE', 'VERIFY_CA')
    monkeypatch.setenv('MYSQL_SSL_CA', str(ca_file))

    config = db.mysql_config()

    assert config['host'] == 'managed-db.example'
    assert config['port'] == 27920
    assert config['database'] == 'defaultdb'
    assert config['ssl_disabled'] is False
    assert config['ssl_verify_cert'] is True
    assert config['ssl_ca'] == str(ca_file.resolve())


def test_mysql_config_defaults_ssl_mode_to_required(monkeypatch):
    for name, value in {
        'MYSQL_HOST': 'managed-db.example',
        'MYSQL_PORT': '27920',
        'MYSQL_USER': 'avnadmin',
        'MYSQL_PASSWORD': 'test-password',
        'MYSQL_DATABASE': 'defaultdb',
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv('MYSQL_SSL_MODE', raising=False)
    monkeypatch.delenv('MYSQL_SSL_CA', raising=False)

    config = db.mysql_config()

    assert config['ssl_disabled'] is False
    assert config['ssl_verify_cert'] is False
    assert 'ssl_ca' not in config


def test_mysql_config_reports_missing_ca_file(monkeypatch):
    for name, value in {
        'MYSQL_HOST': 'managed-db.example',
        'MYSQL_PORT': '27920',
        'MYSQL_USER': 'avnadmin',
        'MYSQL_PASSWORD': 'test-password',
        'MYSQL_DATABASE': 'defaultdb',
        'MYSQL_SSL_MODE': 'VERIFY_CA',
        'MYSQL_SSL_CA': 'certs/missing-ca.pem',
    }.items():
        monkeypatch.setenv(name, value)

    try:
        db.mysql_config()
    except ValueError as error:
        assert 'MYSQL_SSL_CA file not found' in str(error)
        assert 'MYSQL_SSL_MODE=REQUIRED' in str(error)
    else:
        raise AssertionError('A missing CA certificate must be reported clearly.')


def test_required_ssl_does_not_load_optional_ca_file(monkeypatch):
    for name, value in {
        'MYSQL_HOST': 'managed-db.example',
        'MYSQL_PORT': '27920',
        'MYSQL_USER': 'avnadmin',
        'MYSQL_PASSWORD': 'test-password',
        'MYSQL_DATABASE': 'defaultdb',
        'MYSQL_SSL_MODE': 'REQUIRED',
        'MYSQL_SSL_CA': 'certs/missing-ca.pem',
    }.items():
        monkeypatch.setenv(name, value)

    config = db.mysql_config()

    assert config['ssl_disabled'] is False
    assert config['ssl_verify_cert'] is False
    assert 'ssl_ca' not in config


def test_mysql_config_rejects_mysql_system_schemas(monkeypatch):
    for name, value in {
        'MYSQL_HOST': 'managed-db.example',
        'MYSQL_PORT': '27920',
        'MYSQL_USER': 'avnadmin',
        'MYSQL_PASSWORD': 'test-password',
        'MYSQL_DATABASE': 'sys',
        'MYSQL_SSL_MODE': 'REQUIRED',
    }.items():
        monkeypatch.setenv(name, value)

    try:
        db.mysql_config()
    except ValueError as error:
        assert 'dedicated application database' in str(error)
    else:
        raise AssertionError('MySQL system schemas must not be accepted.')


def test_verify_schema_reports_missing_tables():
    class MissingSchemaDatabase:
        def execute(self, _sql):
            class Cursor:
                def fetchall(self):
                    return [{'table_name': 'users'}]
            return Cursor()

    try:
        db.verify_schema(MissingSchemaDatabase())
    except db.DatabaseSchemaError as error:
        assert 'career_recommendations' in str(error)
        assert 'database.sql' in str(error)
    else:
        raise AssertionError('An incomplete schema must be rejected.')


def test_database_uses_mysql_placeholders_and_closes_cursors(monkeypatch):
    connection = FakeConnection()
    monkeypatch.setattr(db.mysql.connector, 'connect', lambda **kwargs: connection)
    for name, value in {
        'MYSQL_HOST': 'managed-db.example',
        'MYSQL_PORT': '27920',
        'MYSQL_USER': 'avnadmin',
        'MYSQL_PASSWORD': 'test-password',
        'MYSQL_DATABASE': 'defaultdb',
        'MYSQL_SSL_MODE': 'REQUIRED',
    }.items():
        monkeypatch.setenv(name, value)

    database = db.connect_db()
    database.execute('SELECT * FROM users WHERE email = %s', ('user@example.com',))
    database.close()

    assert connection.cursor_instance.executed == (
        'SELECT * FROM users WHERE email = %s', ('user@example.com',)
    )
    assert connection.cursor_instance.closed is True
    assert connection.closed is True


def test_schema_is_mysql_compatible():
    schema = (Path(db.BASE_DIR) / 'database.sql').read_text(encoding='utf-8').lower()
    assert 'create table if not exists users' in schema
    assert 'auto_increment' in schema
    assert 'engine=innodb' in schema
    for table_name in db.REQUIRED_TABLES:
        assert f'create table if not exists {table_name}' in schema


def test_init_db_handles_connection_errors(monkeypatch):
    for name, value in {
        'SECRET_KEY': 'test-secret',
        'MYSQL_HOST': 'managed-db.example',
        'MYSQL_PORT': '27920',
        'MYSQL_USER': 'avnadmin',
        'MYSQL_PASSWORD': 'test-password',
        'MYSQL_DATABASE': 'defaultdb',
        'MYSQL_SSL_MODE': 'REQUIRED',
        'ADMIN_USERNAME': 'admin',
        'ADMIN_PASSWORD': 'secret',
    }.items():
        monkeypatch.setenv(name, value)

    import app as app_module

    def raising_get_db():
        raise RuntimeError('db unavailable')

    monkeypatch.setattr(app_module, 'get_db', raising_get_db)
    assert app_module.init_db() is False


def test_init_db_creates_schema_when_auto_init_is_enabled(monkeypatch):
    import importlib

    for name, value in {
        'SECRET_KEY': 'test-secret',
        'MYSQL_HOST': 'managed-db.example',
        'MYSQL_PORT': '27920',
        'MYSQL_USER': 'avnadmin',
        'MYSQL_PASSWORD': 'test-password',
        'MYSQL_DATABASE': 'defaultdb',
        'MYSQL_SSL_MODE': 'REQUIRED',
        'ADMIN_USERNAME': 'admin',
        'ADMIN_PASSWORD': 'secret',
        'DB_AUTO_INIT': 'True',
    }.items():
        monkeypatch.setenv(name, value)

    import app as app_module
    importlib.reload(app_module)

    class SchemaDatabase:
        def __init__(self):
            self.statements = []

        def execute(self, statement, _params=()):
            assert not _params
            self.statements.append(statement)
            return FakeCursor()

        def commit(self):
            pass

        def close(self):
            pass

    database = SchemaDatabase()
    monkeypatch.setattr(app_module, 'connect_db', lambda: database)
    monkeypatch.setitem(app_module.app.config, 'DB_AUTO_INIT', True)
    migrated_databases = []
    monkeypatch.setattr(
        app_module, 'apply_migrations',
        lambda migration_db: migrated_databases.append(migration_db),
    )

    def skip_seed_data(_database, _career_data):
        assert _database is database
        assert _career_data is app_module.CAREER_DATA

    monkeypatch.setattr(app_module, 'ensure_seed_data', skip_seed_data)

    assert app_module.init_db() is True
    assert any('CREATE TABLE IF NOT EXISTS users' in sql for sql in database.statements)
    assert any('CREATE TABLE IF NOT EXISTS quiz_results' in sql for sql in database.statements)
    assert migrated_databases == [database]


def test_safe_error_message_redacts_passwords(monkeypatch):
    for name, value in {
        'SECRET_KEY': 'test-secret',
        'MYSQL_HOST': 'managed-db.example',
        'MYSQL_PORT': '27920',
        'MYSQL_USER': 'avnadmin',
        'MYSQL_PASSWORD': 'test-password',
        'MYSQL_DATABASE': 'defaultdb',
        'MYSQL_SSL_MODE': 'REQUIRED',
        'ADMIN_USERNAME': 'admin',
        'ADMIN_PASSWORD': 'secret',
    }.items():
        monkeypatch.setenv(name, value)

    import app as app_module

    message = app_module.safe_error_message(RuntimeError('connect failed with password=super-secret and user=admin'))
    assert 'super-secret' not in message
    assert '<redacted>' in message


def test_health_endpoint_reports_database_status(monkeypatch):
    for name, value in {
        'SECRET_KEY': 'test-secret',
        'MYSQL_HOST': 'managed-db.example',
        'MYSQL_PORT': '27920',
        'MYSQL_USER': 'avnadmin',
        'MYSQL_PASSWORD': 'test-password',
        'MYSQL_DATABASE': 'defaultdb',
        'MYSQL_SSL_MODE': 'REQUIRED',
        'ADMIN_USERNAME': 'admin',
        'ADMIN_PASSWORD': 'secret',
    }.items():
        monkeypatch.setenv(name, value)

    import importlib
    import app as app_module
    importlib.reload(app_module)

    monkeypatch.setenv('DB_AUTO_INIT', 'False')
    monkeypatch.setattr(app_module, 'connect_db', lambda: db.Database(FakeConnection()))
    client = app_module.app.test_client()
    response = client.get('/health')

    assert response.status_code == 200
    assert response.get_json()['status'] == 'ok'
    assert response.get_json()['database'] == 'connected'


def test_database_errors_are_returned_without_exposing_password(monkeypatch):
    for name, value in {
        'SECRET_KEY': 'test-secret',
        'MYSQL_HOST': 'managed-db.example',
        'MYSQL_PORT': '27920',
        'MYSQL_USER': 'avnadmin',
        'MYSQL_PASSWORD': 'test-password',
        'MYSQL_DATABASE': 'defaultdb',
        'MYSQL_SSL_MODE': 'REQUIRED',
        'ADMIN_USERNAME': 'admin',
        'ADMIN_PASSWORD': 'secret',
        'DB_AUTO_INIT': 'False',
    }.items():
        monkeypatch.setenv(name, value)

    import importlib
    import app as app_module
    importlib.reload(app_module)

    def raise_connection_error():
        raise db.Error('Access denied: password=test-password')

    monkeypatch.setattr(app_module, 'connect_db', raise_connection_error)
    client = app_module.app.test_client()

    health_response = client.get('/health')
    assert health_response.status_code == 503
    assert health_response.get_json()['message'] == 'Access denied: password=<redacted>'

    page_response = client.get('/', headers={'Accept': 'text/html'})
    assert page_response.status_code == 503
    assert 'Access denied: password=&lt;redacted&gt;' in page_response.get_data(as_text=True)
    assert page_response.mimetype == 'text/html'
    assert 'test-password' not in page_response.get_data(as_text=True)

    api_response = client.get('/api/questions', headers={'Accept': 'application/json'})
    assert api_response.status_code == 503
    assert api_response.get_json()['message'] == 'Access denied: password=<redacted>'

import logging
import sys
from types import ModuleType

import pytest

import run_server


def test_main_passes_render_port_to_gunicorn(monkeypatch, caplog):
    monkeypatch.setenv('PORT', '5123')
    calls = []

    gunicorn_module = ModuleType('gunicorn')
    gunicorn_app_module = ModuleType('gunicorn.app')
    gunicorn_wsgi_module = ModuleType('gunicorn.app.wsgiapp')
    gunicorn_wsgi_module.run = lambda: calls.append(sys.argv.copy())
    monkeypatch.setitem(sys.modules, 'gunicorn', gunicorn_module)
    monkeypatch.setitem(sys.modules, 'gunicorn.app', gunicorn_app_module)
    monkeypatch.setitem(sys.modules, 'gunicorn.app.wsgiapp', gunicorn_wsgi_module)

    with caplog.at_level(logging.INFO):
        run_server.main()

    assert calls == [[
        'gunicorn',
        '--bind', '0.0.0.0:5123',
        '--log-level', 'info',
        '--error-logfile', '-',
        '--capture-output',
        'app:app',
    ]]
    assert 'Starting Gunicorn on 0.0.0.0:5123' in caplog.text


@pytest.mark.parametrize('port', ['0', '65536', 'not-a-port'])
def test_main_rejects_invalid_port(monkeypatch, port):
    monkeypatch.setenv('PORT', port)

    with pytest.raises(ValueError, match='PORT must be an integer between 1 and 65535'):
        run_server.get_port()

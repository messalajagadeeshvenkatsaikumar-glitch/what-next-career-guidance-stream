import logging
import os
import sys


def get_port():
    port_value = os.environ.get('PORT', '5000').strip()
    try:
        port = int(port_value)
    except ValueError as error:
        raise ValueError('PORT must be an integer between 1 and 65535.') from error
    if not 1 <= port <= 65535:
        raise ValueError('PORT must be an integer between 1 and 65535.')
    return port


def main():
    port = get_port()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    logging.info('Starting Gunicorn on 0.0.0.0:%s', port)
    sys.argv = [
        'gunicorn',
        '--bind', f'0.0.0.0:{port}',
        '--log-level', 'info',
        '--error-logfile', '-',
        '--capture-output',
        'app:app',
    ]

    from gunicorn.app.wsgiapp import run

    run()


if __name__ == '__main__':
    main()

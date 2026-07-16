web: cd leadrescue && python manage.py migrate --noinput && gunicorn config.wsgi --bind 0.0.0.0:$PORT
worker: cd leadrescue && celery -A config worker --loglevel=info

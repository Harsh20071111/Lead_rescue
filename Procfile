web: gunicorn config.wsgi --chdir leadrescue --bind 0.0.0.0:$PORT
worker: celery -A config worker --loglevel=info --chdir leadrescue

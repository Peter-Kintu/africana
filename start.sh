#!/bin/bash
python manage.py cleanup_duplicate_uuids
python manage.py migrate
python -m gunicorn africana.wsgi
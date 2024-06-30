#!/bin/sh

echo "Starting development web server $(date)"

# Run Django management commands
python manage.py makemigrations
python manage.py migrate

result=$?
if [ "$result" != 0 ]; then
    exit 1
fi

# Start the Django development server
python manage.py runserver 0.0.0.0:8000
#!/bin/sh
# Prepares the database and then runs the container command (gunicorn).
set -eu

if [ "${DJANGO_RUN_MIGRATIONS:-1}" = "1" ]; then
    python src/manage.py migrate --noinput
fi

# Demo users and reservations for the assessment. The command is idempotent,
# but it resets the demo passwords, so keep it off outside a demo environment.
if [ "${DJANGO_SEED_DEMO_DATA:-0}" = "1" ]; then
    python src/manage.py seed_assessment_data
fi

exec "$@"

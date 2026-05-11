#!/bin/sh
set -e

PUID=${PUID:-1000}
PGID=${PGID:-1000}

# Ensure group and user exist with the requested IDs
if ! getent group "$PGID" > /dev/null 2>&1; then
    groupadd -g "$PGID" appgroup
fi
if ! getent passwd "$PUID" > /dev/null 2>&1; then
    useradd -u "$PUID" -g "$PGID" --no-create-home appuser
fi

# Fix ownership of volume mount points so the app can write to them
chown -R "$PUID:$PGID" /app/config /app/data

exec gosu "$PUID:$PGID" "$@"

#!/bin/sh
set -e

# Default PUID/PGID to 1000 if not set.
PUID="${PUID:-1000}"
PGID="${PGID:-1000}"

# Reject root UID/GID.
if [ "$PUID" = "0" ] || [ "$PGID" = "0" ]; then
    echo "ERROR: PUID and PGID must be non-zero. Refusing to run as root." >&2
    exit 1
fi

# Validate numeric values.
case "$PUID" in
    ''|*[!0-9]*)
        echo "ERROR: PUID must be a positive integer, got '$PUID'." >&2
        exit 1
        ;;
esac
case "$PGID" in
    ''|*[!0-9]*)
        echo "ERROR: PGID must be a positive integer, got '$PGID'." >&2
        exit 1
        ;;
esac

echo "Setting up user binocular with PUID=$PUID and PGID=$PGID"

# Create or modify group.
if getent group binocular >/dev/null 2>&1; then
    groupmod -o -g "$PGID" binocular
else
    groupadd -o -g "$PGID" binocular
fi

# Create or modify user.
if id binocular >/dev/null 2>&1; then
    usermod -o -u "$PUID" -g "$PGID" binocular
else
    useradd -o -u "$PUID" -g "$PGID" -M -d /app -s /bin/sh binocular
fi

# Ensure data and modules directories exist and are owned correctly.
mkdir -p /app/data /app/modules
chown "$PUID:$PGID" /app/data /app/modules

# Drop privileges and exec the application.
exec su-exec binocular:binocular "$@"

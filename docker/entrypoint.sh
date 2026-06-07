#!/bin/sh
set -e

# ---------------------------------------------------------------------------
# PUID / PGID Entrypoint — linuxserver.io-style user mapping
#
# Reads PUID and PGID env vars, creates matching user:group, chowns volumes,
# and drops privileges via su-exec (or gosu fallback) before exec'ing CMD.
# ---------------------------------------------------------------------------

# --- Determine privilege-drop tool ---
SU_EXEC=""
if command -v su-exec >/dev/null 2>&1; then
    SU_EXEC="su-exec"
    echo "[entrypoint] INFO: Using su-exec" >&2
elif command -v gosu >/dev/null 2>&1; then
    SU_EXEC="gosu"
    echo "[entrypoint] INFO: Using gosu" >&2
else
    echo "[entrypoint] ERROR: Neither su-exec nor gosu found in PATH" >&2
    exit 2
fi

# --- Trap SIGTERM/SIGINT before chown ---
trap_handler() {
    echo "[entrypoint] WARNING: Received SIGTERM — chown may be incomplete" >&2
    exit 0
}
trap 'trap_handler' TERM INT

# --- Resolve and validate PUID ---
if [ -z "${PUID+x}" ]; then
    # Unset → silent default
    PUID=1000
elif [ -z "${PUID}" ]; then
    # Set but empty → non-numeric fallback
    echo "[entrypoint] WARNING: PUID= is non-numeric, falling back to 1000" >&2
    PUID=1000
else
    case "${PUID}" in
        *[!0-9]*)
            echo "[entrypoint] WARNING: PUID=${PUID} is non-numeric, falling back to 1000" >&2
            PUID=1000
            ;;
        *)
            if [ "${PUID}" = "0" ]; then
                echo "[entrypoint] ERROR: PUID must not be 0" >&2
                exit 1
            fi
            if [ "${#PUID}" -gt 10 ] || [ "${PUID}" -gt 4294967294 ] 2>/dev/null; then
                echo "[entrypoint] ERROR: PUID=${PUID} is out of range (1-4294967294)" >&2
                exit 4
            fi
            ;;
    esac
fi

# --- Resolve and validate PGID ---
if [ -z "${PGID+x}" ]; then
    PGID=1000
elif [ -z "${PGID}" ]; then
    echo "[entrypoint] WARNING: PGID= is non-numeric, falling back to 1000" >&2
    PGID=1000
else
    case "${PGID}" in
        *[!0-9]*)
            echo "[entrypoint] WARNING: PGID=${PGID} is non-numeric, falling back to 1000" >&2
            PGID=1000
            ;;
        *)
            if [ "${PGID}" = "0" ]; then
                echo "[entrypoint] ERROR: PGID must not be 0" >&2
                exit 1
            fi
            if [ "${#PGID}" -gt 10 ] || [ "${PGID}" -gt 4294967294 ] 2>/dev/null; then
                echo "[entrypoint] ERROR: PGID=${PGID} is out of range (1-4294967294)" >&2
                exit 4
            fi
            ;;
    esac
fi

# --- Log resolved identity ---
echo "[entrypoint] INFO: Resolved PUID=${PUID} PGID=${PGID} user=app" >&2

# --- Create or reuse group ---
if getent group "${PGID}" >/dev/null 2>&1; then
    GROUP_NAME="$(getent group "${PGID}" | cut -d: -f1)"
    echo "[entrypoint] INFO: Reusing existing group ${GROUP_NAME} (GID ${PGID})" >&2
else
    groupadd -g "${PGID}" app
    GROUP_NAME="app"
fi

# --- Create or reuse user ---
if getent passwd "${PUID}" >/dev/null 2>&1; then
    USER_INFO="$(getent passwd "${PUID}")"
    USER_NAME="$(echo "${USER_INFO}" | cut -d: -f1)"
    USER_SHELL="$(echo "${USER_INFO}" | cut -d: -f7)"
    USER_HOME="$(echo "${USER_INFO}" | cut -d: -f6)"
    echo "[entrypoint] INFO: Reusing existing user ${USER_NAME} (UID ${PUID}) with shell ${USER_SHELL} home ${USER_HOME}" >&2
else
    useradd -u "${PUID}" -g "${PGID}" -d /app -M -s /usr/sbin/nologin app
    USER_NAME="app"
fi

# --- chown /app/data ---
DATA_START=$(date +%s)
if ! chown -R --no-dereference "${PUID}:${PGID}" /app/data 2>/dev/null; then
    echo "[entrypoint] ERROR: Failed to chown /app/data" >&2
    exit 3
fi
DATA_END=$(date +%s)
DATA_DURATION=$((DATA_END - DATA_START))
echo "[entrypoint] INFO: chown /app/data completed in ${DATA_DURATION}s" >&2

# --- chown /app/modules ---
MOD_START=$(date +%s)
if ! chown -R --no-dereference "${PUID}:${PGID}" /app/modules 2>/dev/null; then
    # Distinguish read-only rootfs from a genuine failure
    if touch /tmp/.probe 2>/dev/null; then
        rm -f /tmp/.probe
        echo "[entrypoint] ERROR: Failed to chown /app/modules" >&2
        exit 3
    else
        echo "[entrypoint] WARNING: Read-only rootfs detected — ownership unchanged" >&2
    fi
fi
MOD_END=$(date +%s)
MOD_DURATION=$((MOD_END - MOD_START))
echo "[entrypoint] INFO: chown /app/modules completed in ${MOD_DURATION}s" >&2

# --- Done — drop privileges and exec CMD ---
echo "[entrypoint] INFO: entrypoint complete, starting application via ${SU_EXEC}" >&2
exec "${SU_EXEC}" "${USER_NAME}" "$@"

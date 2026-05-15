#!/usr/bin/env bash
# Install and enable the homeassistant-server systemd service.
#
# Usage:
#   sudo ./install-server-service.sh [INSTALL_DIR] [SERVICE_USER]
#
# Defaults:
#   INSTALL_DIR  = /opt/homeassistant
#   SERVICE_USER = homeassistant
#
# What this script does:
#   1. Creates the service user (if it doesn't exist)
#   2. Copies the project to INSTALL_DIR (if not already there)
#   3. Creates a Python venv and installs server requirements
#   4. Writes the service file to /etc/systemd/system/
#   5. Reloads systemd, enables and starts the service

set -euo pipefail

INSTALL_DIR="${1:-/opt/homeassistant}"
SERVICE_USER="${2:-homeassistant}"
SERVICE_FILE="homeassistant-server.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "==> Install dir  : $INSTALL_DIR"
echo "==> Service user : $SERVICE_USER"

# ── 1. Create service user ────────────────────────────────────────────────────
if ! id "$SERVICE_USER" &>/dev/null; then
    echo "==> Creating user $SERVICE_USER"
    useradd --system --no-create-home --shell /usr/sbin/nologin "$SERVICE_USER"
fi

# ── 2. Copy project files ─────────────────────────────────────────────────────
echo "==> Copying project to $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
rsync -a --exclude='.git' --exclude='venv' --exclude='__pycache__' \
    "$PROJECT_ROOT/" "$INSTALL_DIR/"
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"

# ── 3. Create venv and install dependencies ───────────────────────────────────
VENV="$INSTALL_DIR/venv"
if [ ! -d "$VENV" ]; then
    echo "==> Creating venv at $VENV"
    python3 -m venv "$VENV"
fi
echo "==> Installing server requirements"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$INSTALL_DIR/requirements-server.txt"
chown -R "$SERVICE_USER:$SERVICE_USER" "$VENV"

# ── 4. Write service file ─────────────────────────────────────────────────────
SERVICE_SRC="$SCRIPT_DIR/$SERVICE_FILE"
SERVICE_DEST="/etc/systemd/system/$SERVICE_FILE"
echo "==> Writing service file to $SERVICE_DEST"

# Substitute the install dir into the unit file (handles non-default paths)
sed "s|/opt/homeassistant|$INSTALL_DIR|g" "$SERVICE_SRC" \
    | sed "s|User=homeassistant|User=$SERVICE_USER|g" \
    | sed "s|Group=homeassistant|Group=$SERVICE_USER|g" \
    > "$SERVICE_DEST"

chmod 644 "$SERVICE_DEST"

# ── 5. Enable and start the service ──────────────────────────────────────────
echo "==> Reloading systemd"
systemctl daemon-reload

echo "==> Enabling homeassistant-server to start on boot"
systemctl enable homeassistant-server

echo "==> Starting homeassistant-server"
systemctl restart homeassistant-server

echo ""
echo "Done. Check status with:"
echo "  systemctl status homeassistant-server"
echo "  journalctl -u homeassistant-server -f"

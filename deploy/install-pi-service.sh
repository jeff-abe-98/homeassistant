#!/usr/bin/env bash
# Install and enable the homeassistant-pi systemd service on a Raspberry Pi 5.
#
# Prerequisites (run BEFORE this script):
#   - HailoRT driver installed for AI HAT+ 2:
#       sudo apt update && sudo apt install -y hailo-h10-all
#   - PCIe Gen 3 enabled in /boot/firmware/config.txt:
#       dtparam=pciex1_gen=3
#   - Reboot after driver install and config.txt change:
#       sudo reboot
#   - Verify AI HAT+ 2 is detected:
#       hailortcli fw-control identify
#
# Usage:
#   sudo ./install-pi-service.sh [INSTALL_DIR] [SERVICE_USER]
#
# Defaults:
#   INSTALL_DIR  = /opt/homeassistant
#   SERVICE_USER = homeassistant
#
# What this script does:
#   1. Creates the service user (if it doesn't exist) and adds it to the audio group
#   2. Copies the project to INSTALL_DIR
#   3. Creates a Python venv and installs Pi requirements
#   4. Writes the main service file + scheduler service + scheduler timer to /etc/systemd/system/
#   5. Reloads systemd, enables and starts the service and scheduler timer

set -euo pipefail

INSTALL_DIR="${1:-/opt/homeassistant}"
SERVICE_USER="${2:-homeassistant}"
SERVICE_FILE="homeassistant-pi.service"
SCHEDULER_SERVICE="homeassistant-scheduler.service"
SCHEDULER_TIMER="homeassistant-scheduler.timer"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "==> Install dir  : $INSTALL_DIR"
echo "==> Service user : $SERVICE_USER"

# ── 1. Create service user and add to audio group ─────────────────────────────
if ! id "$SERVICE_USER" &>/dev/null; then
    echo "==> Creating user $SERVICE_USER"
    useradd --system --no-create-home --shell /usr/sbin/nologin "$SERVICE_USER"
fi

# Audio group membership is required for PyAudio microphone + sounddevice output.
if getent group audio &>/dev/null; then
    echo "==> Adding $SERVICE_USER to the audio group"
    usermod -aG audio "$SERVICE_USER"
fi

# ── 2. Copy project files ─────────────────────────────────────────────────────
echo "==> Copying project to $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
rsync -a --exclude='.git' --exclude='venv' --exclude='.venv' --exclude='__pycache__' \
    "$PROJECT_ROOT/" "$INSTALL_DIR/"
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"

# ── 3. Create venv and install dependencies ───────────────────────────────────
VENV="$INSTALL_DIR/venv"
if [ ! -d "$VENV" ]; then
    echo "==> Creating venv at $VENV"
    python3 -m venv --system-site-packages "$VENV"
fi
echo "==> Installing Pi requirements"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$INSTALL_DIR/requirements-pi.txt"
chown -R "$SERVICE_USER:$SERVICE_USER" "$VENV"

# ── 4. Write service and timer files ─────────────────────────────────────────
write_unit() {
    local src="$SCRIPT_DIR/$1"
    local dest="/etc/systemd/system/$1"
    echo "==> Writing $dest"
    sed "s|/opt/homeassistant|$INSTALL_DIR|g" "$src" \
        | sed "s|User=homeassistant|User=$SERVICE_USER|g" \
        | sed "s|Group=homeassistant|Group=$SERVICE_USER|g" \
        > "$dest"
    chmod 644 "$dest"
}

write_unit "$SERVICE_FILE"
write_unit "$SCHEDULER_SERVICE"
write_unit "$SCHEDULER_TIMER"

# ── 5. Enable and start the service and scheduler timer ──────────────────────
echo "==> Reloading systemd"
systemctl daemon-reload

echo "==> Enabling homeassistant-pi to start on boot"
systemctl enable homeassistant-pi

echo "==> Enabling scheduler timer"
systemctl enable homeassistant-scheduler.timer
systemctl start homeassistant-scheduler.timer

echo "==> Starting homeassistant-pi"
systemctl restart homeassistant-pi

echo ""
echo "Done. Check status with:"
echo "  systemctl status homeassistant-pi"
echo "  systemctl status homeassistant-scheduler.timer"
echo "  journalctl -u homeassistant-pi -f"

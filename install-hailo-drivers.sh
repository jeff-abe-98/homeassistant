#!/bin/bash
set -e

echo "=== Hailo AI HAT+ 2 Driver Installation ==="

# Install runtime + PCIe driver
echo "[1/3] Installing hailo-h10-all..."
apt update
apt install -y hailo-h10-all

# Enable PCIe Gen 3 (if not already set)
CONFIG=/boot/firmware/config.txt
if grep -q 'pciex1_gen=3' "$CONFIG"; then
    echo "[2/3] PCIe Gen 3 already enabled — skipping"
else
    echo "[2/3] Enabling PCIe Gen 3 in $CONFIG..."
    echo 'dtparam=pciex1_gen=3' >> "$CONFIG"
fi

echo "[3/3] Done. Rebooting in 5 seconds (Ctrl-C to cancel)..."
sleep 5
reboot

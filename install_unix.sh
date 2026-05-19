#!/usr/bin/env bash
# OpenClaw USB Killswitch — Linux & macOS Installer
# Run with: sudo bash install_unix.sh

set -e

INSTALL_DIR="/opt/openclaw-killswitch"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEM="$(uname -s)"

echo "========================================"
echo " OpenClaw USB Killswitch — Unix Setup"
echo " Platform: $SYSTEM"
echo "========================================"
echo

# Check root
if [[ $EUID -ne 0 ]]; then
   echo "ERROR: Please run as root: sudo bash install_unix.sh"
   exit 1
fi

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 is required. Install it first."
    exit 1
fi

echo "[1/4] Installing to $INSTALL_DIR ..."
mkdir -p "$INSTALL_DIR"
cp "$SCRIPT_DIR/killswitch.py" "$INSTALL_DIR/killswitch.py"
chmod 700 "$INSTALL_DIR/killswitch.py"
echo "      Done."

# ── Linux: systemd service ──────────────────────
if [[ "$SYSTEM" == "Linux" ]]; then
    echo "[2/4] Installing systemd service..."
    cat > /etc/systemd/system/openclaw-killswitch.service << EOF
[Unit]
Description=OpenClaw USB Killswitch
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 $INSTALL_DIR/killswitch.py
Restart=always
RestartSec=3
User=root

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable openclaw-killswitch.service
    systemctl start  openclaw-killswitch.service
    echo "      Systemd service enabled and started."
    echo "      Status: $(systemctl is-active openclaw-killswitch.service)"

    # udev rule to instantly detect USB removal
    echo "[3/4] Installing udev rule for instant USB detection..."
    cat > /etc/udev/rules.d/99-openclaw-killswitch.rules << 'EOF'
# Trigger killswitch script on USB removal
ACTION=="remove", SUBSYSTEM=="block", ENV{ID_BUS}=="usb", \
    RUN+="/usr/bin/python3 /opt/openclaw-killswitch/killswitch.py --usb-event remove"
EOF
    udevadm control --reload-rules
    echo "      udev rule installed."

# ── macOS: LaunchDaemon ─────────────────────────
elif [[ "$SYSTEM" == "Darwin" ]]; then
    echo "[2/4] Installing LaunchDaemon (runs at boot)..."
    PLIST="/Library/LaunchDaemons/com.openclaw.killswitch.plist"
    cat > "$PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>             <string>com.openclaw.killswitch</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$INSTALL_DIR/killswitch.py</string>
    </array>
    <key>RunAtLoad</key>         <true/>
    <key>KeepAlive</key>         <true/>
    <key>StandardOutPath</key>   <string>/var/log/openclaw_killswitch.log</string>
    <key>StandardErrorPath</key> <string>/var/log/openclaw_killswitch.log</string>
</dict>
</plist>
EOF
    launchctl load -w "$PLIST"
    echo "      LaunchDaemon loaded."

    echo "[3/4] Installing disk-eject trigger via launchd..."
    # macOS sends DiskArbitration events; the Python script polls via diskutil
    echo "      (macOS: polling mode active — eject event caught within poll interval)"
fi

echo "[4/4] Creating manual fire command..."
cat > /usr/local/bin/openclaw-killswitch-fire << EOF
#!/bin/bash
echo "Manually firing OpenClaw killswitch..."
python3 $INSTALL_DIR/killswitch.py --fire-now
EOF
chmod +x /usr/local/bin/openclaw-killswitch-fire

echo
echo "✅ Killswitch installed and running!"
echo "   Log file: ~/.openclaw_killswitch.log"
echo "   Manual fire: openclaw-killswitch-fire"
echo
if [[ "$SYSTEM" == "Linux" ]]; then
    echo "   Service status: systemctl status openclaw-killswitch"
fi

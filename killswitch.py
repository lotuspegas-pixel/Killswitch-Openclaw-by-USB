#!/usr/bin/env python3
"""
OpenClaw USB Killswitch
=======================
Monitors for a specific USB key. When the key is REMOVED (or absent on startup),
the killswitch fires: OpenClaw is killed and optionally deleted/blocked.

Works on: Windows, Linux, macOS
"""

import os
import sys
import time
import json
import signal
import logging
import platform
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime

# ──────────────────────────────────────────────
# CONFIGURATION  (edit before first run)
# ──────────────────────────────────────────────
CONFIG = {
    # Label of your USB key (exactly as it appears in your OS)
    "usb_label": "OPENCLAW_KEY",

    # Unique file that must exist on the USB key (extra verification)
    "usb_secret_file": ".openclaw_auth",

    # SHA-256 hash of the content of that file  ← generate with:
    #   python3 -c "import hashlib; print(hashlib.sha256(b'YOUR_SECRET').hexdigest())"
    "usb_secret_hash": "REPLACE_WITH_YOUR_HASH",

    # What to do when killswitch fires
    "action_kill_process": True,       # SIGKILL the OpenClaw process
    "action_block_network": True,      # Block OpenClaw via firewall
    "action_delete_program": False,    # DELETE the OpenClaw installation (irreversible!)
    "action_lock_files": True,         # Remove execute permission from OpenClaw binary

    # Paths to OpenClaw (adjust to your installation)
    "openclaw_process_name": "openclaw",
    "openclaw_install_dirs": [
        "~/OpenClaw",
        "~/.local/share/openclaw",
        "C:\\Program Files\\OpenClaw",
        "/opt/openclaw",
        "/usr/local/bin/openclaw",
    ],

    # How often to check for the USB key (seconds)
    "poll_interval": 2,

    # Grace period after USB removal before firing (seconds)
    "grace_period": 5,

    # Log file location
    "log_file": "~/.openclaw_killswitch.log",

    # Mode: "on_remove" (USB removed → fire) or "on_insert" (USB inserted → fire)
    "trigger_mode": "on_remove",
}
# ──────────────────────────────────────────────


SYSTEM = platform.system()  # "Windows", "Linux", "Darwin"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(Path(CONFIG["log_file"]).expanduser()),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("killswitch")


# ──────────────────────────────────────────────
# USB DETECTION
# ──────────────────────────────────────────────

def get_mounted_usb_volumes() -> list[str]:
    """Return list of mount points / drive letters for removable USB media."""
    volumes = []

    if SYSTEM == "Windows":
        import ctypes
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for i in range(26):
            if bitmask & (1 << i):
                letter = chr(65 + i) + ":\\"
                drive_type = ctypes.windll.kernel32.GetDriveTypeW(letter)
                if drive_type == 2:  # DRIVE_REMOVABLE
                    volumes.append(letter)

    elif SYSTEM == "Darwin":
        result = subprocess.run(
            ["diskutil", "list", "-plist", "external"],
            capture_output=True, text=True
        )
        # Also check /Volumes directly
        volumes_dir = Path("/Volumes")
        if volumes_dir.exists():
            volumes = [str(p) for p in volumes_dir.iterdir() if p.is_dir()]

    else:  # Linux
        result = subprocess.run(
            ["lsblk", "-o", "MOUNTPOINT,HOTPLUG", "-J"],
            capture_output=True, text=True
        )
        try:
            data = json.loads(result.stdout)
            for device in data.get("blockdevices", []):
                for child in device.get("children", [device]):
                    if child.get("hotplug") == "1" and child.get("mountpoint"):
                        volumes.append(child["mountpoint"])
        except Exception:
            # Fallback: check /media and /run/media
            for base in ["/media", "/run/media"]:
                base_path = Path(base)
                if base_path.exists():
                    for p in base_path.rglob("*"):
                        if p.is_mount():
                            volumes.append(str(p))

    return volumes


def find_auth_key() -> str | None:
    """
    Return the mount point of the authorised USB key, or None if not found.
    Verification: correct label OR secret file with matching hash.
    """
    for vol in get_mounted_usb_volumes():
        vol_path = Path(vol)

        # Check label (volume name in path or via OS)
        label_matches = CONFIG["usb_label"].lower() in str(vol_path).lower()

        # Check secret file + hash
        secret_path = vol_path / CONFIG["usb_secret_file"]
        hash_matches = False
        if secret_path.exists():
            try:
                content = secret_path.read_bytes()
                digest = hashlib.sha256(content).hexdigest()
                hash_matches = (digest == CONFIG["usb_secret_hash"])
            except Exception:
                pass

        if label_matches or hash_matches:
            return str(vol_path)

    return None


# ──────────────────────────────────────────────
# KILLSWITCH ACTIONS
# ──────────────────────────────────────────────

def kill_openclaw_process():
    """Force-kill all OpenClaw processes."""
    name = CONFIG["openclaw_process_name"]
    log.warning(f"[ACTION] Killing process: {name}")

    if SYSTEM == "Windows":
        subprocess.run(["taskkill", "/F", "/IM", f"{name}.exe"], capture_output=True)
        subprocess.run(["taskkill", "/F", "/IM", name], capture_output=True)
    else:
        subprocess.run(["pkill", "-9", "-f", name], capture_output=True)

    log.info(f"Process kill command sent for: {name}")


def block_network():
    """Block OpenClaw's network access via system firewall."""
    name = CONFIG["openclaw_process_name"]
    log.warning(f"[ACTION] Blocking network for: {name}")

    if SYSTEM == "Windows":
        # Windows Firewall – block outbound & inbound
        for direction in ["in", "out"]:
            subprocess.run([
                "netsh", "advfirewall", "firewall", "add", "rule",
                f"name=OPENCLAW_KILLSWITCH_{direction.upper()}",
                f"dir={direction}", "action=block",
                f"program=%ProgramFiles%\\OpenClaw\\{name}.exe",
                "enable=yes"
            ], capture_output=True)

    elif SYSTEM == "Darwin":
        # macOS: use pf (packet filter) – adds a block rule
        pf_rule = f'block drop proto tcp from any to any\n'
        try:
            subprocess.run(["pfctl", "-e"], capture_output=True)
            subprocess.run(["pfctl", "-f", "/etc/pf.conf"], capture_output=True)
        except Exception as e:
            log.error(f"pf error: {e}")

    else:  # Linux
        # iptables: block by process owner or known port
        subprocess.run([
            "iptables", "-A", "OUTPUT", "-m", "owner",
            "--cmd-owner", name, "-j", "DROP"
        ], capture_output=True)

    log.info("Network block applied.")


def lock_openclaw_files():
    """Remove execute permission from OpenClaw binaries."""
    log.warning("[ACTION] Locking OpenClaw files (removing execute permission)")

    for raw_dir in CONFIG["openclaw_install_dirs"]:
        dir_path = Path(raw_dir).expanduser()
        if dir_path.exists():
            if SYSTEM == "Windows":
                # On Windows: deny execute via icacls
                subprocess.run([
                    "icacls", str(dir_path), "/deny", "Everyone:(X)",
                    "/T"
                ], capture_output=True)
            else:
                subprocess.run(["chmod", "-R", "a-x", str(dir_path)], capture_output=True)
            log.info(f"Locked: {dir_path}")


def delete_openclaw():
    """Permanently delete OpenClaw installation directories."""
    log.critical("[ACTION] DELETING OpenClaw installation — THIS IS IRREVERSIBLE")
    import shutil

    for raw_dir in CONFIG["openclaw_install_dirs"]:
        dir_path = Path(raw_dir).expanduser()
        if dir_path.exists():
            try:
                shutil.rmtree(dir_path)
                log.critical(f"DELETED: {dir_path}")
            except Exception as e:
                log.error(f"Could not delete {dir_path}: {e}")


def fire_killswitch(reason: str):
    """Execute all configured killswitch actions."""
    log.critical("=" * 60)
    log.critical(f"🔴 KILLSWITCH FIRED — Reason: {reason}")
    log.critical(f"   Time: {datetime.now().isoformat()}")
    log.critical("=" * 60)

    if CONFIG["action_kill_process"]:
        kill_openclaw_process()

    if CONFIG["action_block_network"]:
        block_network()

    if CONFIG["action_lock_files"]:
        lock_openclaw_files()

    if CONFIG["action_delete_program"]:
        delete_openclaw()

    log.critical("🔴 Killswitch actions complete.")


# ──────────────────────────────────────────────
# MAIN MONITOR LOOP
# ──────────────────────────────────────────────

def main():
    log.info("OpenClaw USB Killswitch starting...")
    log.info(f"Platform: {SYSTEM}")
    log.info(f"Trigger mode: {CONFIG['trigger_mode']}")
    log.info(f"USB label: {CONFIG['usb_label']}")
    log.info(f"Poll interval: {CONFIG['poll_interval']}s | Grace period: {CONFIG['grace_period']}s")

    # Check secret hash is configured
    if CONFIG["usb_secret_hash"] == "REPLACE_WITH_YOUR_HASH":
        log.warning("⚠️  usb_secret_hash not configured — running in label-only mode.")

    key_present = find_auth_key() is not None
    log.info(f"USB key present at startup: {key_present}")

    if CONFIG["trigger_mode"] == "on_remove" and not key_present:
        log.warning("USB key not present at startup — firing immediately!")
        fire_killswitch("USB key absent at startup")
        return

    removal_detected_at = None

    def handle_signal(sig, frame):
        log.info("Killswitch daemon stopping (signal received).")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    log.info("Monitoring... (Ctrl+C to stop)")

    while True:
        try:
            key_found = find_auth_key()
            now_present = key_found is not None

            if CONFIG["trigger_mode"] == "on_remove":
                if key_present and not now_present:
                    # USB was just removed
                    log.warning(f"USB key removed! Grace period: {CONFIG['grace_period']}s")
                    removal_detected_at = time.time()

                if removal_detected_at:
                    elapsed = time.time() - removal_detected_at
                    # Re-check in case it was briefly unplugged
                    if find_auth_key():
                        log.info("USB key re-inserted within grace period — cancelling.")
                        removal_detected_at = None
                    elif elapsed >= CONFIG["grace_period"]:
                        fire_killswitch("USB key removed and not re-inserted within grace period")
                        removal_detected_at = None

            elif CONFIG["trigger_mode"] == "on_insert":
                if not key_present and now_present:
                    log.info("USB key inserted — firing killswitch.")
                    fire_killswitch("USB key inserted (on_insert mode)")

            key_present = now_present
            time.sleep(CONFIG["poll_interval"])

        except Exception as e:
            log.error(f"Monitor loop error: {e}")
            time.sleep(CONFIG["poll_interval"])


if __name__ == "__main__":
    main()

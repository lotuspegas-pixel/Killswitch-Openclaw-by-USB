#!/usr/bin/env python3
"""
OpenClaw Killswitch — USB Key Setup
====================================
Run this script ONCE to:
  1. Generate a cryptographically random secret
  2. Write it to your USB key
  3. Print the hash to paste into killswitch.py CONFIG

Usage:
    python3 setup_usb_key.py /path/to/usb/mount
    # Windows example: python setup_usb_key.py E:\\
    # Linux example:   python3 setup_usb_key.py /media/yourname/OPENCLAW_KEY
    # macOS example:   python3 setup_usb_key.py /Volumes/OPENCLAW_KEY
"""

import sys
import os
import hashlib
import secrets
from pathlib import Path

AUTH_FILENAME = ".openclaw_auth"

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 setup_usb_key.py <USB_MOUNT_PATH>")
        sys.exit(1)

    usb_path = Path(sys.argv[1])
    if not usb_path.exists():
        print(f"ERROR: Path does not exist: {usb_path}")
        sys.exit(1)

    # Generate a 64-byte random secret
    secret = secrets.token_bytes(64)
    secret_hex = secret.hex()
    digest = hashlib.sha256(secret).hexdigest()

    auth_file = usb_path / AUTH_FILENAME

    # Write to USB key
    auth_file.write_bytes(secret)
    print(f"\n✅ Secret written to: {auth_file}")
    print(f"\n{'='*60}")
    print("  COPY THIS INTO killswitch.py → CONFIG['usb_secret_hash']:")
    print(f"\n  \"{digest}\"")
    print(f"{'='*60}")
    print("\n⚠️  Keep your USB key safe — losing it means losing killswitch control.")
    print("    Make a second backup USB key by running this script again and")
    print("    adding the second hash to your config.\n")

if __name__ == "__main__":
    main()

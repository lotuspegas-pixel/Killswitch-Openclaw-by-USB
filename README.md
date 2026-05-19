# OpenClaw USB Killswitch

> **A physical dead man's switch for OpenClaw.**  
> Pull the USB key out — OpenClaw stops. Instantly. No questions asked.

Born out of a real incident: a bug in OpenClaw caused it to send unsolicited WhatsApp messages to 80 people from my contact list without my knowledge or consent. After spending an afternoon apologising to friends, family and clients one by one, I built this — so no one else has to go through the same experience.

---

## Why this exists

AI automation tools are powerful. That power comes with risk. No software is bug-free, and when an AI tool connected to your accounts and contacts misbehaves, you need to be able to stop it **immediately** — not after clicking through menus, not after a reboot. Right now.

This killswitch gives you that control. One physical action. Total shutdown.

---

## Files

| File | Purpose |
|---|---|
| `killswitch.py` | Main daemon — monitors your USB key and fires the killswitch |
| `setup_usb_key.py` | One-time setup: writes a secret authentication token to your USB key |
| `install_windows.bat` | Installs the daemon as a Windows scheduled task (run as Administrator) |
| `install_unix.sh` | Installs as a systemd service (Linux) or LaunchDaemon (macOS) |

---

## How it works

```
USB key present  →  OpenClaw runs normally           ✅
USB key removed  →  5-second grace period  →  KILLSWITCH FIRES 🔴
                         ├── OpenClaw process force-killed (SIGKILL)
                         ├── Network access blocked via system firewall
                         ├── Execute permissions stripped from binaries
                         └── (optional) Full installation permanently deleted
```

The daemon runs silently in the background at all times. If the USB key is absent when your computer starts up, the killswitch fires immediately — OpenClaw never gets a chance to run.

### Trigger modes

| Mode | Behaviour |
|---|---|
| `"on_remove"` *(default)* | Removing the USB key fires the killswitch |
| `"on_insert"` | Inserting the USB key fires the killswitch (for incident response scenarios) |

---

## Installation

### Step 1 — Configure `killswitch.py`

Open `killswitch.py` and edit the `CONFIG` block at the top:

```python
"usb_label": "OPENCLAW_KEY",          # Volume label of your USB key (case-sensitive)
"openclaw_process_name": "openclaw",  # Exact process name as it appears in Task Manager / ps
"openclaw_install_dirs": [            # All directories where OpenClaw is installed
    "~/OpenClaw",
    "C:\\Program Files\\OpenClaw",
    "/opt/openclaw",
],
"action_kill_process": True,          # Force-kill the process
"action_block_network": True,         # Block network access via firewall
"action_delete_program": False,       # ⚠️  True = PERMANENTLY delete OpenClaw (irreversible)
"action_lock_files": True,            # Remove execute permissions from binaries
"grace_period": 5,                    # Seconds to wait before firing (allows accidental re-insert)
```

### Step 2 — Set up your USB key

Insert your USB key, then run:

```bash
# Replace the path with your actual mount point:
#   Windows:  python  setup_usb_key.py E:\
#   Linux:    python3 setup_usb_key.py /media/yourname/OPENCLAW_KEY
#   macOS:    python3 setup_usb_key.py /Volumes/OPENCLAW_KEY

python3 setup_usb_key.py /Volumes/OPENCLAW_KEY
```

The script generates a cryptographically random 64-byte secret and writes it to your USB key. It then prints a SHA-256 hash — copy it and paste it into `killswitch.py`:

```python
"usb_secret_hash": "paste-your-hash-here",
```

> **Important:** Make a second backup USB key right away. If you lose your only key, you lose killswitch control.

### Step 3 — Install the daemon

**Windows** — run as Administrator:
```
install_windows.bat
```

**Linux:**
```bash
sudo bash install_unix.sh
```

**macOS:**
```bash
sudo bash install_unix.sh
```

The daemon starts immediately and is configured to run automatically at every login/boot.

---

## Manually firing the killswitch

You don't need to pull the USB key — you can trigger it manually at any time:

- **Windows:** double-click `FIRE_KILLSWITCH.bat` on your Desktop
- **Linux / macOS:** run `openclaw-killswitch-fire` in any terminal

---

## Viewing logs

```bash
tail -f ~/.openclaw_killswitch.log
```

Every action the killswitch takes is logged with a timestamp, including the reason it fired.

---

## Security

- Your USB key holds a **64-byte cryptographically random secret** — not guessable
- The daemon verifies both the **volume label** and the **SHA-256 hash** of the secret file
- Both checks must pass — label alone is not enough
- Without the correct USB key the killswitch cannot be bypassed
- Always keep a **second backup USB key** stored safely offline

---

## Platform support

| Platform | Process kill | Network block | File lock | Auto-start |
|---|---|---|---|---|
| Windows 10/11 | ✅ taskkill | ✅ Windows Firewall | ✅ icacls | ✅ Scheduled Task |
| Linux (systemd) | ✅ pkill | ✅ iptables | ✅ chmod | ✅ systemd service |
| macOS 12+ | ✅ pkill | ✅ pf | ✅ chmod | ✅ LaunchDaemon |

---

## Troubleshooting

| Problem | Solution |
|---|---|
| USB detected but killswitch fires anyway | Check `usb_label` — it is case-sensitive |
| OpenClaw process not being killed | Verify `openclaw_process_name` using Task Manager (Windows) or `ps aux \| grep openclaw` (Linux/macOS) |
| Daemon not starting | Check the log: `~/.openclaw_killswitch.log` |
| `lsblk` not found (Linux) | Run `sudo apt install util-linux` |
| Permission denied on install | Make sure you run the installer as Administrator / with `sudo` |

---

## Disclaimer

This tool is provided as-is, for personal safety and control purposes. The author is not responsible for data loss resulting from enabling `action_delete_program`. That option is irreversible — use with care.

This project is not affiliated with or endorsed by the OpenClaw development team.

---

## License

MIT — free to use, modify and distribute.

# OpenClaw USB Killswitch

Een fysieke USB-sleutel die OpenClaw onmiddellijk uitschakelt of verwijdert
wanneer de sleutel uit de computer wordt getrokken (of niet aanwezig is bij opstarten).

---

## Bestanden

| Bestand | Doel |
|---|---|
| `killswitch.py` | Hoofd-daemon — werkt op Windows, Linux en macOS |
| `setup_usb_key.py` | Schrijft de geheime sleutel naar je USB-stick |
| `install_windows.bat` | Installeert als Windows geplande taak (als Administrator) |
| `install_unix.sh` | Installeert als systemd/LaunchDaemon (Linux/macOS) |

---

## Stap-voor-stap installatie

### 1. Configureer `killswitch.py`

Open `killswitch.py` en pas het `CONFIG` blok aan:

```python
"usb_label": "OPENCLAW_KEY",          # Label van jouw USB-stick
"openclaw_process_name": "openclaw",  # Exacte procesnaam
"openclaw_install_dirs": [            # Paden naar OpenClaw
    "~/OpenClaw",
    ...
],
"action_kill_process": True,
"action_block_network": True,
"action_delete_program": False,       # True = DEFINITIEF verwijderen
"action_lock_files": True,
```

### 2. Bereid je USB-sleutel voor

```bash
# Steek de USB-stick in, weet het mountpunt:
#   Windows: E:\
#   Linux:   /media/jij/OPENCLAW_KEY
#   macOS:   /Volumes/OPENCLAW_KEY

python3 setup_usb_key.py /Volumes/OPENCLAW_KEY
```

Kopieer de hash die je ziet en plak die in `killswitch.py`:
```python
"usb_secret_hash": "abc123...",
```

### 3. Installeer de daemon

**Windows** (als Administrator):
```
install_windows.bat
```

**Linux**:
```bash
sudo bash install_unix.sh
```

**macOS**:
```bash
sudo bash install_unix.sh
```

---

## Hoe werkt het?

```
USB aanwezig → OpenClaw mag draaien ✅
USB verwijderd → 5 seconden grace period → KILLSWITCH 🔴
  ├── OpenClaw process geforceerd gestopt (SIGKILL)
  ├── Netwerk geblokkeerd via firewall
  ├── Uitvoerrechten verwijderd van binaries
  └── (optioneel) Volledige installatie verwijderd
```

### Trigger modes
- `"on_remove"` *(standaard)*: USB eruit = killswitch
- `"on_insert"`: USB erin steken = killswitch (voor incident response)

---

## Handmatig de killswitch activeren

**Windows**: dubbelklik op `FIRE_KILLSWITCH.bat` op je bureaublad  
**Linux/macOS**: `openclaw-killswitch-fire` in terminal

---

## Logs bekijken

```bash
tail -f ~/.openclaw_killswitch.log
```

---

## Veiligheid

- De USB-sleutel bevat een 64-byte willekeurig geheim
- De killswitch verifieert zowel het volume-label **als** de SHA-256 hash
- Zonder de juiste USB-stick kan de killswitch niet worden omzeild
- Maak altijd een **tweede reserve USB-sleutel** aan

---

## Troubleshooting

| Probleem | Oplossing |
|---|---|
| USB herkend maar killswitch vliegt af | Controleer `usb_label` (hoofdlettergevoelig) |
| OpenClaw wordt niet gevonden | Controleer `openclaw_process_name` met `ps aux` of Task Manager |
| Daemon start niet | Controleer log: `~/.openclaw_killswitch.log` |
| lsblk niet gevonden (Linux) | `sudo apt install util-linux` |

# AEGIS Radar — RTAF Tactical Air Defense Simulator

A real-time air defense Command-and-Control simulator built with Python and Pygame. You play as the tactical commander of the Royal Thai Air Force (RTAF) Air Defense network, managing radar contacts, authorizing intercepts, and keeping the base alive against escalating threat waves.

---

## Features

### Radar Display
- Rotating AESA sweep line with a fading phosphor trail
- Weapon Engagement Zone (WEZ) range rings: THAAD (400 km), SAM (200/80 km), CIWS (20 km)
- Real-world Thailand map geometry rendered as vector terrain
- RTAF airbases: Wing 1, 4, 7, 21, 23 displayed on map
- Contacts labeled with ID code, speed, and flight level
- 60 FPS smooth interpolation between 1-second simulation ticks

### Contact Types
| Type | Description |
|---|---|
| Aircraft | Mixed civilian/hostile; hostile includes fighters and EW jets |
| Airliner | Commercial traffic — do NOT shoot down |
| Drone / UAV | Slow, low RCS — hard to detect early |
| Helicopter | Low-altitude CAS threats |
| TBM | Tactical ballistic missiles — high speed, short warning |
| ICBM | Near-instant kill on base, only THAAD can reach it |
| Ghost Track | Radar clutter that auto-clears on identification |
| EW Ghost | Fake blips injected by enemy jamming aircraft |

### AWACS & CAP
- Two AWACS aircraft rotate from Wing 7 on patrol orbits over the Gulf of Thailand
- When primary AWACS fuel drops below 20%, Wing 7 launches a relief aircraft before RTB
- Two CAP fighters maintain constant standing patrols — one over the north (Wing 4), one over the south (Wing 7)
- Low-fuel CAP fighters RTB automatically; replacements launch on a staggered schedule

### Weapons
- **THAAD** — Long-range ballistic missile defense, limited rounds
- **SAM** — General-purpose air defense; subject to chaff evasion by fast jets
- **CIWS** — Auto-firing last-ditch close-in weapon; degrades against Mach 2+ targets
- **Fighter** — Scrambled from the nearest airbase; effective against all aerial threats

### Electronic Warfare
When a Heavy EW aircraft (EA-18G Growler) is active:
- The radar sweep line speed becomes erratic and unpredictable
- All radar contacts jitter on screen, degrading spatial accuracy
- Floods the scope with 2–6 EW Ghost Tracks per tick
- Jamming factor reduces radar detection range to 30% inside the EW strobe sector

### Engagement Logic
- All intercepts start from the geographically nearest airbase
- Hit probabilities include kinematic penalties: fast targets are harder to hit
- Fighters are 95% effective against slow targets (drones/helicopters)
- Shooting down a civilian airliner is an instant game-over

---

## Controls

| Key | Action |
|---|---|
| `Click` | Select / lock a contact |
| `1` | Fire THAAD at selected contact |
| `2` | Fire SAM at selected contact |
| `3` | Fire CIWS at selected contact |
| `4` | Scramble fighter from nearest airbase |
| `Backspace` | Abort active engagement on selected contact |
| `5` | Manual spawn: ICBM |
| `6` | Manual spawn: Fighter |
| `7` | Manual spawn: Drone |
| `8` | Manual spawn: Civilian airliner |
| `9` | Manual spawn: Heavy EW aircraft |
| `0` | Manual spawn: AWACS |
| `W` | Manual spawn: Hostile wave (5 fighters) |
| `WASD / Arrows` | Pan camera |
| `Scroll wheel` | Zoom |
| `F11` | Toggle fullscreen |
| `R` | Restart (after base destroyed) |
| `ESC` | Quit |

---

## Project Structure

```
airdefense_oop_final_project/
├── main.py            # Entry point
├── radar_ui.py        # Pygame rendering, input handling, HUD
├── command_center.py  # Game loop, wave spawning, engagement resolution
├── targets.py         # All air contact classes (AirContact, Aircraft, AWACS, etc.)
├── personnel.py       # RadarOperator, WeaponOfficer, ThreatQueue, Engagement
├── config.py          # All numeric constants and airbase data
├── requirements.txt   # Python dependencies
└── *.json             # Country border geometry for map rendering
```

### Class Overview

**`targets.py`**
- `AirContact` (ABC) — base class for all radar contacts
- `Aircraft`, `Helicopter`, `Drone`, `TacticalBM`, `ICBM`, `Airliner` — threat types
- `AWACS` — friendly, orbits over Gulf of Thailand, transitions between TRANSIT → ON_STATION → RTB
- `CAPFighter` — friendly combat air patrol, same state machine as AWACS
- `GhostTrack` — clutter that fades when identified
- `EWGhostTrack` — fake blips spawned by active EW jamming

**`personnel.py`**
- `RadarOperator` — auto-identifies unidentified contacts by ETA priority
- `WeaponOfficer` — auto-authorizes fire on highest threat score contacts
- `ThreatQueue` — priority queue sorted by threat score
- `Engagement` — tracks a single weapon-target pair through to impact
- `get_closest_airbase()` — returns nearest RTAF wing for fighter launches

**`command_center.py`**
- Tick loop: `detect_airspace()` → `process_reloads()` → `process_personnel()` → `process_engagements()` → `process_auto_ciws()` → `update_world()`
- Manages AWACS/CAP rotation, fighter RTB queue, wave cooldowns, damage resolution

---

## Installation & Running

```bash
pip install -r requirements.txt
python main.py
```

Or run the compiled executable directly:
```
AEGIS_Radar.exe
```

To recompile the executable (requires PyInstaller):
```bash
pip install pyinstaller
python -m PyInstaller --onefile --noconsole --name "AEGIS_Radar" \
  --add-data "tha.json;." --add-data "mmr.json;." --add-data "lao.json;." \
  --add-data "khm.json;." --add-data "mys.json;." --add-data "vnm.json;." \
  --add-data "chn.json;." --add-data "idn.json;." --add-data "phl.json;." \
  --add-data "twn.json;." main.py
```

---

## Dependencies

- Python 3.10+
- pygame >= 2.0.0

---

## Academic Context

This project was developed as an Object-Oriented Programming (OOP) final project demonstrating:
- Abstract base classes and inheritance hierarchies
- Polymorphism through overridden `move()` and `identify_target()` methods
- Encapsulation of state machines (TRANSIT / ON_STATION / RTB) within unit classes
- Separation of concerns: rendering (radar_ui), simulation logic (command_center), domain models (targets, personnel)

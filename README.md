# AEGIS Radar — RTAF Tactical Air Defense Simulator

Real-time air defense simulator built with Python + Pygame. You run the RTAF air defense network — manage radar contacts, authorize intercepts, and keep your base alive against escalating threat waves.

![Python](https://img.shields.io/badge/python-3.10+-blue) ![Pygame](https://img.shields.io/badge/pygame-2.0+-green)

---

## What it does

You sit at a radar console watching contacts appear on a rotating AESA sweep. Some are civilian airliners, some are hostile fighters, some are ballistic missiles. Your job is to identify them, prioritize threats, and fire the right weapon before they reach the base.

The sim handles AWACS rotation, combat air patrol scheduling, ammo logistics, and automatic CIWS engagement. You handle the hard calls — which target gets the THAAD round, when to scramble fighters, and whether that unidentified blip is a Boeing 777 or a Su-35.

---

## Features

- **Rotating AESA radar** with phosphor trail, 60fps interpolation, zoom/pan
- **Real Thailand map** rendered from GeoJSON with terrain contours and airbase markers
- **9 contact types**: fighters, drones, helicopters, TBMs, ICBMs, airliners, EW jammers, ghosts, and CAP patrols
- **AWACS/CAP rotation**: auto-launched from Wing 7 and Wing 4, fuel management, relief swaps
- **4 weapon systems**: THAAD, SAM, CIWS (auto-fire), and fighter scramble from nearest airbase
- **Electronic warfare**: heavy EW jammer floods your screen with green particle noise, ghost tracks, scan line glitches, and erratic sweep rotation — your whole display goes haywire
- **Engagement math**: hit probability accounts for target speed, chaff deployment, weapon type, and closure rate
- **Shoot down an airliner and it's game over** (court-martial)

---

## Controls

| Key | What it does |
|---|---|
| `Click` | Select a contact |
| `1` / `2` / `3` / `4` | Fire THAAD / SAM / CIWS / Scramble fighter |
| `Backspace` | Abort engagement |
| `5-9, 0, W` | Spawn: ICBM / Fighter / Drone / Airliner / EW / AWACS / Wave |
| `WASD` / `Arrows` | Pan camera |
| `Scroll` | Zoom |
| `F11` | Fullscreen |
| `R` | Restart (after death) |
| `ESC` | Quit |

---

## Project layout

```
├── main.py             # entry point
├── radar_ui.py         # rendering, input, HUD
├── command_center.py   # game loop, waves, engagements
├── targets.py          # all contact classes
├── personnel.py        # radar operator, weapon officer, threat queue
├── config.py           # tuning constants, airbase coords
├── requirements.txt
└── *.json              # country border geometry
```

### How the classes fit together

**targets.py** — `AirContact` is the abstract base. Everything inherits from it: `Aircraft`, `Drone`, `Helicopter`, `TacticalBM`, `ICBM`, `Airliner`, `AWACS`, `CAPFighter`, `GhostTrack`, `EWGhostTrack`. Each overrides `identify_target()` and optionally `move()` and `calculate_threat_score()`.

**personnel.py** — `RadarOperator` auto-IDs contacts by ETA priority. `WeaponOfficer` authorizes fire on highest-scoring threats. `ThreatQueue` is a min-heap. `Engagement` tracks weapon-to-target state. `get_closest_airbase()` picks the nearest RTAF wing for scrambles.

**command_center.py** — runs the tick loop: detect → reload → personnel → engage → CIWS → world update. Handles AWACS/CAP rotation, fighter RTB, wave spawns, EW ghost injection, and damage.

---

## Running it

```bash
pip install pygame
python main.py
```

Or just run `AEGIS_Radar.exe` directly.

To rebuild the exe:
```bash
pip install pyinstaller
python -m PyInstaller --onefile --noconsole --name AEGIS_Radar ^
  --add-data "tha.json;." --add-data "mmr.json;." --add-data "lao.json;." ^
  --add-data "khm.json;." --add-data "mys.json;." --add-data "vnm.json;." ^
  --add-data "chn.json;." --add-data "idn.json;." --add-data "phl.json;." ^
  --add-data "twn.json;." main.py
```

---

## OOP concepts used

This is a university OOP final project. It demonstrates:

- Abstract base classes and inheritance (`AirContact` → 10 subclasses)
- Polymorphism (`move()`, `identify_target()`, `calculate_threat_score()` all overridden per type)
- Encapsulation (state machines like TRANSIT/ON_STATION/RTB live inside the unit, not the game loop)
- Composition (CommandCenter owns contacts, engagements, operators)
- Separation of concerns (rendering vs simulation vs domain models)

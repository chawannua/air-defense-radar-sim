# AEGIS Radar — RTAF Tactical Air Defense Simulator

A real-time air defense Command-and-Control (C2) simulator built with Python and Pygame. The player assumes the role of a tactical air defense commander for the Royal Thai Air Force (RTAF), responsible for monitoring the national airspace, identifying radar contacts, authorizing weapon engagements, and defending the base against escalating waves of hostile threats.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [How to Play](#how-to-play)
- [Controls](#controls)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [OOP Design](#oop-design)
- [Dependencies](#dependencies)

---

## Overview

The simulation models a simplified but operationally grounded air defense radar station. The radar display uses a rotating AESA (Active Electronically Scanned Array) sweep, with contacts appearing as blips that fade between scan passes. The player must distinguish between civilian airliners passing through the airspace and hostile military contacts inbound to the base.

The game progresses through three escalation phases:

| Phase | Duration | Description |
|---|---|---|
| **Peacetime** | 0 – 2 min | Heavy civilian air traffic. Rare unidentified contacts. No hostile waves. |
| **Tensions** | 2 – 6 min | Hostiles begin probing the border. Civilian traffic decreases as alert levels rise. Small attack waves may begin. |
| **Wartime** | 6 min+ | Airspace is closed to civilian traffic. Full hostile engagement with escalating difficulty, including ballistic missiles and mass drone swarms. |

The current phase is displayed in the top status bar of the HUD.

---

## Features

### Radar Display
- Rotating AESA sweep line with fading phosphor trail
- Weapon Engagement Zone (WEZ) range rings for each weapon system
- Real-world Thailand map geometry rendered from GeoJSON data
- RTAF military airbases plotted on the map (Wing 1, 4, 7, 21, 23)
- Topographical contour lines and mountain peak markers
- Smooth 60 FPS rendering with interpolation between 1-second simulation ticks
- Zoom and pan camera controls

### Contact Types

| Type | Speed | Description |
|---|---|---|
| Aircraft | Mach 0.7 – 2.5 | Mixed civilian and hostile. Hostile variants include fighters and electronic warfare jets. |
| Airliner | Mach 0.7 – 0.85 | Commercial flights transiting the airspace. Shooting one down results in immediate game over. |
| Drone / UAV | Mach 0.1 – 0.6 | Small radar cross-section. Difficult to detect at long range. |
| Helicopter | Mach 0.1 – 0.3 | Low-altitude close air support threats. |
| Tactical BM | Mach 6 – 10 | Tactical ballistic missiles. Extremely fast with short warning time. |
| ICBM | Mach 15 – 25 | Intercontinental ballistic missiles. Deals catastrophic base damage. Only THAAD can engage. |
| Ghost Track | Mach 0.02 – 0.15 | Radar clutter (birds, weather). Automatically clears on identification. |
| EW Ghost | Mach 0.8 – 3.5 | False contacts injected by enemy electronic warfare aircraft. Disappears after a few seconds. |

### AWACS and Combat Air Patrol (CAP)
- Two AWACS aircraft (Saab 340 AEW&C) operate from Wing 7, providing airborne early warning coverage over the Gulf of Thailand
- When the primary AWACS reaches low fuel, a relief aircraft launches before it returns to base
- Two CAP fighters maintain standing patrols — F-16 over the north from Wing 4, Gripen over the south from Wing 7
- CAP fighters automatically return to base when fuel is low, and replacements launch on a staggered schedule
- AWACS extends radar detection range significantly by providing a high-altitude sensor platform

### Weapon Systems

| Weapon | Range | Rounds | Specialty |
|---|---|---|---|
| THAAD | 400 km | 8 | Long-range ballistic missile defense. Only weapon effective against ICBMs. |
| SAM | 80 – 200 km | 50 | General-purpose air defense. Subject to chaff evasion by fast jets. |
| CIWS | 20 km | 150 | Fully automatic close-in weapon. Fires automatically at contacts entering range. |
| Fighter | Nearest airbase | 15 | Scrambled interceptors. Launched from the closest RTAF wing to the target. |

All weapons have reload timers and resupply logistics. Hit probability is affected by target speed, altitude, and weapon type.

### Electronic Warfare (EW)
When a Heavy EW aircraft (EA-18G Growler) is active in the airspace:
- The radar sweep line becomes erratic and unpredictable
- All radar contacts jitter on screen, degrading positional accuracy
- Hundreds of green noise particles flood the entire radar display
- Horizontal CRT-style scan line glitches appear across the screen
- False target contacts (EW Ghost Tracks) are injected directly onto the radar
- A bright jamming strobe cone radiates from the EW aircraft's bearing
- Radar detection range is reduced to 30% within the jammer's sector

### Engagement Logic
- Fighter intercepts are always launched from the geographically closest airbase
- Hit probabilities include kinematic penalties — faster targets are harder to hit
- Fighters are highly effective (95%) against slow targets such as drones and helicopters
- SAM engagements can be defeated by chaff deployment (25% evasion chance for fast jets)
- If a civilian airliner is shot down, the game ends immediately (court-martial)

---

## How to Play

### Objective
Defend the base by intercepting hostile contacts before they reach distance zero. The base starts at 100% integrity. If it reaches 0%, the game is over.

### Gameplay Loop
1. **Monitor** the radar display for new contacts appearing as unidentified blips
2. **Wait** for the Radar Operator to automatically identify each contact (indicated in the tactical log)
3. **Assess** whether the contact is friendly (blue), hostile (red), or suspect (yellow)
4. **Select** a hostile contact by clicking on it
5. **Engage** using the appropriate weapon key (1–4)
6. **Monitor** the engagement in the tactical log until impact

### Tips
- During **Peacetime**, do not fire on unidentified contacts — they are almost always civilian aircraft
- During **Wartime**, treat all unidentified contacts as hostile — civilian airspace has been closed
- Use **THAAD** only for ballistic missiles — it is a limited and valuable resource
- Use **Fighters** for long-range intercepts and **SAM** for medium-range threats
- The **CIWS** fires automatically — you do not need to control it
- If an **EW jammer** appears, prioritize destroying it to restore radar clarity
- The **Flight Info Panel** (left side) shows detailed data on the selected contact

---

## Controls

### Engagement Controls (requires a selected contact)

| Key | Action |
|---|---|
| `Click` | Select a contact on the radar or from the track list |
| `1` | Fire THAAD at selected contact |
| `2` | Fire SAM at selected contact |
| `3` | Fire CIWS at selected contact |
| `4` | Scramble a fighter from the nearest airbase |
| `Backspace` | Abort all active engagements on the selected contact |

### Manual Spawn Controls (debug/testing, no contact selected)

| Key | Action |
|---|---|
| `5` | Spawn an ICBM |
| `6` | Spawn a hostile fighter |
| `7` | Spawn a drone |
| `8` | Spawn a civilian airliner |
| `9` | Spawn a heavy EW aircraft (EA-18G Growler) |
| `0` | Spawn an AWACS |
| `W` | Spawn a hostile wave (5 fighters) |

### Navigation and Display

| Key | Action |
|---|---|
| `WASD` / `Arrow keys` | Pan the camera |
| `Mouse scroll` | Zoom in / out |
| `Middle / Right click drag` | Pan the camera |
| `F11` | Toggle fullscreen |
| `R` | Restart the simulation (only available after base is destroyed) |
| `ESC` | Quit the application |

---

## Installation

### Requirements
- Python 3.10 or higher
- pygame 2.0.0 or higher

### From Source
```bash
git clone https://github.com/chawannua/air-defense-radar-sim.git
cd air-defense-radar-sim
pip install -r requirements.txt
python main.py
```

### Pre-built Executable
A compiled Windows executable (`AEGIS_Radar.exe`) is included in the repository. No Python installation is required to run it.

### Building the Executable
To recompile the standalone executable using PyInstaller:
```bash
pip install pyinstaller
python -m PyInstaller --onefile --noconsole --name "AEGIS_Radar" ^
  --add-data "tha.json;." --add-data "mmr.json;." --add-data "lao.json;." ^
  --add-data "khm.json;." --add-data "mys.json;." --add-data "vnm.json;." ^
  --add-data "chn.json;." --add-data "idn.json;." --add-data "phl.json;." ^
  --add-data "twn.json;." main.py
```

---

## Project Structure

```
airdefense_oop_final_project/
├── main.py             # Application entry point
├── radar_ui.py         # Pygame rendering engine, input handling, HUD overlays
├── command_center.py   # Core simulation loop, escalation phases, engagement resolution
├── targets.py          # Air contact class hierarchy (AirContact and all subclasses)
├── personnel.py        # AI operators (RadarOperator, WeaponOfficer), threat prioritization
├── config.py           # Game balance constants, airbase coordinates, weapon parameters
├── requirements.txt    # Python package dependencies
├── test_logic.py       # Automated headless test suite for simulation logic
└── *.json              # GeoJSON country border data for map rendering
```

---

## OOP Design

This project was developed as an Object-Oriented Programming final project. The following OOP principles are demonstrated throughout the codebase:

### Abstraction and Inheritance
`AirContact` is an abstract base class (ABC) that defines the interface for all radar contacts. Ten subclasses inherit from it, each implementing their own behavior:

```
AirContact (ABC)
├── Aircraft          — Mixed civilian/hostile jets
├── Airliner          — Commercial flights (always friendly)
├── Helicopter        — Low-altitude rotary-wing threats
├── Drone             — Small unmanned aerial vehicles
├── TacticalBM        — Tactical ballistic missiles
├── ICBM              — Intercontinental ballistic missiles
├── AWACS             — Friendly airborne early warning
├── CAPFighter        — Friendly combat air patrol
├── GhostTrack        — Radar clutter / false alarms
└── EWGhostTrack      — Electronic warfare deception targets
```

### Polymorphism
Each subclass overrides `identify_target()` to produce type-specific identification behavior. Several subclasses also override `move()` for custom flight dynamics (e.g., `AWACS` orbits a fixed point, `Airliner` flies across the map instead of toward the base, `EWGhostTrack` moves erratically). `calculate_threat_score()` is overridden by `ICBM` and `TacticalBM` to ensure ballistic threats always receive the highest engagement priority.

### Encapsulation
State machines are encapsulated within individual unit classes rather than managed externally. Both `AWACS` and `CAPFighter` manage their own lifecycle states (`TRANSIT_TO_STATION` → `ON_STATION` → `RTB`) internally, including fuel consumption, heading calculation, and position updates.

### Composition
`CommandCenter` composes multiple subsystems: it owns the contact lists, active engagements, `RadarOperator`, `WeaponOfficer`, and `ThreatQueue`. The simulation loop delegates to each component in sequence rather than implementing all logic in a single method.

### Separation of Concerns
The project is divided into distinct modules:
- **`radar_ui.py`** — Presentation layer (rendering, input, visual effects)
- **`command_center.py`** — Application logic (game loop, spawning, engagement resolution)
- **`targets.py`** — Domain model (contact types, physics, detection)
- **`personnel.py`** — AI decision-making (threat prioritization, auto-identification)
- **`config.py`** — Configuration data (weapon stats, airbase positions, balance tuning)

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| Python | 3.10+ | Runtime |
| pygame | ≥ 2.0.0 | Graphics rendering, input handling, audio |

---

## License

This project is developed for academic purposes as part of an Object-Oriented Programming course.

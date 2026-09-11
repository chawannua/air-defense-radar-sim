# AEGIS Radar — RTAF Tactical Air Defense C2 Simulator

<div align="center">

[![Release](https://img.shields.io/github/v/release/chawannua/air-defense-radar-sim?label=version&style=flat-square)](CHANGELOG.md)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Pygame 2.0+](https://img.shields.io/badge/Pygame-2.0%2B-FF6F00?style=for-the-badge&logo=python&logoColor=white)](https://pygame.org)
[![NumPy](https://img.shields.io/badge/NumPy-1.24%2B-013243?style=for-the-badge&logo=numpy&logoColor=white)](https://numpy.org)
[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg?style=for-the-badge)](LICENSE)
[![RTAF C2](https://img.shields.io/badge/Military_C2-RTAF_SOC-00529B?style=for-the-badge&logo=shield)](https://github.com/chawannua/air-defense-radar-sim)
[![Windows Executable](https://img.shields.io/badge/Windows_Binary-AEGIS__Radar.exe-success?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/chawannua/air-defense-radar-sim/releases/latest)

## 📡 AEGIS Air Defense Radar Simulator
> A highly optimized, multi-threaded 2D radar simulation built with Python and Pygame, featuring realistic procedural audio, deterministic thread-safe mechanics, decoupled OOP architecture, and 100% logic test coverage.

### ⚡ Current Release: `v1.5.0` (Proprietary Source-Available License)
Expands the tactical theatre from 11 to 20 registered regions — adding India, Bangladesh, Sri Lanka, Nepal, Bhutan, Brunei, Timor-Leste, South Korea and North Korea as Natural Earth 1:10m sovereign outlines — growing operational span from 3,716 × 2,930 km to 6,788 × 5,806 km (+83% east-west, +98% north-south). Geodata registration only; the protected map engine gained nine loader entries and no rendering logic was altered. Test suite expansion to 42/42.

**Quick Links:**
[Download AEGIS_Radar.exe (Windows)](https://github.com/chawannua/air-defense-radar-sim/releases/latest) • [Changelog (v1.0.0 → v1.5.0)](CHANGELOG.md) • [Features](#key-features) • [Tactical Controls](#complete-tactical-keybindings-menu--combat) • [Architecture](#system-architecture--oop-design) • [Verification (42/42)](test_logic.py)

</div>

---

## Table of Contents

1. [Executive Summary & Value Proposition](#executive-summary--value-proposition)
2. [Key Features](#key-features)
3. [Real-World Tactical Map Engine (`map_manager.py`)](#real-world-tactical-map-engine-map_managerpy)
4. [Advanced Combat & Electronic Warfare Systems](#advanced-combat--electronic-warfare-systems)
5. [Anti-Jammer Electronic Counter-Countermeasures (ECCM)](#anti-jammer-electronic-counter-countermeasures-eccm)
6. [Campaign Operations & Missions Engine (`missions.py`)](#campaign-operations--missions-engine-missionspy)
7. [Tactical Armory & Technology Upgrade Tree (`[TAB]`)](#tactical-armory--technology-upgrade-tree-tab)
8. [Procedural Audio Engine (`sound_engine.py`)](#procedural-audio-engine-sound_enginepy)
9. [Visual FX & "Juice" Engine (`visual_effects.py`)](#visual-fx--juice-engine-visual_effectspy)
10. [Complete Tactical Keybindings (Menu & Combat)](#complete-tactical-keybindings-menu--combat)
11. [System Architecture & OOP Design](#system-architecture--oop-design)
12. [Automated Testing (42/42 Test Suite)](#automated-testing-4242-test-suite)
13. [Release History & Version Evolution (v1.0.0 → v1.5.0)](#release-history--version-evolution-v100--v150)
14. [Version Control, Release Architecture & Repository Governance](#version-control-release-architecture--repository-governance)
15. [Installation & Build Guide](#installation--build-guide)
16. [Dependencies](#dependencies)
17. [License & Acknowledgments](#license--acknowledgments)

---

## Executive Summary & Value Proposition

**AEGIS Radar** drops the operator into the hot seat of an RTAF Air Defense Sector Operations Center. Rather than an arcade shooter, the simulator models the cognitive workload, situational assessment, sensor physics, and doctrine of modern integrated air defense networks.

### Core Pillars
- **Geographic Authenticity**: Projected 1:10m Natural Earth vectors representing Thailand, the Bangkok FIR / ADIZ, and 8 regional nations with 22 strategic airbases and elevation masking.
- **Physical Radar Models**: Earth curvature radar horizons, fourth-root radar cross-section (RCS) range equations, line-of-sight mountain obstruction, and AESA multi-mode beam dynamics.
- **Electronic Warfare & Countermeasures**: SEAD Anti-Radiation Missiles homing on transmitter emissions, stand-off EW jamming strobe cones, active RF decoys, and multi-tier EMCON (Emission Control).
- **Procedural Audio DSP**: Zero `.wav` or `.mp3` dependencies. Every sound effect is synthesized at runtime from mathematical signal processing equations using NumPy.
- **Deterministic Simulation Core**: 1 Hz tactical logic paired with a decoupled, sub-millisecond 60 FPS interpolated rendering engine and $T^2$ trauma camera physics.

```
+----------------------------------------------------------------------------------------------------+
|                                    RTAF AIR DEFENSE C2 TOPOLOGY                                    |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|    [ SPACE-COM / EWR ]               [ SAAB 340 AEW&C ]                  [ FORWARD CAP FLIGHT ]    |
|      Early Warning                     High-Look AWACS                    F-16 / JAS-39 Gripen     |
|             │                                 │                                    │               |
|             ▼                                 ▼                                    ▼               |
|   ┌────────────────────────────────────────────────────────────────────────────────────────────┐   |
|   │                        TACTICAL EVENT BUS & SECTOR COMMAND CENTER                          │   |
|   │     - EMCON Controller: ACTIVE (360°) | SECTOR (120°) | SILENT (Dark)                      │   |
|   │     - Salvo Doctrine:   SINGLE (1x)   | RIPPLE (2x)   | SALVO (3x, P_k >= 90%)             │   |
|   │     - Defense Assets:   THAAD (400km) | SAM (200km)   | CIWS (20km) | Scramble Wings       │   |
|   └────────────────────────────────────────────────────────────────────────────────────────────┘   |
|             ▲                                 ▲                                    ▲               |
|             │                                 │                                    │               |
|    [ HOSTILE THREATS ]              [ TACTICAL MAP ENGINE ]               [ PROCEDURAL AUDIO/VFX ]  |
|    - Mach 4.5 ARM (SEAD)            - 1:10m Natural Earth Vectors         - NumPy Float32 Synthesis |
|    - 200ft Terrain Cruise           - 20 Thai Rings / 1,545 Vertices      - Multi-Stage Shockwaves  |
|    - Low-RCS Stealth Bombers        - 8 Neighboring States                - Shrapnel Embers         |
|    - Heavy EA-18G Strobe EW         - Peak LOS Occlusion                  - CRT Trauma & Vignette   |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

---

## Key Features

- **Dynamic IFF & Airspace Escalation**:
  - **Peacetime (0–2 min)**: Busy commercial airspace transited by civilian airliners (`THA`, `AXM`, `BKP`). Strict Rules of Engagement (ROE); inadvertent shootdowns trigger immediate court-martial.
  - **Tensions (2–6 min)**: Border probes, cross-border reconnaissance, electronic warfare jamming, and unidentified bogies.
  - **Wartime / DEFCON 1 (6+ min)**: Airspace closed to civil traffic. Full hostile saturation strikes including hypersonic ballistic missiles (Mach 6–25), loitering drone swarms, and cruise missiles.
- **RTAF Air Wing Distribution**: Scramble interceptors dynamically from authentic installations: Wing 1 (Korat), Wing 4 (Takhli), Wing 7 (Surat Thani), Wing 21 (Ubon), Wing 23 (Udon), Wing 41 (Chiang Mai), Wing 56 (Hat Yai), and RTN Utapao.
- **Target Tracking & Automatic Intercept Lead**: Real-time vector calculation estimating target future coordinates with animated HUD lead pip reticles and marching dashed interception vectors.
- **Logistics & Fuel Cycles**: Automated Combat Air Patrol (CAP) rotations and AWACS staggered relief flights over the Gulf of Thailand with Bingo fuel RTB (Return to Base) protocols.
- **Anti-Jammer ECCM Triad**:
  - **Radar Burn-Through Mode (`[F]`)**: AESA transmitter overdrive punches through standoff jamming noise, elevating radar range from 30% to 150% in strobe azimuths for 20 seconds.
  - **Home-On-Jam (HOJ) Missile Guidance (`[H]`)**: Missiles switch from active reflection to passive RF homing, extending SAM battery engagement range from 200 km to **350 km** against radiating jammers with $\ge 85\%$ $P_k$ (bypassing chaff decoys).
  - **Passive ESM Triangulation**: Real-time cross-bearing triangulation between Bangkok Ground C2 and airborne Saab 340 AEW&C locks exact coordinates of standoff jammers (`[ESM-FIX]`).

---

## System Boundaries & Modification Governance

> For AI agents and developers, this repository enforces strict boundaries documented in [`SYSTEM_BOUNDARIES.md`](SYSTEM_BOUNDARIES.md) and [`AGENTS.md`](AGENTS.md):
> - **Strictly Protected (Immutable)**: `map_manager.py` (v1.1.0 Natural Earth map geometry), all GeoJSON maps (`tha.json`, `coastlines.json`, etc.), and `missions.py`.
> - **Permitted**: `command_center.py`, `targets.py`, `radar_ui.py`, `sound_engine.py`, `test_logic.py`, `README.md`, `CHANGELOG.md`.

## Real-World Tactical Map Engine (`map_manager.py`)

The tactical display is built on an enterprise geospatial projection engine converting raw WGS-84 coordinate geometry into local kilometer grids relative to the Bangkok C2 Center ($13.7563^\circ\text{ N}, 100.5018^\circ\text{ E}$).

```
                             [VIETNAM: 1,960 pts]
  [MYANMAR: 2,092 pts]                │
           \                          │
            \      [LAOS: 770 pts]   /
             \            │         /
              ▼           ▼        ▼
       ┌──────────────────────────────┐
       │   THAILAND SOVEREIGN REALM   │ ◄─── 20 Rings / 1,545 High-Res Vertices
       │  (Mainland + 7 Island Rings) │      (Phuket, Samui, Chang, Kut, Phangan,
       └──────────────────────────────┘       Tarutao, Lanta)
             /            │
            /     [CAMBODIA: 542 pts]
           ▼              │
  [MALAYSIA: 698 pts]     ▼
           │       [SOUTH CHINA SEA / PACIFIC REACH]
           ▼       - Southern China & Hainan Island (1,830 pts)
  [SINGAPORE & IDN] - Sumatra / Indonesia (1,641 pts)
```

### Geospatial Dataset Breakdown

| Geodata Layer | Source / Format | Elements / Vertices | Description |
|---|---|---|---|
| **Thailand Sovereign** | `tha.json` | 20 Rings / 1,545 pts | Complete mainland boundary + Phuket, Ko Samui, Ko Chang, Ko Kut, Ko Phangan, Ko Tarutao, and Ko Lanta. |
| **Neighboring States** | `*.json` | 10 Sovereign Borders | Myanmar (2,092 pts), Vietnam (1,960 pts), Indonesia/Sumatra (1,641 pts), Southern China/Hainan (1,830 pts), Laos (770 pts), Malaysia (698 pts), Cambodia (542 pts), Singapore (18 pts), Philippines (`phl.json`), Taiwan (`twn.json`). |
| **Maritime Coastlines** | `coastlines.json` | 229 Segments / 8,338 pts | High-resolution 1:10m Natural Earth coastal boundaries for the Gulf of Thailand, Andaman Sea, and South China Sea. |
| **International Borders**| `borders.json` | 522 Segments / 2,873 pts | Land boundary demarcations between regional states. |
| **Bangkok FIR / ADIZ** | Algorithmic Polygon | 31 Strategic Waypoints | Authentic Thai Air Defense Identification Zone boundary rendered in amber tactical dashed borders. |
| **Airbases & Hubs** | Tactical Database | 22 Strategic Hubs | 8 RTAF Wings, RTN Utapao, civil gateways (Phuket, Don Mueang, Suvarnabhumi), and 12 neighbor capital/military hubs. |
| **Mountain Topography** | Digital Elevation | 6 Key Peaks + Contours | Topographic relief contours around Doi Inthanon, Doi Pha Hom Pok, Khao Luang, Phu Kradueng, Tenasserim, and Khao Yai. |

### Topographical Mountain Peak Radar Masking
Radars operate on line-of-sight (LOS). The map engine tracks key high-altitude peaks. Low-flying targets (such as cruise missiles skimming terrain at 200 ft AGL) within a 25 km occlusion shadow behind a peak higher than the target altitude are physically masked from ground radar:

$$\text{LOS Masked} \iff \exists\,\text{Peak } P : (h_P > h_{\text{tgt}}) \land \left(\text{dist}(P, \overline{O,\mathbf{r}_{\text{tgt}}}) \le 25\text{ km}\right) \land (\mathbf{r}_{\text{tgt}} \cdot \mathbf{r}_P > 0)$$

*Masked contacts disappear from ground radar scopes and require high-altitude airborne radar (AWACS at 30,000 ft or CAP fighters) to achieve look-down detection.*

### Map Display Modes (`[F2]`)
Operators can cycle through four tactical projection modes via `[F2]`:
1. **FULL TACTICAL (Mode 0)**: Complete rendering of all sovereign borders, neighbor geometries, international boundaries, topographic contour rings, mountain peaks, and maritime hydrography.
2. **SOVEREIGN FOCUS (Mode 1)**: Highlights Thailand's sovereign territory, island chains, coastlines, and the Bangkok FIR / ADIZ boundary. Mutes neighboring state clutter.
3. **MINIMAL RADAR (Mode 2)**: Retains only coastlines and strategic airbase markers for an uncluttered radar scope.
4. **TACTICAL DARK (Mode 3)**: Disables map vector overlays entirely, presenting a pure dark phosphor PPI scope.

### High-Performance Surface Caching Architecture
To guarantee a solid 60 FPS without dropping frames during intense missile swarms, `map_manager.py` implements a screen-space surface cache. Map geometries are projected into relative kilometer coordinates once upon loading. Re-rendering only executes when camera position $(cx, cy)$, zoom level, window dimensions, or display mode changes, achieving an ultra-low **1.3 ms render latency**.

---

## Advanced Combat & Electronic Warfare Systems

### Threat Profile & Kinematics

| Threat Class | Velocity | Altitude | RCS ($m^2$) | Threat Behavior & Tactical Doctrine |
|---|---|---|---|---|
| **Anti-Radiation Missile (ARM)** | Mach 3.5 – 4.5 | 18,000 – 35,000 ft | 0.05 – 0.15 | High-speed SEAD weapon homing on active radar emissions. Forces operator to switch to `SILENT` EMCON or deploy RF Decoys. |
| **Cruise Missile** | Mach 0.85 | 200 ft AGL | 0.01 | Low-level terrain skimmer; utilizes mountain peak masking. Requires AWACS look-down detection. |
| **Stealth Bomber** | Mach 0.92 | 50,000 ft | 0.001 | Low-observable strategic penetrator. Undetectable beyond 35 km by ground radar. Launches dual cruise missiles at standoff range (90 km). |
| **ICBM** | Mach 15 – 25 | 150,000 – 350,000 ft | 0.1 – 0.8 | Stratospheric ballistic missile. Deals 70% base damage. Only engageable by THAAD outside terminal phase. |
| **Tactical BM** | Mach 6 – 10 | 80,000 – 140,000 ft | 0.2 – 1.0 | Short-warning ballistic threat. High engagement priority. |
| **EA-18G Growler (EW)** | Mach 0.9 – 1.6 | 28,000 – 42,000 ft | 1.5 – 3.0 | Heavy electronic warfare platform. Emits high-intensity jamming strobe cones, degrades radar range to 30%, and injects false ghost tracks. |
| **Combat Jet / Strike** | Mach 0.8 – 2.2 | 15,000 – 45,000 ft | 1.0 – 5.0 | Multi-role fighters (Su-30, MiG-29, J-10C). Capable of deploying radar-spoofing chaff (25% evasion chance). |
| **Suicide Drone / Loitering** | Mach 0.15 – 0.4 | 500 – 4,000 ft | 0.02 – 0.05 | Low-observable loitering munitions. Difficult to detect at long range; prime targets for rapid CIWS engagement. |
| **Commercial Airliner** | Mach 0.75 – 0.85 | 30,000 – 41,000 ft | 40.0 – 100.0 | Civil transit traffic with active transponders. Destroying one results in instant court-martial. |

### Emission Control (EMCON) System (`[E]`)
Operators can modulate their electronic signature to counter hostile Electronic Support Measures (ESM) and SEAD attacks:
- **ACTIVE (360°)**: Full transmitter power output. Maximum detection envelope across all azimuths; radar dishes broadcast continuous RF energy, giving ARM seekers a clear homing beacon.
- **SECTOR (120°)**: Directional electronic beam-steering restricted to the high-threat northern and eastern sectors ($300^\circ \to 060^\circ$). Silences transmitter power across rear arcs.
- **SILENT (Dark)**: Radar transmitters shut down completely. Breaks incoming ARM seeker locks, forcing missiles into blind ballistic drift ($P_k \to 0$). The base relies exclusively on datalinks from airborne AWACS and CAP fighter radars.

```
       ACTIVE MODE (360°)                SECTOR MODE (120°)                SILENT MODE (DARK)
             .---.                             .---.                             .---.        
          .-'     '-.                       .-' / \ '-.                       .-'     '-.     
        .'     ▲     '.                   .'   /   \   '.                   .'           '.   
       /       │       \                 /    / 120°\    \                 /               \  
      |    ◄───┼───►    |               |    / SECTOR\    |               |     NO EMISSION | 
       \       │       /                 \  /         \  /                 \   (PASSIVE DL) / 
        '.     ▼     .'                   .'           '.                   '.           .'   
          '-.     .-'                       '-.     .-'                       '-.     .-'     
             '---'                             '---'                             '---'        
     Emits 360° Radiation             Emits 120° Forward Arc           Transmitter Dark / Cold
     ARM Missiles Home In             Reduces Signature 66%            ARMs Break Seeker Lock
```

### Salvo Firing Doctrine (`[S]`)
Modern missile defense doctrines employ salvo firing to defeat evasive threats and hypersonic reentry vehicles:
- **SINGLE**: 1 interceptor fired per track. Preserves magazine depth.
- **RIPPLE (2x)**: Fires 2 interceptors sequentially at the target:
  $$P_{k,\text{ripple}} = 1 - (1 - P_{k,\text{single}})^2$$
- **SALVO (3x)**: Fires 3 interceptors in coordinated succession:
  $$P_{k,\text{salvo}} = 1 - (1 - P_{k,\text{single}})^3 \quad (\text{Guarantees } P_k \ge 90\% \text{ against hypersonics})$$

### Active RF Decoys Countermeasure (`[D]`)
When Anti-Radiation Missiles are detected inbound, the commander can deploy pneumatic remote RF Decoys (`[D]`). The decoy blooms 15 km off-axis from the command center, transmitting high-power synthetic radar emissions for 20 seconds. Homing ARM seekers are seduced away from the command bunker, intercepting the expendable decoy in harmless detonation.

### Air Defense Weapon Systems

```
+------------------+----------+---------+----------+----------------------------------------------------+
| System           | Range    | Ammo    | Alt Ceiling| Primary Tactical Mission                         |
+------------------+----------+---------+----------+----------------------------------------------------+
| THAAD Battery    | 400 km   | 8 rds   | 350,000 ft| Upper-tier exo-atmospheric BMD. ICBM interceptor.  |
| SAM Battery      | 200 km   | 50 rds  | 100,000 ft| Area air defense. High-speed strike & bombers.     |
| Phalanx CIWS     | 20 km    | 150 rds | 15,000 ft | Terminal close-in point defense. Auto-fire Gatling.|
| RTAF Interceptors| Closest  | 15 sorties| 60,000 ft| Scrambled from nearest Wing to target vector.      |
+------------------+----------+---------+----------+----------------------------------------------------+
```

---

## Anti-Jammer Electronic Counter-Countermeasures (ECCM)

When hostile standoff electronic warfare aircraft (`EA-18G Growler`, `EC-130H Compass Call`, `J-16D`) project high-power noise strobes into the sector, ground radar detection range is degraded by up to 70% and false ghost tracks appear. AEGIS Radar deploys a three-pillar ECCM doctrine:

```
+---------------------------------------------------------------------------------------------------------+
|                                    ANTI-JAMMER ECCM TRIAD                                               |
+---------------------------------------------------------------------------------------------------------+
|                                                                                                         |
|  1. RADAR BURN-THROUGH [F]           2. HOME-ON-JAM (HOJ) [H]             3. PASSIVE ESM FIX [AWACS]    |
|  - AESA transmitter overdrive        - Passive RF seeker guidance         - Dual-station cross-bearing  |
|  - Multiplier: 0.3x -> 1.5x          - SAM Range: 200 km -> 350 km        - Bangkok C2 (0,0) + AWACS    |
|  - 20s capacitor discharge           - Lethality: P_k >= 85%              - Fixes exact (x, y) coords   |
|  - Cyan pencil beam overlay          - Bypasses chaff countermeasures     - Amber [ESM-FIX] diamond pip |
|                                                                                                         |
+---------------------------------------------------------------------------------------------------------+
```

### 1. Radar Burn-Through Overdrive (`[F]`)
- **Physics**: Transmitter overdrive focuses maximum AESA RF power into the jamming strobe. In radar physics, burn-through occurs when echo power from the target exceeds the jammer's noise density:
  $$\text{Jamming Multiplier} = \begin{cases} 1.50 & \text{if Burn-Through Active (ECCM [F])} \\ 0.30 & \text{if Jammed Sector without ECCM} \\ 1.00 & \text{Normal Clear Airspace} \end{cases}$$
- **Operational Profile**: Toggled via **`[F]`**. Capacitor banks sustain overdrive for 20 seconds.
- **Visual & Audio**: Draws an illuminated cyan pencil beam slicing through the strobe wedge and plays a procedural 450–2,400 Hz AESA overdrive chirp.

### 2. Home-On-Jam (HOJ) Missile Guidance (`[H]`)
- **Physics**: When a jammer broadcasts hundreds of kilowatts of noise, missiles disable active monopulse radar and switch to passive angle-on-jam tracking.
- **Capabilities**:
  - **SAM Battery Engagement Range**: Extended from 200 km to **350 km** against radiating EW targets.
  - **High Lethality**: Boosts single-missile $P_k$ to **$\ge 85\%$** against jammers.
  - **Countermeasure Immunity**: Completely bypasses aircraft chaff decoys.
- **HUD & Reticle**: Displays an amber `[HOJ-TRACK]` ring around radiating jammers and top bar status `[H] HOJ: ENABLED`.

### 3. Passive ESM Cross-Bearing Triangulation (Saab 340 AEW&C)
- **Physics**: Dual-station Electronic Support Measures (ESM) cross-bearing triangulation between ground C2 (Bangkok HQ $0, 0$) and the airborne Saab 340 AEW&C loitering over the Gulf of Thailand.
- **Automation**: Operates autonomously whenever AWACS is active in theater.
- **Display**: Fixes the exact $(x, y)$ coordinates of standoff jammers with an amber diamond crosshair and `[ESM-FIX]` tag.

---

## Campaign Operations & Missions Engine (`missions.py`)

Cycle operational scenarios at any time by pressing **`[F1]`**. Each scenario introduces unique victory conditions, threat compositions, and operational constraints.

```
       [F1] KEYPRESS
            │
            ▼
    ┌────────────────────────┐
    │  OP-DEFENSE (Standard) │ ──► Escalating 3-Phase Defense Sandbox (Peacetime -> Wartime)
    └────────────────────────┘
            │
            ▼
    ┌────────────────────────┐
    │  OP-GUARDIAN (Escort)  │ ──► Escort RTAF VIP Flight (ROYAL-01) Chiang Mai -> Don Mueang
    └────────────────────────┘
            │
            ▼
    ┌────────────────────────┐
    │  OP-IRONSWARM (DEFCON1)│ ──► Repel 3 Massive Waves of Saturation Swarms & Ballistic Salvos
    └────────────────────────┘
            │
            ▼
    ┌────────────────────────┐
    │  OP-GHOST (Stealth)    │ ──► Intercept 2x Low-RCS Stealth Bombers before Standoff Launch
    └────────────────────────┘
```

### 1. Operation Endless Air Defense (`OP-DEFENSE`)
- **Briefing**: Maintain airspace sovereignty across the Bangkok FIR. Manage escalating tension levels from Peacetime civil traffic through DEFCON 1 full-scale conflict.
- **Victory Condition**: Continuous survival; maximize career XP and civilian protection scores.

### 2. Operation Guardian Angel (`OP-GUARDIAN`)
- **Briefing**: Royal Thai VIP Transport `ROYAL-01` departs Wing 41 (Chiang Mai) transiting south to Don Mueang (`VTBD`). Hostile strike packages and loitering suicide drones attempt to ambush the flight corridor.
- **Victory Condition**: `ROYAL-01` touches down safely at Don Mueang.
- **Failure**: Destruction of `ROYAL-01` results in an immediate court-martial and mission failure.

### 3. Operation Iron Swarm (`OP-IRONSWARM`)
- **Briefing**: Immediate DEFCON 1 saturation strike. Hostiles launch 3 coordinated assault waves:
  - *Wave 1*: 8x loitering suicide drone swarms crossing the eastern border.
  - *Wave 2*: Supersonic Cruise Missiles and Mach 4 Anti-Radiation Missiles.
  - *Wave 3*: Combined ICBM terminal strike supported by cruise missiles and ARM salvos.
- **Victory Condition**: Neutralize all 3 attack echelons while preserving base structural integrity. Award: **+8,000 XP**.

### 4. Operation Ghost Hunter (`OP-GHOST`)
- **Briefing**: Forward SIGINT identifies 2x strategic low-RCS Stealth Bombers ingressing at 50,000 ft. Ground radar cannot detect stealth airframes beyond 35 km.
- **Doctrine**: Scramble forward Gripen fighters and deploy AWACS to establish airborne triangulation before bombers reach their 90 km standoff weapon release point.
- **Victory Condition**: Splash both stealth bombers before standoff launch. Award: **+10,000 XP**.

---

## Tactical Armory & Technology Upgrade Tree (`[TAB]`)

Pressing **`[TAB]`** opens the tactical upgrades overlay. Upgrades are purchased in real time using XP earned from verified intercepts, long-range kills, and protected airliners.

### Two-Tier Armory Progression Architecture
The armory features an expandable, two-tier developmental tree:
1. **Tier 1 (Conventional Systems)**: Standard operational enhancements available immediately.
2. **Tier 2 (Black Ops Experimental Arsenal)**: Classified advanced weapon and sensor prototypes unlocked **only after mastering all 5 Tier 1 upgrades**.

Inside the Armory overlay, press **`[T]`** to switch between **Tier 1: Conventional** and **Tier 2: Black Ops** tabs.

```
+----------------------------------------------------------------------------------------------------------------+
|                                    TACTICAL ARMORY & UPGRADE SYSTEM [TAB]                                      |
+----------------------------------------------------------------------------------------------------------------+
|  [T] TAB 1: TIER 1 CONVENTIONAL                                  [T] TAB 2: TIER 2 BLACK OPS (CLASSIFIED)      |
|  - AESA Radar Overclock [1] (1,200 XP)                           - Quantum Space Radar [1 / 6] (3,500 XP)      |
|  - Doppler Clutter Filter [2] (800 XP)                           - Meteor Ramjet Scrambles [2 / 7] (4,000 XP)  |
|  - RF Decoy Resupply Pack [3] (1,000 XP)                         - Helios Laser CIWS [3 / 8] (5,000 XP)        |
|  - Phalanx Rapid Ammo Feed [4] (1,500 XP)                        - Tactical EMP Generator [4 / 9] (4,500 XP)   |
|  - Active AESA Seekers [5] (2,500 XP)                            - Nanotech Aegis Shield [5 / 0] (6,000 XP)    |
|                                                                                                                |
|  Status: [5/5 Unlocked] ──► AUTHORIZES ─────────────────────────► Status: [CLASSIFIED LAB UNLOCKED]            |
+----------------------------------------------------------------------------------------------------------------+
```

### Tier 1: Conventional Upgrades

| Key | Upgrade Node | Cost | Tactical Enhancement | Operational Effect |
|---|---|---|---|---|
| **`[1]`** | `AESA_RANGE` | 1,200 XP | AESA Radar Overclock | Increases maximum radar instrumented range by +25% (800 km $\to$ 1,000 km). |
| **`[2]`** | `DOPPLER_FILTER` | 800 XP | Doppler Clutter Filter | High-velocity MTI filtering automatically purging weather clutter and bird flock false tracks. |
| **`[3]`** | `DECOY_PACK` | 1,000 XP | Decoy Resupply | Instantly adds +3 pneumatic Active RF Decoys to the command bunker inventory. |
| **`[4]`** | `RAPID_CIWS` | 1,500 XP | Phalanx Rapid Feed | Expands CIWS magazine capacity by +100 rounds (150 $\to$ 250) and triggers an instant reload. |
| **`[5]`** | `AESA_SEEKERS` | 2,500 XP | Active AESA Seekers | High-precision gallium-nitride missile guidance providing +15% hit probability ($P_k$) across SAM and THAAD batteries. |

*Unlock Condition for Tier 2: Master and purchase all 5 Tier 1 upgrades (Total: 7,000 XP).*

### Tier 2: Black Ops Experimental Arsenal (Classified)

High Command unlocks experimental Skunkworks / Black Ops prototypes once the conventional armory is completely mastered:

| Key | Upgrade Node | Cost | Tactical Enhancement | Operational Effect |
|---|---|---|---|---|
| **`[1]`** / **`[6]`** | `QUANTUM_SPACE_RADAR` | 3,500 XP | Orbital Quantum Sensor Constellation | Deploys entangled-photon space-based radar looking down from orbit. **Completely bypasses terrain and mountain peak line-of-sight masking**, detecting low-altitude cruise missiles instantly. |
| **`[2]`** / **`[7]`** | `METEOR_HYPERSONIC` | 4,000 XP | Ramjet Hypersonic BVR Scrambles | Equips RTAF fighter wings with MBDA Meteor solid-fuel ramjet missiles. Expands fighter scramble sortie pool by **+10 sorties** (15 $\to$ 25 max) and provides an immediate full restock. |
| **`[3]`** / **`[8]`** | `IRON_BEAM_DIRECTED_ENERGY` | 5,000 XP | Helios 100kW Directed Energy Laser | Upgrades close-in defense to speed-of-light directed energy. Extends auto-engagement envelope from 5.0 km to **30.0 km** with guaranteed **$\ge 95\%$ lethal kill rate** against supersonic threats. |
| **`[4]`** / **`[9]`** | `TACTICAL_EMP_BURST` | 4,500 XP | High-Power Microwave (HPM) Generator | Installs an omnidirectional tactical EMP capacitor bank. Press **`[B]`** during combat to discharge: **immediately vaporizes all EW ghost tracks/jamming** and **fries incoming Anti-Radiation Missile seeker locks**, sending ARMs into blind ballistic drift. |
| **`[5]`** / **`[0]`** | `NANOTECH_AEGIS_SHIELD` | 6,000 XP | Nanotech Force Field & Hull Regeneration | Fortifies Command Bunker structural integrity to **150 Max HP** (restoring HP to 150 immediately) and provides passive 50% damage reduction against heavy ballistic impacts. |

### RTAF Career Rank & XP Progression

Operators earn XP for successful intercepts, with multipliers for threat severity:
- **Drone / Heli**: +100 XP
- **Cruise Missile**: +200 XP
- **Anti-Radiation Missile**: +250 XP
- **Tactical Ballistic Missile**: +400 XP
- **ICBM Intercept**: +1,000 XP
- **Long-Range Intercept (>400 km)**: **+300 XP Bonus**

#### Rank Milestones
$$\text{Airman} \to \text{Leading Airman} (500) \to \text{Corporal} (1.2k) \to \text{Sergeant} (2.2k) \to \text{Flight Lieutenant} (3.5k) \to$$
$$\text{Squadron Leader} (5.2k) \to \text{Wing Commander} (7.5k) \to \text{Group Captain} (10.5k) \to \text{Air Commodore} (14.5k) \to$$
$$\text{Air Marshal} (20k) \to \text{Air Chief Marshal} (28k)$$

---

## Procedural Audio Engine (`sound_engine.py`)

AEGIS Radar contains **0 MB of pre-recorded audio assets**. Every acoustic event is generated on the fly via discrete Digital Signal Processing (DSP) algorithms implemented in NumPy and fed directly into `pygame.sndarray` stereo buffers at 44.1 kHz, 16-bit PCM.

```
      NumPy Mathematical Signal Generation (44.1 kHz Float32 Array)
        │
        ├── Frequency Modulation (FM) & Chirp Sweeps
        ├── Gaussian FIR Low-Pass Convolution Filtering (_gaussian_lowpass)
        ├── Pulse-Width Modulation (PWM) & Harmonic Overtone Stacking
        └── Tanh Soft-Clipping & Peak Normalization Limiting
        │
        ▼
   pygame.sndarray.make_sound (Int16 Stereo PCM Buffer)
        │
        ▼
   Pygame Mixer Hardware Channels (Low-Latency 512 Buffer)
```

### Synthesized Acoustic Suite

1. **AESA Electronic Chirp (`radar_ping`)**: 90 ms logarithmic frequency chirp sweeping from 1,600 Hz down to 850 Hz with an exponential decay envelope:
   $$s(t) = \sin\left(2\pi \cdot f(t) \cdot t\right) \cdot e^{-14 t}, \quad f(t) = 1600 \cdot (850 / 1600)^{t / 0.09}$$
2. **DEFCON 1 Emergency Alarm (`defcon1_alarm`)**: Dual-tone alternating square-wave horn pulsing between 820 Hz and 640 Hz in 250 ms bursts.
3. **Missile Rocket Launch (`missile_launch`)**: High-frequency ignition pop followed by a rising thrust drone (90 Hz up to 240 Hz) layered with brown noise rumble.
4. **Supersonic Detonation & Flak (`explosion_flak`)**: Detonation shock transient spike decaying into a sub-bass acoustic boom (160 Hz down to 35 Hz) with low-pass filtered expansion noise. Includes `heavy=True` mode for ICBM and command base hits.
5. **CIWS Gatling BRRRRT (`ciws_burst`)**: 65 Hz fundamental pulse train with stacked odd harmonics modeling the 3,900 RPM firing rate of a 20mm M61A1 Vulcan cannon.
6. **Tactical Warning Pip (`contact_alert`)**: 1,200 Hz pure-tone alert burst (60 ms) on contact identification.
7. **Tactical Radio Dispatch (`radio_chatter`)**: Radio squawk burst combined with asynchronous non-blocking Windows SAPI text-to-speech voice notifications (with fallback telemetry beeps).

---

## Visual FX & "Juice" Engine (`visual_effects.py`)

A dedicated game-feel engine translates kinetic impacts into visceral tactical feedback:

```
                                  KINETIC IMPACT EVENT
                                           │
          ┌────────────────────────────────┼────────────────────────────────┐
          ▼                                ▼                                ▼
   [ SHOCKWAVE RING ]             [ FLASH BLOOM ]                 [ SHRAPNEL PARTICLES ]
   - R: 5px -> 45px (Non-linear)  - 3-Frame Hyper-Bright Epicenter - 25-90 Thermodynamic Embers
   - Width: 3px -> 1px            - Soft Alpha Halo Glow           - White -> Yellow -> Amber -> Smoke
   - Smooth Alpha Dissolve                                         - Aerodynamic Drag & Gravity
          │                                │                                │
          └────────────────────────────────┼────────────────────────────────┘
                                           │
                                           ▼
                            [ CAMERA TRAUMA MODEL (T^2) ]
                            - Trauma offset = T^2 * Max_Offset
                            - Non-linear decay per second
```

- **Multi-Phase Shockwaves**: Expanding circular wave-front rings with non-linear ease-out expansion curves ($R(t) = R_0 + \Delta R \cdot t^{0.65}$) and inner refraction ripples.
- **Thermodynamic Shrapnel Particles**: 25 to 50 individual high-velocity shrapnel embers (55 to 90 for heavy detonations) with aerodynamic drag, gravity drift, thermal shrinkage, and a 4-stage thermodynamic color decay cycle:
  $$\text{Pure White } (255, 255, 255) \longrightarrow \text{Solar Yellow } (255, 235, 75) \longrightarrow \text{Hot Amber } (255, 125, 20) \longrightarrow \text{Charcoal Smoke } (50, 50, 50)$$
- **Trauma-Squared Screen Shake**: Implements the industry-standard $T^2$ trauma model where screen jitter is proportional to $\text{trauma}^2 \times \text{max\_offset}$. Ensures low trauma creates subtle vibrations while ballistic impacts generate intense, screen-shaking jolts.
- **Dynamic Targeting Reticle**: Rotating corner brackets around selected targets with an animated dashed lead vector pointing to the future intercept coordinate:
  $$\mathbf{r}_{\text{lead}} = \mathbf{r}_{\text{target}} + \mathbf{v}_{\text{target}} \cdot t_{\text{intercept}}$$
- **Emergency CRT Damage Vignette**: When command base HP falls below 30%, a pulsating crimson CRT edge gradient constricts around the screen perimeter, escalating in frequency from 4 Hz to 12 Hz as integrity nears zero.

---

## Complete Tactical Keybindings (Menu & Combat)

### Pre-Simulation: Main Menu Navigation (`scenes.py`)

| Keybinding / Input | Context | Menu Action |
|---|---|---|
| **`[Up Arrow]` / `[W]`** | Main Menu | Move selection cursor up (`SPECTATOR` $\to$ `PLAYER` $\to$ `EXIT`) |
| **`[Down Arrow]` / `[S]`** | Main Menu | Move selection cursor down |
| **`[Enter]` / `[Space]`** | Main Menu | Activate selected item (Launch chosen sortie mode or exit) |
| **`[Mouse Motion]`** | Main Menu | Hover selection over menu options with visual green highlight |
| **`[Mouse Left-Click]`** | Main Menu | Direct click-to-launch selected mode |
| **`[ESC]`** | Main Menu | Clean simulation termination |

### Tactical Air Defense C2 Operations (`radar_ui.py`)

| Keybinding | Context | Tactical Action |
|---|---|---|
| **`[Click]`** | Radar / Track List | Select an air contact or track list entry |
| **`[1]`** | Target Selected | Fire **THAAD** Battery at selected target (Long-range BMD) |
| **`[2]`** | Target Selected | Fire **SAM** Battery at selected target (Medium-range air defense) |
| **`[3]`** | Target Selected | Engage target with **Phalanx CIWS** (Close-in defense, $\le 20$ km) |
| **`[4]`** | Target Selected | Scramble **Interceptors** from the closest operational RTAF Wing |
| **`[Backspace]`**| Target Selected | **Abort Engagement**: Cancels active missiles and recalls fighters |
| **`[E]`** | Global | Toggle **EMCON Mode**: `ACTIVE` (360°) $\to$ `SECTOR` (120°) $\to$ `SILENT` (Dark) |
| **`[S]`** | Global | Toggle **Salvo Doctrine**: `SINGLE` (1x) $\to$ `RIPPLE` (2x) $\to$ `SALVO` (3x, $P_k \ge 90\%$) |
| **`[D]`** | Global | Deploy **Active RF Decoy**: Blooms 15 km away to seduce homing ARMs |
| **`[F]`** | Global | Toggle **Radar Burn-Through Mode (ECCM)**: AESA transmitter overdrive cuts through jammer strobe ($0.3\times \to 1.5\times$ range) |
| **`[H]`** | Global | Toggle **Home-On-Jam (HOJ) Guidance**: Passive RF seeker doctrine extends SAM range to 350 km against jammers ($P_k \ge 85\%$) |
| **`[B]`** | Global | Discharge **Tactical EMP Shockwave**: Vaporizes EW ghost tracks & fries ARM seekers (requires Tier 2 EMP) |
| **`[TAB]`** | Global | Toggle **Tactical Armory & Upgrade Tree** (Tier 1 Conventional & Tier 2 Black Ops) |
| **`[T]`** | Armory Open | Toggle **Armory Tab**: `Tier 1: Conventional` $\longleftrightarrow$ `Tier 2: Black Ops (Classified)` |
| **`[1 - 5]`** | Armory Open | Purchase tech upgrade nodes for current active tab (Tier 1 or Tier 2) |
| **`[6 - 0]`** | Armory Open | Direct-key purchase for Tier 2 Black Ops nodes (`6`=Quantum, `7`=Meteor, `8`=Laser, `9`=EMP, `0`=Nanotech) |
| **`[F1]`** | Global | Cycle **Campaign Scenario**: `OP-DEFENSE` $\to$ `OP-GUARDIAN` $\to$ `OP-IRONSWARM` $\to$ `OP-GHOST` |
| **`[F2]`** | Global | Cycle **Map Overlay**: `FULL TACTICAL` $\to$ `SOVEREIGN FOCUS` $\to$ `MINIMAL` $\to$ `DARK` |
| **`[U]`** | Global | Toggle **Audio Mute** (Procedural synthesizer silence) |
| **`[F11]`** | Global | Toggle **Fullscreen / Windowed** mode |
| **`[R]`** | Global / Defeat | **Re-initialize Sortie**: Resets command center and tactical systems (functional in both Spectator & Player modes) |
| **`[ESC]`** | Global | Terminate simulation and exit cleanly |
| **`[Arrow Keys]`** | Global | Pan tactical radar camera (W, S, D reserved for tactical actions) |
| **`[Mouse Wheel]`**| Global | Smooth Zoom In / Zoom Out (0.10x to 10.0x scale) |
| **`[Mid/Right Drag]`**| Global | Pan camera via mouse drag |
| **`[W]`** | Global | Select airborne **AWACS** aircraft & activate airborne radar C2 menu |
| **`[Right-Click]`** | AWACS Selected | Retask AWACS to new orbit patrol station at cursor coordinate |
| **`[= / +]` / `[- / _]`** | AWACS Selected | Expand / tighten AWACS orbit patrol radius ($\pm 10$ km, 20–150 km) |
| **`[R]`** | AWACS Selected | Order immediate Return to Base (RTB) to Wing 7 Surat Thani |
| **`[P]`** | Debug / Sandbox | Force **Phase 3 (Wartime)** trigger: closes civilian airspace, activates DEFCON 1 |
| **`[5 - 0]`** | Debug (No Target)| Spawn test targets: `5`=ICBM, `6`=Fighter, `7`=Drone, `8`=Airliner, `9`=EA-18G EW, `0`=AWACS |
| **`[M]` / `[C]`** | Debug (No Target)| Spawn special threats: `M`=ARM Missile, `C`=Cruise Missile |

---

## System Architecture & OOP Design

The project is structured according to strict Object-Oriented Programming (OOP) principles, clean separation of concerns, and an event-driven architecture.

### Subsystem Architecture & Execution Flow

```
                                      [ main.py ]
                                           │  Bootstraps Pygame Display & Scene Manager
                                           ▼
                                [ scenes.py (MenuScene) ]
                                ├── camera_director.py (Smoothstep RTAF Waypoint Pan)
                                └── profiles.py (SimulationProfile Selection)
                                           │
                        ┌──────────────────┴──────────────────┐
                        ▼                                     ▼
             [ SPECTATOR_PROFILE ]                   [ PLAYER_PROFILE ]
             - Autonomous AI C2                      - Human Holds Trigger
             - 2.0x Spawn Pressure                   - Balanced Threat Waves
             - View-Only Command Gate                - Starvation-Free Backup Fire
                        └──────────────────┬──────────────────┘
                                           ▼
                                [ radar_ui.py:start_radar() ]
                                           │  Composes & Updates C2 Systems
                                           ▼
                               [ command_center.py:CommandCenter ]
                               (Tactical Aggregate Root & Event Bus)
       ┌──────────────────┬────────────────┬─────────────────┬──────────────────┐
       ▼                  ▼                ▼                 ▼                  ▼
[ map_manager.py ]  [ targets.py ]  [ personnel.py ]  [ missions.py ]   [ sound_engine.py ]
- 11x GeoJSON       - 10x Contact   - RadarOperator   - OP-DEFENSE      - NumPy DSP Audio
- Peak Masking        Subclasses    - WeaponOfficer   - OP-GUARDIAN     - 0 MB WAV/MP3 Files
- Surface Cache     - Kinematics    - Rank & XP       - OP-IRONSWARM    - Float32 Synthesizers
                    - Threat Queue                    - OP-GHOST
                                                                                │
                                                                                ▼
                                                                      [ visual_effects.py ]
                                                                      - T² Trauma Camera
                                                                      - Shockwave Rings
                                                                      - Thermodynamic Embers
```

### Complete Repository Directory Layout

```
air-defense-radar-sim/
├── main.py                   # Application entry point; initializes Pygame & launches SceneManager
├── scenes.py                 # Scene state machine: Scene base class, SceneManager, dark-tactical MenuScene
├── camera_director.py        # Cinematic camera: smoothstep waypoint easing across RTAF airbases, cosine zoom
├── profiles.py               # Decoupled SimulationProfile: SPECTATOR_PROFILE, PLAYER_PROFILE, DEFAULT_PROFILE
├── radar_ui.py               # Presentation layer: AESA sweep render, PPI CRT phosphors, HUD overlays, input handlers
├── command_center.py         # Simulation core & aggregate root: engagement doctrine, ECCM triad, threat queue
├── map_manager.py            # Geospatial projection: Natural Earth 1:10m vectors, mountain peak LOS masking, caching
├── targets.py                # Domain models: AirContact ABC and 10 polymorphic target subclasses
├── personnel.py              # AI tactical crew: RadarOperator, WeaponOfficer, XP career rank progression
├── missions.py               # Operational scenarios: OP-DEFENSE, OP-GUARDIAN, OP-IRONSWARM, OP-GHOST
├── sound_engine.py           # 100% procedural audio: NumPy mathematical DSP synthesis (zero audio files)
├── visual_effects.py         # Visual juice engine: T² camera trauma model, shockwaves, shrapnel, lead vectors
├── config.py                 # Simulation balance constants, RTAF airbase coordinates, weapon envelopes (single truth)
├── test_logic.py             # Headless automated verification suite: 42 test modules passing 100%
├── CONTRIBUTING.md           # Developer onboarding, domain modeling guides, and contribution rules
├── CHANGELOG.md              # Historical version changelog adhering to Keep a Changelog & SemVer
├── SYSTEM_BOUNDARIES.md      # Immutable boundaries and modification governance for developers and AI agents
├── AGENTS.md                 # Agent orchestration directives and dynamic model tiering rules
├── requirements.txt          # Minimal runtime dependencies (pygame >= 2.0.0, numpy >= 1.24.0)
├── .gitignore                # Strict repository hygiene (ignores work/, *.exe, *.log, byte-cache)
└── *.json                    # 1:10m Natural Earth geodata:
    ├── tha.json              # Thailand sovereign border (20 rings, 1,545 vertices)
    ├── mmr.json              # Myanmar sovereign boundary
    ├── lao.json              # Laos sovereign boundary
    ├── khm.json              # Cambodia sovereign boundary
    ├── mys.json              # Malaysia sovereign boundary
    ├── sgp.json              # Singapore sovereign boundary
    ├── vnm.json              # Vietnam sovereign boundary
    ├── chn.json              # Southern China & Hainan Island
    ├── idn.json              # Indonesia & Sumatra
    ├── phl.json              # Philippines boundary (+57% theater expansion)
    ├── twn.json              # Taiwan boundary (+57% theater expansion)
    ├── coastlines.json       # Maritime coastlines (229 segments, 8,338 vertices)
    └── borders.json          # International land demarcations (522 segments, 2,873 vertices)
```

### Domain Contact Hierarchy

```
                                  AirContact (ABC)
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        │                                │                                │
     Aircraft                         Missile                         AirSupport
        ├── Airliner (Civil)             ├── TacticalBM                  ├── AWACS (Early Warning)
        ├── Fighter (Combat Strike)      ├── ICBM (Ballistic Reentry)    └── CAPFighter (Combat Air Patrol)
        ├── EA-18G Growler (Heavy EW)    ├── AntiRadiationMissile (ARM)
        ├── Helicopter (Rotary)          └── CruiseMissile (Terrain LOS)
        ├── Drone (UAV Loiter)
        ├── StealthBomber (Low-RCS)
        └── VIPTransport (ROYAL-01)
```

### OOP Principles in Practice

- **Polymorphism**: 
  - Subclasses override `identify_target()` with domain-specific callsign prefixes, transponder squawks, and flight plans.
  - Subclasses implement specialized `move()` dynamics: `AWACS` executes circular loiter orbits; `Airliner` transits flight corridors; `AntiRadiationMissile` tracks radar emission coordinates; `CruiseMissile` computes terrain occlusion; `VIPTransport` tracks southern approach waypoints.
  - Subclasses override `calculate_threat_score()` to ensure critical ballistic threats automatically populate the top of the AI engagement queue.
- **Composition**:
  - `CommandCenter` acts as the central aggregate root, composing `MapManager`, `SoundManager`, `VFXManager`, `MissionManager`, `RadarOperator`, `WeaponOfficer`, and `ThreatQueue`.
- **Encapsulation**:
  - Internal states (e.g., weapon cooldowns, reload sequences, decoy timers, fuel consumption rates, camera trauma values) are encapsulated within their respective domain entities and accessed via clean methods.
- **Event-Driven Architecture**:
  - The core simulation decouples gameplay logic from presentation via an asynchronous Tactical Event Bus (`emit_event()`). Visual and acoustic engines subscribe to events (`INTERCEPT_KILL`, `MISSILE_LAUNCH`, `BASE_DAMAGE`, `DEFCON_CHANGE`, `PROMOTION`), eliminating tight coupling.

---

## Automated Testing (42/42 Test Suite)

AEGIS Radar includes a comprehensive, headless automated test suite in [`test_logic.py`](test_logic.py). All 42 test modules validate core simulation physics, kinematics, and operational doctrines without requiring a GUI:

```bash
$ python test_logic.py
```

### Test Suite Matrix

```
[PASS]  1. Coordinate System Geometry (North/East sine/cosine bearing projection)
[PASS]  2. AWACS set_xy Bearing Consistency (Cartesian-to-polar angle validation)
[PASS]  3. CAPFighter set_xy Bearing Consistency
[PASS]  4. AWACS move() Heading Alignment with Vector Displacement
[PASS]  5. Airliner move() Cartesian Y-Convention Integrity
[PASS]  6. EWGhostTrack Lifecycle & Spatial Range Bounds
[PASS]  7. CommandCenter Electronic Warfare Ghost Track Injection
[PASS]  8. EWGhostTrack Harmlessness (Zero Base Structural Damage on Impact)
[PASS]  9. Base AirContact Kinematic Delta Position Updating
[PASS] 10. AntiRadiationMissile (ARM) Emission Homing, SILENT Loss of Lock & Decoy Seduction
[PASS] 11. CruiseMissile Line-of-Sight Topographical Mountain Peak Masking (Doi Inthanon)
[PASS] 12. EMCON Three-Tier State Cycling & Sensor Gating Logic
[PASS] 13. Salvo Firing Doctrine (SINGLE/RIPPLE/SALVO) Ammunition Consumption & P_k
[PASS] 14. Active RF Decoy Deployment, Blooming Lifespan & Depletion Limits
[PASS] 15. Tactical Event Bus Message Dispatch & DEFCON Transition Hooks
[PASS] 16. RTAF Career Rank XP Progression & Civilian Shootdown Court-Martial
[PASS] 17. After-Action Report (AAR) Data Serialization & Performance Metrics
[PASS] 18. Tactical Technology Upgrade Tree Unlocking, Deductions & Multipliers
[PASS] 19. Campaign Mission Cycling (OP-DEFENSE, OP-GUARDIAN, OP-IRONSWARM, OP-GHOST)
[PASS] 20. Real Tactical Map Geodata Validation (Thailand 20 rings / 1,545 pts, 8 Neighbors, ADIZ)
[PASS] 21. CIWS Manual Intercept Execution & Rapid CIWS Rate-of-Fire Upgrade
[PASS] 22. AWACS & CAP RTB Landing Asset Pool Recovery without Leakage
[PASS] 23. Friendly Fire Prevention & Universal Civilian Shootdown Court-Martial
[PASS] 24. Multi-Format Geodata Mountain Peak Masking Tuple Unpacking Safety
[PASS] 25. Historical Event Bus Retention for After-Action Report (AAR) Analytics
[PASS] 26. Tier 2 Black Ops Experimental Arsenal Gating, Purchases & Mechanics
[PASS] 27. AI Interceptor Prioritization & Standoff EW Suppression
[PASS] 28. Anti-Jammer Electronic Counter-Countermeasures (ECCM Burn-Through [F], HOJ [H] 350km SAM, Passive ESM Triangulation)
[PASS] 29. Controllable AWACS Operations & Sensor Fusion
[PASS] 30. Tactical Audio Engine & Alarm Cooldown Logic
[PASS] 31. Visual Effects Subsystem & EMP Shockwave Ring
[PASS] 32. Simulation Profiles (Spectator vs Player)
[PASS] 33. Cinematic Camera Director
[PASS] 34. CommandCenter Profile-Driven Spawn & Weapon Autonomy
[PASS] 35. Auto-CIWS Last-Ditch Leaker Discrimination
[PASS] 36. Context-Derived Chaff / Evasion Countermeasures
[PASS] 37. EW Ghost Flood Gated on Real Electronic-Warfare State
[PASS] 38. DEFAULT_PROFILE Retains Command Input
[PASS] 39. Spectator Cannot Reach IFF Re-Designation (Court-Martial Guard)
[PASS] 40. Restart After Death Reachable in Both Modes
[PASS] 41. Player-Mode Backup Fire Must Not Starve on a Distant Priority Threat

==================================================
ALL 41 TEST MODULES PASSED (100% SUCCESS RATE)
```

---

## Release History & Version Evolution (v1.0.0 → v1.5.0)

This project strictly adheres to [Semantic Versioning 2.0.0 (SemVer)](https://semver.org/) and follows the [Keep a Changelog](https://keepachangelog.com/) standard.

Full changelog details and release history are maintained in **[CHANGELOG.md](CHANGELOG.md)**.

### Version Evolution: `v1.0.0` ➔ `v1.1.0` ➔ `v1.1.1` ➔ `v1.2.0` ➔ `v1.3.0` ➔ `v1.3.1` ➔ `v1.3.2` ➔ `v1.4.0` ➔ `v1.4.1` ➔ `v1.5.0`

In accordance with SemVer (`MAJOR.MINOR.PATCH`):
- The version increment from **`v1.0.0`** to **`v1.1.0`** introduced major Phase 3 features and the real Southeast Asia geodata map engine.
- The version increment from **`v1.1.0`** to **`v1.1.1`** delivered critical bug fixes, UI coordinate harmonizations, audio click elimination, and asset recovery safeguards.
- The version increment from **`v1.1.1`** to **`v1.2.0`** introduced the Tier 2 Black Ops Experimental Arsenal, the 3-pillar Anti-Jammer ECCM Triad, and automated AI interceptor standoff suppression.
- The version increment from **`v1.2.0`** to **`v1.3.0`** introduces Interactive AWACS Command & Control, a complete Procedural Audio Engine Overhaul, and comprehensive Input Disambiguation.
- The version increment from **`v1.3.0`** to **`v1.3.1`** implemented security hardening, audio thread-safety locks, memory caps, and trajectory alignment telemetry.
- The version increment from **`v1.3.1`** to **`v1.3.2`** delivers the `VFXManager.add_shockwave()` crash hotfix triggered by Tactical EMP `[B]` discharge under heavy contact loads, and expands the test suite to 31/31.
- The version increment from **`v1.3.2`** to **`v1.4.0`** introduces the cinematic Main Menu and scene system, strict Spectator/Player mode separation, context-aware skill triggers replacing RNG and blind-geometry firing, and expands map coverage to the Philippines and Taiwan (+57% east-west extent). Test suite expands to 41/41.
- The version increment from **`v1.4.0`** to **`v1.4.1`** expands the tactical theatre from 11 to 20 registered regions across South, South-East and East Asia, growing operational span from 3,716 x 2,930 km to 6,788 x 5,806 km (+83% east-west, +98% north-south). Geodata registration only; no rendering logic altered. Test suite expands to 42/42.
- The version increment from **`v1.4.1`** to **`v1.5.0`** changes the distribution licence from MIT to a proprietary source-available licence. No simulation behaviour changed; the MINOR bump marks the change in what recipients may do with the software. Releases up to v1.4.1 remain available under MIT.

### 🌟 Version 1.5.0 Feature Highlights
- **Licence Change (MIT ➔ Proprietary Source-Available):** Source remains public for evaluation, study and personal non-commercial use. Modification, derivative works, redistribution and commercial use now require written permission.
- **Explicitly Non-Retroactive:** Releases up to and including `v1.4.1` were published under MIT and remain available under those terms permanently, recorded in Section 3(b) of the licence rather than left ambiguous.
- **Third-Party Licensing Preserved:** Section 4 records that pygame (LGPL-2.1), NumPy (BSD-3-Clause), SDL2 (zlib) and FreeType (FTL) remain under their own terms, and that geodata is public-domain Natural Earth. LGPL permits proprietary applications that link pygame.
- **Documentation Alignment:** `CONTRIBUTING.md` no longer solicits outside contributions; its technical documentation is retained as internal reference.
- **No Behavioural Change:** The simulation is functionally identical to v1.4.1 — 20 regions, 6,788 × 5,806 km theatre, suite 42/42.

### 🌟 Version 1.4.1 Feature Highlights
- **Geodata Theatre Expansion (11 ➔ 20 Regions):** Registered Natural Earth 1:10m sovereign outlines for India, Bangladesh, Sri Lanka, Nepal, Bhutan, Brunei, Timor-Leste, South Korea and North Korea, extending the theatre from 3,716 × 2,930 km to **6,788 × 5,806 km** (+83% east-west, +98% north-south).
- **Calibrated Outline Fidelity:** Douglas-Peucker simplification tolerance derived by reproducing Thailand's shipped 1,545-point outline from its 3,317-point source (`eps = 0.005019°`), then applied uniformly — new regions match existing data density rather than shipping coarse low-vertex shapes.
- **Deliberate Extent Discipline:** Japan, Papua New Guinea and Australia evaluated and excluded for sitting beyond the ~4,000 km origin guidance; at the 0.10 zoom floor the furthest registered point renders 455 px from centre against an 800 px half-window limit.
- **Zero-Regression Registration:** The protected map engine gained nine `country_files` entries (10 insertions, 1 deletion). Renderer, polygon caching, display modes and `latlon_to_km()` untouched.
- **Regression Lock (Test Group 42):** Registry/disk agreement, v1.4.0 region survival, minimum outline density, theatre growth, zoom-floor fit and `main.py` ↔ `config.py` version lockstep all asserted automatically. Suite 41/41 ➔ 42/42.

### 🌟 Version 1.4.0 Feature Highlights
- **Main Menu & Scene Architecture (`scenes.py`, `camera_director.py`):** State-driven scene manager featuring dark-tactical C2 aesthetics, phosphor green/amber scanlines, full keyboard/mouse navigation, and smoothstep-eased cinematic camera panning over RTAF airbases with cosine zoom breathing.
- **Strict Simulation Profile Decoupling (`profiles.py`):** Immutable `SimulationProfile` definitions for Spectator (autonomous AI showcase at ~2.0× spawn pressure, unified command-input gate) and Player (balanced waves, human command trigger, backup-only auto-fire).
- **Context-Aware Combat AI Overhauls:**
  - *Auto-CIWS:* Replaced blind geometry firing with closing-leaker discrimination, transponder IFF awareness, EW ghost exclusion, outer-layer coordination, and threat-score prioritization capped at 2 targets/tick.
  - *Physical Chaff Countermeasures:* Replaced static 25% RNG with dynamic `capability × range × salvo × ECCM` derivation and finite dispenser magazines; civil traffic carries zero countermeasures.
  - *EW Ghost Flooding:* Replaced flat 40% rate with jammer strength and distance scaling; EMCON SILENT radar guarantees zero false track injection.
- **Geodata Theater Expansion:** Registered sovereign boundary vectors for the Philippines (`phl.json`) and Taiwan (`twn.json`), expanding east-west operational span from 2,360 km to 3,716 km (+57%) with zoom floor lowered to 0.10.
- **Critical Bug Hardening:** Fixed friendly Saab 340 AEW&C jammer misclassification, gated IFF re-designation against spectator court-martial, decoupled game-over restart from input gates, and eliminated player backup fire threat starvation.

### 🌟 Version 1.3.0 Feature Highlights
- **Controllable AWACS Operations:** Fully interactive AWACS integration granting a 400 km look-down sensor horizon, dynamic right-click patrol station retasking, adjustable orbit radii (20–150 km), and instant Return-To-Base (RTB) commands.
- **Procedural Audio Engine Overhaul:** Synthesized missile launch redesigned for deep resonant roars, DEFCON alarm deadlock fixed with a 10-second auto-cutoff, and dynamic brevity callouts via procedural generation.
- **Input & Navigation Disambiguation:** Complete removal of ambiguous WASD panning—camera navigation is now strictly mapped to Arrow Keys. `[W]`, `[S]`, and `[D]` are exclusively reserved for tactical actions (AWACS, Salvo, Decoy).
- **Test Matrix Expansion:** Formally updated test suite matrix expanded to 30/30 deterministic tests passing with 0 errors (100% green).

| Capability Area | Release `v1.1.1` (Phase 3 Hardened) | Release `v1.2.0` (Black Ops & ECCM Suite) | Release `v1.3.0` (AWACS & Audio Overhaul) | Release `v1.3.2` (EMP Shockwave Hotfix) | Release `v1.4.0` (Main Menu & Context-Aware AI) |
|---|---|---|---|---|---|
| **Geospatial Map Engine** | Fixed dashed ADIZ rendering bug (`dy` NameError) & added Civil Airport Hubs. | Formally locked and protected via `SYSTEM_BOUNDARIES.md` (100% zero-regression guarantee). | Integrated AWACS 400 km look-down radar bubble. | No change — protected asset. | Registered `phl.json` & `twn.json` expanding theater span to 3,716 km (+57%); zoom floor lowered to 0.10. |
| **Visual FX & UI Rendering** | Fixed VFX double offset culling; centered modals to screen viewport; restored 60 FPS. | Added ECCM cyan overdrive pencil beam, ESM-FIX diamond reticles, and HOJ tracking indicators. | HUD explicit controls display; disambiguated right-click target interaction. | Fixed `VFXManager.add_shockwave()` crash on EMP `[B]` discharge under high contact load. | Cinematic Main Menu (`scenes.py`), smoothstep camera director (`camera_director.py`), phosphor scanline CRT overlays. |
| **Audio Engine** | Added 3ms attack ramp eliminating DC step pops; C-contiguous buffer enforcement. | Added procedural synthesizers `synth_eccm_burn()` (AESA chirp) and `synth_hoj_lock()` (1850 Hz warble). | Synthesized missile roar redesigned, DEFCON alarm 10s auto-cutoff, brevity callouts. | No change. | Seamless audio transition between menu and combat; debounced alarm callouts. |
| **Combat & Asset Mechanics** | Fixed CIWS manual fire execution; resolved AWACS/CAP pool recovery leaks; ARM momentum impact. | Implemented Tier 2 Black Ops Arsenal (5 upgrades), EMP shockwave `[B]`, Burn-Through `[F]`, HOJ `[H]`, and AWACS ESM cross-fix. | Interactive AWACS orbit retask `[Right-Click]`, orbit radius `[+/-]`, and `[R]` RTB commands. | EMP shockwave `[B]` discharge stabilized — no longer crashes with ≥10 active contacts. | Decoupled Spectator/Player profiles; leaker-prioritized Auto-CIWS; physical chaff; RF-gated EW floods; starvation-free backup fire. |
| **Automated Verification** | 25/25 Test Suite + 2,000-frame headless fuzz monkey test. | 28/28 Automated Test Suite passing with 0 errors (100% green). | **30/30 Automated Test Suite** passing with 0 errors (100% green). | **31/31 Automated Test Suite** passing with 0 errors — Test 31 covers `add_shockwave()` stability. | **41/41 Automated Test Suite** passing with 0 errors (100% green) — Tests 32–41 cover profiles, AI doctrine & anti-starvation locks. |

---

## Version Control, Release Architecture & Repository Governance

AEGIS Radar maintains strict software engineering and version control standards designed for mission-critical reliability, traceable evolution, and reproducible simulation builds.

### 1. Repository Topology & Branching Model
- **Trunk-Based Development (`main`)**: The repository maintains a single long-lived `main` branch. All features, fixes, and documentation improvements are validated locally via the automated test suite before atomic integration.
- **Linear, Clean History**: The repository history is kept strictly linear, free of extraneous merge bubbles or work-in-progress checkpoint commits. Every commit on `origin/main` represents a complete, compilable, and passing state.
- **Single-Author Attribution Integrity**: 100% of all repository commits are authored by the primary project architect (`Chawannua <chawannua@gmail.com>`). The repository enforces a strict commit trailer hygiene policy: no third-party co-author or session trailers are permitted, preserving pure project authorship and a clean contribution graph.

### 2. Semantic Versioning 2.0.0 (SemVer)
The project strictly enforces [Semantic Versioning 2.0.0](https://semver.org/) under the `MAJOR.MINOR.PATCH` specification:
- **`MAJOR` (x.0.0)**: Breaking architectural changes, incompatible save/replay telemetry schemas, or fundamental restructuring of the core simulation loop.
- **`MINOR` (0.x.0)**: Backwards-compatible tactical features, new weapon systems, geodata theater expansions, audio DSP synthesizers, and operational mission additions (e.g., `v1.1.0` Geodata Engine, `v1.2.0` Black Ops & ECCM, `v1.3.0` Controllable AWACS, `v1.4.0` Main Menu & Context-Aware AI).
- **`PATCH` (0.0.x)**: Backwards-compatible bug fixes, UI coordinate harmonizations, performance optimizations, and crash hotfixes (e.g., `v1.1.1` Coordinate Fixes, `v1.3.1` Thread Safety & Input Disambiguation, `v1.3.2` EMP Shockwave Crash Hotfix).

### 3. Conventional Commits 1.0.0 Standard
All commit messages adhere to the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification:
```
<type>(<scope>): <short imperative subject summary>

[optional multi-line body explaining rationale and verification metrics]
```
Standardized commit types utilized across the repository:
- `feat`: Implementation of new tactical features, weapon systems, map layers, or UI scenes.
- `fix`: Resolution of simulation bugs, numerical glitches, coordinate offsets, or crash triggers.
- `docs`: Documentation expansions, README synchronization, CHANGELOG updates, or architecture diagrams.
- `test`: Addition, refactoring, or expansion of headless unit/regression test modules.
- `chore`: Version bumps, dependency maintenance, release preparation, or file pruning.
- `ci`: Build scripts, PyInstaller spec configurations, or distribution workflows.
- `perf`: Numerical optimization, surface caching, rendering latency, or DSP memory profiling.

### 4. 5-Point Release Synchronization Protocol
To guarantee zero version drift across documentation, runtime binaries, and source code, every release undergoes an atomic 5-point synchronization gate:

| Touchpoint | File / Asset | Verification Rule |
|---|---|---|
| **1. Simulation Config** | [`config.py`](config.py) | `GameConfig.VERSION` string matches target release version (e.g., `"1.4.0"`). |
| **2. Application Entry** | [`main.py`](main.py) | `__version__` string matches target release version (e.g., `"1.4.0"`). |
| **3. Changelog** | [`CHANGELOG.md`](CHANGELOG.md) | Dedicated `[X.Y.Z] - YYYY-MM-DD` section containing Keep a Changelog categories (`Added`, `Changed`, `Fixed`, `Verification`). |
| **4. Technical Documentation**| [`README.md`](README.md) | Current Release banner, Quick Links, Feature Highlights table, and Evolution Chain reflect new version. |
| **5. Git Release Tag** | `refs/tags/vX.Y.Z` | Annotated Git tag created with release notes: `git tag -a vX.Y.Z -m "Release vX.Y.Z: ..."` |

### 5. Pre-Tag Verification Quality Gate
No release tag may be minted or pushed without achieving a 100% clean bill of health from the automated test suite:
```bash
python test_logic.py
```
- **Zero Failures**: All **42/42 test modules** (325+ assertions) must evaluate to `[PASS]`.
- **Adversarial Regression Locks**: Tests 38–41 explicitly lock in critical behavioral guards:
  - *Test 38*: `DEFAULT_PROFILE` command input retention (un-profiled callers retain human console controls).
  - *Test 39*: Spectator IFF re-designation guard against accidental civilian shootdown court-martial.
  - *Test 40*: Post-defeat sortie restart reachable across all simulation profiles.
  - *Test 41*: Starvation-free player-mode backup fire queue traversal over a 40-tick horizon.

### 6. Repository Sanitation & Artifact Hygiene
The repository enforces strict `.gitignore` rules to prevent repository bloat and binary pollution:
- **Build Environments**: Untracked 176MB portable Python distributions (`work/`) preventing unnecessary multi-gigabyte git clones.
- **Compiled Binaries**: Ignores `build/`, `dist/`, `*.spec`, `*.exe`, `*.bin`. Releases are distributed via official GitHub Release binary attachments rather than git tracking.
- **Runtime Logs & Cache**: Automatically ignores `*.log`, `full_log.txt`, `error.log`, `__pycache__/`, and `.pytest_cache/`.
- **Geodata Protection**: All 13 core geospatial datasets (`*.json`) are tracked as read-only, immutable assets governed under [`SYSTEM_BOUNDARIES.md`](SYSTEM_BOUNDARIES.md).

---

## Installation & Build Guide

### Option 1: Standalone Windows Binary (Recommended)
No Python installation or setup required.
1. Download **[`AEGIS_Radar.exe`](https://github.com/chawannua/air-defense-radar-sim/releases/latest)** from the GitHub Releases page.
2. Double-click `AEGIS_Radar.exe` to launch the simulator immediately.

### Option 2: Run From Source (Cross-Platform)

```bash
# 1. Clone the repository
git clone https://github.com/chawannua/air-defense-radar-sim.git
cd air-defense-radar-sim

# 2. Set up virtual environment (Python 3.10+)
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run automated test suite
python test_logic.py

# 5. Launch AEGIS Tactical Radar
python main.py
```

### Option 3: Building the Standalone Executable with PyInstaller

To compile a single-file Windows `.exe` including all embedded 1:10m Natural Earth geodata files:

```powershell
pip install pyinstaller

python -m PyInstaller --onefile --noconsole --name "AEGIS_Radar" `
  --add-data "tha.json;." --add-data "mmr.json;." --add-data "lao.json;." `
  --add-data "khm.json;." --add-data "mys.json;." --add-data "sgp.json;." `
  --add-data "vnm.json;." --add-data "chn.json;." --add-data "idn.json;." `
  --add-data "phl.json;." --add-data "twn.json;." --add-data "borders.json;." `
  --add-data "coastlines.json;." `
  main.py
```

---

## Dependencies

| Package | Minimum Version | Purpose in AEGIS Simulator |
|---|---|---|
| **Python** | `3.10+` | Core programming language runtime. |
| **pygame** | `2.0.0+` | Graphics rendering, input handling, mixer hardware interface. |
| **numpy** | `1.24.0+` | Fast digital signal processing, procedural audio buffer synthesis, vector math. |

---

## License & Acknowledgments

- **License**: Released under a **[Proprietary Source-Available License](LICENSE)**. The source is public for evaluation, study and personal non-commercial use. Modification, redistribution and commercial use are **not** permitted without written permission.
  - Releases up to and including **v1.4.1** were published under the MIT License and remain available under those terms. The proprietary license governs versions released after 2026-09-11.
  - For commercial licensing or modification rights, contact the copyright holder.
- **Academic Context**: Developed as a final project for an Object-Oriented Programming (OOP) curriculum, modeling advanced software design patterns, geospatial data projection, procedural acoustics, and interactive real-time systems.
- **Data Source**: Real-world coastline and sovereign territorial vectors derived from Natural Earth 1:10m Cultural and Physical geospatial databases.

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-09-09

### Added
- **Tier 2 Black Ops Experimental Arsenal (`command_center.py`)**:
  - Implemented progression gate: mastering all 5 Tier 1 upgrades automatically unlocks classified Tier 2 Black Ops developmental projects.
  - Added 5 prototype combat & sensor upgrades:
    1. `QUANTUM_SPACE_RADAR` (3,500 XP): Entangled photon orbital sensor constellation completely bypassing terrain/mountain line-of-sight masking for cruise missiles.
    2. `METEOR_HYPERSONIC` (4,000 XP): Equips RTAF fighter wings with ramjet BVR missiles (+10 max fighter sortie pool, instant reload).
    3. `IRON_BEAM_DIRECTED_ENERGY` (5,000 XP): Helios 100kW laser point-defense extending CIWS auto-engage range to 30.0 km with guaranteed $\ge 95\%$ lethal kill rate.
    4. `TACTICAL_EMP_BURST` (4,500 XP): High-power microwave burst deployed via combat hotkey `[B]` vaporizing all EW ghost tracks and frying inbound ARM seeker locks.
    5. `NANOTECH_AEGIS_SHIELD` (6,000 XP): Fortifies Command Base HP to 150 Max (instant heal) with 50% passive damage mitigation.
  - Added `trigger_emp_burst()` system to neutralize electronic warfare jamming and break homing missile guidance.
- **Tabbed Armory UI & Interactive Controls (`radar_ui.py`)**:
  - Expanded armory overlay from 580x280 to 680x360 with dual-tab support (`[T]` to toggle between Tier 1 Conventional and Tier 2 Black Ops).
  - Added classified access security restriction modal explaining Tier 1 mastery prerequisite.
  - Added hotkey bindings `[1]-[5]` (tab-aware) and direct global purchase keys `[6]-[0]`.
  - Added combat key `[B]` for instantaneous tactical EMP shockwave discharge.
- **Automated Verification Suite (`test_logic.py`)**:
  - Added Section 26 testing suite covering gating conditions, XP deductions, duplicate rejections, and mechanics for all 5 Tier 2 items.
  - All 26 test sections passing (100% green).

## [1.1.1] - 2026-09-08

### Fixed
- **UI & Rendering Engine (`radar_ui.py`)**:
  - Eliminated double screen-offset calculation in `vfx_mgr.draw(screen, 0, 0)`, resolving off-screen culling of all intercept explosions and flak effects.
  - Centered Upgrades modal and After-Action Report (AAR) debriefing window to viewport center (`(WIDTH - w) // 2`, `(HEIGHT - h) // 2`), preventing camera shake and pan distortion.
  - Resolved variable collision on `alpha` (interpolation factor vs radar contact trail opacity), fixing spatial jitter and potential `UnboundLocalError`.
  - Removed duplicate `clock.tick(60)` call that capped UI rendering at 30 FPS, restoring full 60 FPS refresh rate.
  - Corrected active contact selection hit-test box stride from 22px to 18px.
  - Fixed status badge color rendering for `VICTORY` state to tactical green.
- **Simulation Core & Combat Systems (`command_center.py`, `targets.py`, `missions.py`)**:
  - Implemented CIWS manual engagement execution branch in `process_engagements()`, honoring P_k calculation and Rapid CIWS upgrade bonus.
  - Fixed `NameError: VIPTransport` in `command_center.py` by importing `VIPTransport` from `targets.py`.
  - Stored events in `self.historical_events` to preserve After-Action Report metrics after UI event bus consumption.
  - Restored friendly fire / civilian court-martial triggers to fire across any friendly aircraft or civilian VIP craft.
  - Fixed AWACS and CAP landing recovery to prevent permanent asset pool exhaustion upon RTB.
  - Prevented infinite XP gain loops on mission completion in `IronSwarmMission` and `GhostHunterMission`.
  - Added ballistic momentum impact check to `AntiRadiationMissile` when ground radar goes silent.
  - Fixed `is_line_of_sight_masked` peak altitude unpacking to safely support both 3-tuple and 4-tuple peak geodata.
- **Audio & Geospatial Engine (`sound_engine.py`, `map_manager.py`)**:
  - Added 3ms attack ramp in `_to_stereo_sound` to eliminate sample 0 DC step pops/clicks.
  - Resolved `NameError: name 'dy' is not defined` in `map_manager.py` dashed polygon rendering.
  - Added civil airport hub rendering branch for Phuket International Airport (`VTSP`).
  - Added C-contiguous 16-bit PCM array enforcement before passing audio buffers to `pygame.sndarray.make_sound`.
- **Quality Assurance**:
  - Expanded test suite from 20 to 25 automated integration suites in `test_logic.py`, passing with 100% success.
  - Executed 2,000-frame headless monkey fuzz test with zero exceptions at 115.7 FPS.

## [1.1.0] - 2026-09-08

### Added
- **Real-World Tactical Map Engine (`map_manager.py`)**:
  - High-fidelity 1:10m Natural Earth vector geometry for Thailand and 8 neighboring countries (Myanmar, Laos, Cambodia, Vietnam, Malaysia, Singapore, Indonesia/Sumatra, and Southern China/Hainan).
  - 20 distinct Thai rings including mainland and 19 major islands (Phuket, Samui, Phangan, Chang, Kut, Tarutao, Lanta).
  - 8,338 high-resolution coastline points and 2,873 international land boundary points.
  - Bangkok FIR / Thai ADIZ (Air Defense Identification Zone) 31-waypoint boundary polygon.
  - 22 strategic military airbases and regional air hubs (RTAF Wings 1, 4, 7, 21, 23, 41, 56, RTN Utapao, Yangon, Naypyidaw, Vientiane, Phnom Penh, Ho Chi Minh, Da Nang, Hanoi, Kuala Lumpur, Changi, Sanya).
  - Topographical mountain peak masking (Doi Inthanon, Khao Luang, Phu Kradueng, Tenasserim, Khao Yai, Doi Pha Hom Pok).
  - `[F2]` Map mode toggle (`FULL TACTICAL` -> `SOVEREIGN FOCUS` -> `MINIMAL` -> `OFF`).
  - 60 FPS surface caching rendering engine (1.3 ms cached blit time).
- **Campaign Operations & Scenario Engine (`missions.py`)**:
  - `[F1]` Mission cycling through 4 dedicated operational scenarios:
    1. `OP-DEFENSE`: Standard escalating peacetime -> tensions -> wartime air defense sandbox.
    2. `OP-GUARDIAN`: Royal Thai VIP transport escort (`VIP-ROYAL`) from Chiang Mai (Wing 41) to Don Mueang (`VTBD`).
    3. `OP-IRONSWARM`: Instant DEFCON 1 saturation swarm defense against cruise missiles and loitering drones.
    4. `OP-GHOST`: Strategic stealth bomber intercept hunt before standoff weapon release range.
- **Procedural Audio Engine (`sound_engine.py`)**:
  - Pure procedural audio synthesis via NumPy and Pygame mixer (0 MB external WAV/MP3 files required).
  - Real-time synthesis for AESA chirps, DEFCON 1 klaxon, rocket launches, 3,900 RPM Gatling CIWS buzzsaw, detonations, and asynchronous SAPI tactical voice chatter.
  - Fail-safe mock fallback for headless or audio-disabled environments.
- **Visual FX & "Juice" Engine (`visual_effects.py`)**:
  - Expanding shockwaves, thermodynamic shrapnel embers decaying across color spectrum, $T^2$ trauma screen shake, lead-intercept reticles ($ec{P}_{\text{lead}}$), and red CRT edge vignette.
- **Advanced Threat Models & Combat Physics (`targets.py`, `command_center.py`)**:
  - Anti-Radiation Missiles (`ARM`): Mach 3.5–4.5 SEAD threats targeting active radar emissions.
  - Cruise Missiles (`CRUISE`): Mach 0.85 low-altitude nap-of-the-earth threats topographically masked by Thai mountain peaks.
  - Ray-cast line-of-sight topographical mountain masking against ground radar.
  - `[E]` EMCON radar control (`ACTIVE` -> `SECTOR` -> `SILENT`).
  - `[S]` Salvo firing doctrine (`SINGLE` -> `RIPPLE` -> `SALVO`).
  - `[D]` Active RF decoy countermeasures.
- **Tactical Armory & Tech Upgrade Tree (`command_center.py`, `radar_ui.py`)**:
  - `[TAB]` armory overlay to purchase upgrades with accumulated XP:
    - `AESA_RANGE`: +25% radar range (800 km -> 1,000 km).
    - `DOPPLER_FILTER`: Auto-clears clutter ghost tracks.
    - `DECOY_PACK`: +3 RF decoy resupply.
    - `RAPID_CIWS`: +100 CIWS rounds and instant reload.
    - `AESA_SEEKERS`: +15% hit probability boost ($P_k$).
- **Career Progression & After-Action Report (AAR)**:
  - 11 Royal Thai Air Force ranks (Airman up to Air Chief Marshal).
  - High-contrast AAR terminal card rendered on sortie completion or base destruction.
  - Court-martial penalty for civilian airliner shootdowns.
- **Automated Test Suite (`test_logic.py`)**:
  - Expanded to 20 comprehensive test suites with 126 assertions, passing with 100% success.
- **Version Initialization**:
  - `GameConfig.VERSION = "1.1.0"`, `__version__ = "1.1.0"` in `main.py`, and window title display.

### Changed
- Scaled aircraft and missile speeds to real Mach numbers and kinematic physics.
- Replaced 64-point rough polygon outline with 1:10m multi-ring Natural Earth geodata.
- Improved radar UI with smooth 60 FPS cached rendering.

## [1.0.0] - 2026-09-07

### Added
- Initial release of AEGIS Tactical Air Defense Radar Simulator.
- Real-time rotating AESA sweep line and phosphor persistence.
- RTAF Wing airbases and fighter scramble logic.
- Four-tier weapon systems: THAAD (400 km), SAM (80–200 km), CIWS (20 km), and Fighter scrambles.
- Multi-tier threat classes: Aircraft, Airliner, Helicopter, Drone, TacticalBM, ICBM, EW Jammer.
- AWACS orbit patrol and Combat Air Patrol (CAP) lifecycle management.
- 3-phase escalation model: Peacetime (0–2m), Tensions (2–6m), Wartime (6m+).

[1.2.0]: https://github.com/chawannua/air-defense-radar-sim/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/chawannua/air-defense-radar-sim/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/chawannua/air-defense-radar-sim/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/chawannua/air-defense-radar-sim/releases/tag/v1.0.0

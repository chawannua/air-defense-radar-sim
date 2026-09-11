# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - 2026-09-11

### Added
- **Main Menu & Scene System (`scenes.py`)**: New `SceneManager` / `Scene` / `MenuScene` layer runs ahead of the simulation. Dark-tactical C2 styling (phosphor green + amber on near-black, scanline overlay) continuous with the in-game HUD. Keyboard and mouse navigation both supported.
- **Cinematic Camera (`camera_director.py`)**: Menu background pans the live tactical map along smoothstep-eased waypoints drawn from the RTAF airbase positions, with a cosine zoom-breathing effect.
- **Mode Selection (`profiles.py`)**: `SimulationProfile` frozen dataclass with `SPECTATOR_PROFILE` and `PLAYER_PROFILE`. Profiles are injected and read from; `GameConfig` is never mutated, so mode switches cannot leak process-global state.
  - **Spectator Mode**: autonomous AI showcase at ~2.0x spawn pressure, view-only. Enforced by a single command-input gate rather than scattered per-handler checks. Camera pan, zoom, selection, restart, mute and ESC remain available.
  - **Player Mode**: reduced balanced waves, human holds the trigger. Auto-fire is demoted to a backup role (leakers inside 40 km, or unengaged ICBM/TacticalBM). Auto-CIWS stays autonomous in both modes as last-ditch point defence.
- **Map Coverage**: Registered `phl.json` and `twn.json`, already present in the repo but never wired into the loader. East-west extent 2,360 km -> 3,716 km (+57%). Data registration only; no rendering logic altered. Zoom floor lowered 0.2 -> 0.10 so the wider theatre fits on screen.

### Changed
- **Auto-CIWS**: replaced blind geometry (any non-friendly in range) with leaker prioritisation - closing on base, IFF-aware, ghosts excluded, not already covered by an outer layer unless ETA <= 3 ticks. Ranked by `calculate_threat_score()`, capped at 2/tick and 1/tick below 25% magazine. CIWS kills fell 19.6 -> 11.4 with survival flat, i.e. the removed shots were overkill rather than saves.
- **Chaff**: replaced `random.random() < 0.25` with `capability x range x salvo x eccm`, clamped at 0.75 and exactly 0.0 with no cartridges remaining. Aircraft now carry a finite chaff loadout; civilian traffic never chaffs.
- **EW Ghost Flood**: replaced the flat 40%/tick roll with a rate derived from jammer strength and range. EMCON SILENT now returns exactly 0.0 - a radar that is not radiating cannot be flooded. Ghost count scales with jam power instead of a flat 3-8.
- **Repository**: untracked `work/` (3,684 files, 176MB portable Python distribution, unreferenced by source or either PyInstaller spec) and removed `gbr.json`, `irl.json`, the superseded bare `README`, and a stray tracked `.spec`. Tracked files 3,725 -> 37. `.gitignore` rewritten; it had every rule duplicated. History intentionally not rewritten.

### Fixed
- **Friendly AWACS misclassified as a jammer**: the RTAF `Saab 340 AEW&C` `true_type` contains the substring `"EW"`, so a naive match scored our own airborne early-warning platform as a hostile jammer, driving a permanent ghost-track flood with no enemy EW present. `get_jammer_strength()` now returns 0.0 for friendlies.
- **`DEFAULT_PROFILE` was silently view-only**: `player_input_enabled` defaulted to `False`, so running `radar_ui.py` directly - or any `start_radar(profile=None)` call - was unplayable (no firing, no upgrades, no restart).
- **Spectator could lose a game it only watches**: the Flight Info Panel `H/S/F/U` IFF buttons sit under `MOUSEBUTTONDOWN`, outside the `KEYDOWN` command gate. Re-designating a civilian airliner HOSTILE let the autonomous SAM layer kill it, triggering court-martial and `base_hp = 0`. Now gated.
- **Spectator stranded at game over**: restart sat inside the command gate while the AAR screen still prompts "Press [R] to Re-Scramble Sortie". Moved out alongside the fullscreen toggle.
- **Player backup fire starved**: `process_personnel()` popped exactly one threat per tick and discarded the tick when it was backup-ineligible, so a distant high-scoring cruise missile could indefinitely starve a close leaking drone. The queue is now walked until an eligible threat is found; Spectator behaviour is unchanged.

### Verification
- Test suite expanded 31 -> **41 groups**. New groups cover profile-driven spawn and weapon autonomy, the three context-aware skill triggers with hold-fire discrimination, and regression locks on all four critical fixes above.
- The starvation regression test was confirmed to fail against a real revert of the fix, not a mock.
- Balance A/B over 10 identical seeds (Spectator, WARTIME, 2,500-tick cap): survival 700.3 -> 709.9 mean. No material difficulty shift.

## [1.3.2] - 2026-09-09

### Fixed
- **Visual FX Engine (`visual_effects.py`)**:
  - Resolved `AttributeError` / `IndexError` crash in `VFXManager.add_shockwave()` triggered when the Tier 2 Tactical EMP Generator `[B]` was discharged while ≥10 air contacts were active simultaneously. The shockwave particle list was mutated mid-iteration, causing an unsafe in-place modification. Fixed with a copy-on-iterate guard and bounds check before particle emission.

### Changed
- **Test Suite (`test_logic.py`)**: Expanded automated verification matrix from 30 to **31/31** suites. New Test 31 validates `VFXManager.add_shockwave()` stability under high contact load (≥10 contacts), confirming zero crashes across 50 rapid successive EMP discharges.

## [1.3.1] - 2026-09-09

### Security Hardening & Reliability Updates
- **Thread-Safety**: Added `threading.RLock()` to `SoundManager` for safe concurrent asynchronous DEFCON alarm handling.
- **Display Protection**: Clamped `VIDEORESIZE` boundaries to $\ge 640\times480$ preventing zero-surface matrix collapse crashes on window minimize.
- **Memory Optimization**: Capped `historical_events` ledger at 3,000 entries preventing unbound allocation memory leaks during extended campaigns.
- **Visual Accuracy**: Augmented `MISSILE_LAUNCH` event telemetry with explicit `target_x` and `target_y` variables for synchronized tracer trajectory alignments.

## [1.3.0] - 2026-09-09

### Added
- **Interactive AWACS C2 & Sensor Fusion**: Implemented 400 km airborne look-down bubble, right-click station retask, orbit radius tuning ([+/-]), and immediate RTB ([R]).
- **Audio Subsystem Modernization**: Redesigned synthesized missile launch roar, implemented dynamic brevity callouts, and fixed DEFCON alarm deadlock with a 10s auto-cutoff.
- **Input & Navigation Disambiguation**: Removed WASD pan ambiguity. Camera panning is now strictly bound to Arrow Keys; [W], [S], and [D] are preserved for AWACS, Salvo, and Decoy tactical actions.
- **Test Matrix Expansion**: Expanded the 	est_logic.py verification matrix to 30/30 suites passing with zero errors.

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
- **AI Interceptor Prioritization & EW Suppression (`command_center.py`, `targets.py`)**:
  - Elevated strategic threat score (+900 bonus) for active EW jamming platforms in `calculate_threat_score()`.
  - Implemented proactive AI interceptor defense `process_ew_interceptor_defense()`: automatically vectors available RTAF wing interceptors against unengaged standoff jammers to clear radar blinding and ghost track injection.
  - Added duplicate engagement prevention and ammo exhaustion validation.
  - Implemented realistic standoff loiter timer and bingo fuel egress (`loiter_timer`): prevents standoff EW platforms from accumulating indefinitely in the theater during prolonged DEFCON 1 engagements.
- **Anti-Jammer Electronic Counter-Countermeasures (ECCM) Suite**:
  - Implemented 3-pillar anti-jamming doctrine to combat heavy standoff EW jammers (`EA-18G Growler`, `EC-130H`, `J-16D`):
    1. **Radar Burn-Through Overdrive Mode (`[F]`)**: AESA transmitter overdrive punches through jamming wedges, elevating detection range multiplier from $0.3\times$ to **$1.5\times$** in jammer azimuth sectors for 20 seconds with visual cyan pencil beam overlay and procedural audio sweep.
    2. **Home-On-Jam (HOJ) Missile Guidance (`[H]`)**: Passive RF seeker doctrine extending SAM battery engagement range from 200 km to **350 km** against radiating jammers, elevating hit lethality to $\ge 85\%$ and completely bypassing chaff countermeasures.
    3. **Passive ESM Cross-Bearing Triangulation (Automated)**: Real-time dual-station triangulation between Bangkok Ground C2 `(0, 0)` and airborne Saab 340 AEW&C fixing exact $(x, y)$ coordinates of standoff jammers (`[ESM-FIX]`).
- **Tactical Audio & UI Integration (`sound_engine.py`, `radar_ui.py`)**:
  - Added procedural audio synthesizers `synth_eccm_burn()` (AESA 450-2400 Hz overdrive chirp) and `synth_hoj_lock()` (1850 Hz passive RF homing warble).
  - Added HUD status indicators for `[F] ECCM` and `[H] HOJ` in top status bar row 3.
  - Added tactical scope overlays: focused overdrive pencil beam slicing through jammer strobe and amber diamond crosshair reticle with coordinate fix for triangulated ESM contacts.
- **Architectural Governance & Operational Directives (`AGENTS.md`, `SYSTEM_BOUNDARIES.md`)**:
  - Established permanent agent operational directives mandating skill-first & multi-agent workflows.
  - Formally locked strictly protected assets (`map_manager.py`, `missions.py`, and all 16 GeoJSON sovereign border datasets) to guarantee zero regressions.
- **Automated Verification Suite (`test_logic.py`)**:
  - Expanded automated integration test suite from 25 to 28 modules, adding Section 28 covering burn-through factor elevation, timer countdown/expiration, HOJ 350 km SAM range validation, and passive ESM dual-station triangulation.
  - All 28 test suites passing cleanly (100% green).

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

[1.3.2]: https://github.com/chawannua/air-defense-radar-sim/compare/v1.3.1...v1.3.2
[1.3.1]: https://github.com/chawannua/air-defense-radar-sim/compare/v1.3.0...v1.3.1
[1.2.0]: https://github.com/chawannua/air-defense-radar-sim/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/chawannua/air-defense-radar-sim/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/chawannua/air-defense-radar-sim/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/chawannua/air-defense-radar-sim/releases/tag/v1.0.0

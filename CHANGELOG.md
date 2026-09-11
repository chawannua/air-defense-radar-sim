# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.8.0] - 2026-09-12

### Fixed
- **Ballistic launches were roughly ninety an hour.** The spawn rates lived inside `detect_airspace()` as literals, and one tick is one second. Wartime ran a `0.25-0.50` per-tick hostile chance with 10% of those ballistic, so the scope saw about **90 ballistic launches every hour**, and a `BALLISTIC_RAIN` wave added 5-15 more in a single burst. The threat model now lives in `GameConfig`: `THREAT_PHASES` holds the per-phase rates, `THREAT_WEIGHTS` the relative rarity of each type, and `THREAT_MAX_PER_HOUR` a rolling one-hour ceiling that wave spawns obey too. Measured by driving `detect_airspace()` through a full simulated hour:

| Threat | Ceiling / hour | Spawned in 1 h |
|---|---|---|
| ICBM | 1 | **1** |
| TBM | 3 | **3** |
| ARM | 8 | **8** |
| CRUISE | 12 | **12** |
| HELI | 12 | **12** |
| DRONE | 40 | **40** |
| FIGHTER | 60 | **60** |

  Ballistic total: **4 an hour against ~90 before**. Every type reaches its ceiling, so the ceilings - not the underlying rates - are what the player feels; they are one dict in `config.py` and can be lowered without touching spawn code.

- **CAP fighters launched from the wrong airfields.** `CAPFighter` carried its own copy of the airbase coordinates with the latitude sign flipped, so Korat, Takhli and Ubon - all north of Bangkok - put their fighters several hundred km *south* of their real fields, over the Gulf. Home position now reads `GameConfig.wing_home()`, which reads `AIRBASES`, the same table the map draws from, so the two cannot drift apart. Verified over **600 live CAP launches** across wings 4, 7, 21 and 41: zero at a wrong field.

- **Zooming dragged the view back to Bangkok.** Screen position is `CX + x_km * zoom` where `CX` is Bangkok, so changing zoom alone magnifies about Bangkok. Panning out to Japan and scrolling slid the view home. The mouse-wheel handler now compensates the camera so the world point under the cursor stays under the cursor. Measured across a real `0.80 -> 1.25` wheel event with the view panned away: drift **0.21 km**.

### Changed
- **CAP rotates across four wings instead of two.** Only wings 4 and 7 ever flew. Stations are now listed in `GameConfig.CAP_STATIONS` - Northern (Wing 4, Takhli), Southern (Wing 7, Surat Thani), Eastern (Wing 21, Ubon) and Northwestern (Wing 41, Chiang Mai) - and each wing flies the aircraft `WING_AIRCRAFT` lists for it rather than a shared default.

### Added
- Test group 45 covers all three defects: the hourly ceilings over a full simulated hour, every CAP station spawning at its own `AIRBASES` field with northern wings north of Bangkok, CAP rotation across more than two wings, and the wheel handler repositioning the camera. Suite **44 -> 45 groups**.

## [1.7.0] - 2026-09-12

### Fixed
- **The straight edge across the map was never a map border.** v1.6.0 terminated every layer on one shared clip frame on the reasoning that "the straight edge reads as the map border rather than a stray box". It does not. A polygon straddling the frame is returned *closed along the cut* by the clipper, so the frame was being drawn as though it were coastline: `chn.json` alone carried **36.25 degrees (~3,000 km)** of perfectly straight fake border across northern China, and the theatre sat inside a visible hard rectangle. Landmasses pressed against that rectangle - Korea, the eastern archipelagos - read as crude polygons because of it, not because of their resolution. Measured medians before the fix: Korea **2.87 km**, Philippines **3.90 km**, Thailand **4.45 km** per segment. The Philippines was already finer than Thailand.

  Clip lines are now detected from the geometry rather than assumed - a perfectly axis-aligned run of vertices sitting at the extreme edge of the data, which real coastline never is. Rings touching one are split into open runs; rings clear of one are untouched and stay closed. Longest surviving axis-aligned run: **~3,000 km -> 19 km**.

- **Labels no longer smear when zoomed out.** Every label tier rendered at every scale with no culling, so at the zoom floor the theatre became an unreadable pile of overlapping text. Text is now collected into priority tiers (`LBL_HQ` through `LBL_PEAK`), gated on a minimum zoom, and collision-culled in a final pass that also lifts all text above the linework. The default 0.8 zoom is unchanged - every label, peak and contour it carried before is still drawn.

### Added
- **Japan joins the theatre as the 21st region.** v1.4.1 recorded JPN, PNG and AUS as "excluded as beyond the ~4,000 km guidance"; that guidance was already exceeded at the time (furthest point 4,611 km) and Japan is reinstated deliberately here, not by oversight. Every region was regenerated from Natural Earth 1:10m on a window of `lon 68..146, lat -11..46`, which contains the whole archipelago - Ryukyus at **24.21N** through eastern Hokkaido at **145.82E** - with no cut touching it. The old boundary at `130.9E` had been slicing Japan in half. Japan gains a country label, Tokyo and Okinawa regional hubs, and East China Sea / Philippine Sea / Sea of Japan maritime labels.

| Layer | v1.6.0 | v1.7.0 |
|---|---|---|
| `coastlines.json` | 27,639 pts | **39,410 pts** |
| `borders.json` | 7,785 pts | **9,305 pts** |
| `jpn.json` | absent | **4,390 pts** (99 rings) |
| Regions | 20 | **21** |
| Theatre span | 6,786 x 5,806 km | **8,399 x 6,294 km** |
| Cuts inside the theatre | 3 (`lon 130.9`, `lat -9.5 / 43.0`) | **1** (`lat 46.0`, trimmed) |

### Changed
- **Zoom floor 0.09 -> 0.07** (`radar_ui.py:369`). The widened window puts **5,968 km** between Bangkok and the furthest point; the old floor would have left it off screen on the narrowest supported 1024px display. The floor moved rather than the assertion, preserving the invariant test group 42 already enforced.
- **Render brought back inside the frame budget.** v1.6.0 shipped knowing the uncached render cost ~26 ms against a 16.7 ms budget, and the surface cache misses on every pan. This release adds 39% more geometry (69k -> 97k drawable points), so that was measured before anything was regenerated. Strokes are now rejected on a precomputed bounding box before a single vertex is transformed, thinned to the resolution the current zoom can resolve (`LOD_MIN_PX`), and the three hot linework passes inline the km-to-screen projection instead of calling it once per point.

| Zoom | Before | After |
|---|---|---|
| floor (0.09 -> 0.07) | 23.1 ms | **12.6 ms** |
| 0.30 | 23.4 ms | **17.9 ms** (worst case) |
| 0.80 (default) | 21.4 ms | **12.5 ms** (every vertex kept) |
| 2.00 | - | **9.3 ms** |

- `README.md` geodata figures corrected against the files actually shipped; the table had drifted to claiming 229 coastline segments against 885 present on disk.

### Review
An adversarial review pass ran against both commits before this version was cut.
It found no critical defects and verified the four highest-risk mechanisms
empirically rather than by reading - `split_ring_on_frame` property-tested over
20,000 random rings against a ground-truth segment set (zero losses, zero
duplicates, correct wrap-around), and viewport culling pixel-diffed on-versus-off
at four zooms with the camera pushed into all four quadrants (zero differing
pixels). Three real defects came out of it and are fixed here:

- **An RTAF wing was being suppressed by a decorative country name at the default
  zoom.** `WING 4 (TAKHLI)` sits 40 px from the `THAILAND` label, which is wider
  than it; with country names ranked above bases the wing was culled outright and
  scored 0.00 on a glyph match of the rendered surface. Operational labels now
  outrank decorative ones - HQ, then RTAF/RTN wings, then the sovereign label,
  then neighbouring country names. Fixing that exposed a second-order bug: the
  `SOVEREIGN AIRSPACE` subtitle then rendered with no `THAILAND` above it, so a
  label can now declare a parent and is dropped when the parent loses.
- **The level-of-detail guard checked the wrong length.** It tested the input, not
  the output, so at the zoom floor 326 country rings fell below three points and
  were drawn as open chords, and 369 coastline strokes collapsed to a single point
  and were discarded entirely - closed island loops repeat their first vertex
  last, so the "keep the final point" step never fired for one. All now zero.
- **A code comment claimed more than the code delivered.** "The default 0.8 zoom
  keeps every vertex" was false: 213 strokes thin there. The claim is corrected to
  what is true, and the test that backed it - which sampled only Thailand's
  mainland, the single most favourable stroke in the theatre - now sweeps every
  stroke at every zoom against the bound the floored stride actually guarantees.

Two hardening changes came from review nits: a clip line must now carry at least
2 degrees of accumulated run before it is believed, and cut membership is matched
within a tolerance so that an export re-rounding `46.0` to `45.99998` cannot
silently disable the trimming. One residual hazard is documented rather than
fixed: a window edge placed exactly on a real straight border is indistinguishable
from a cut, so the theatre must not be re-cut on the 141st meridian, which carries
the Indonesia-Papua New Guinea border.

### Testing
- **Suite 42 -> 44 groups.** Both defects were invisible to every existing assertion - point counts and theatre span are identical whether or not the clip frame is drawn - so the new groups guard them directly. Group 43: no clip edge may survive loading, curved and non-extremal geometry must never be flagged as a cut, a straight inland feature must pass through untouched (the Indonesia-PNG border runs dead straight along the 141st meridian and must not be mistaken for one), Japan must arrive whole, and the tiers that cause the smear must be culled at the zoom floor. Group 44: culling metadata must stay index-aligned with its geometry, every bounding box must contain its own stroke, and LOD must never thin at or above the default zoom.

## [1.6.0] - 2026-09-12

### Changed
- **Uniform map detail across the whole theatre.** v1.4.1 grew the map roughly fivefold in area but left the high-fidelity layers covering only the original Southeast Asia box, so expansion regions rendered with a single thin outline while SEA carried three overlapping layers. Every layer is now rebuilt at the density of Thailand itself - Douglas-Peucker at `eps = 0.005019`, the tolerance that reproduces `tha.json` exactly - giving **17-27 points per 100 km everywhere** against Thailand at 18.5.

| Layer | Before | After |
|---|---|---|
| `coastlines.json` | 8,338 pts (SEA box only) | **27,639 pts** (full theatre) |
| `borders.json` | 2,873 pts (SEA box only) | **7,785 pts** (full theatre) |
| `phl.json` | 110 pts | **3,608 pts** |
| `twn.json` | 9 pts | **256 pts** |
| `chn.json` | 1,830 pts, cut at lon 114 / lat 25.5 | **5,994 pts**, cut on the theatre frame |
| `idn.json` | 1,641 pts, cut at lon 114 / lat -1 | **7,816 pts**, cut on the theatre frame |
| `mys.json`, `mmr.json`, `kor.json` | cut mid-map | re-cut on the frame |

- **The mid-map rectangle is gone.** Its cause was not the renderer: `coastlines.json`, `borders.json` and five country polygons had all been clipped to a `lon 89-114, lat -1-25.5` box during the original SEA localisation, so China and Indonesia ended in open water partway across the map. Every layer now terminates on one shared frame (`lon 68.1-130.9, lat -9.5-43.0`), so the straight edge reads as the map border rather than a stray box.
- **Zoom floor 0.10 -> 0.09** (`radar_ui.py:369`). Restoring the north-east corner of China moved the furthest point to 4,611 km, rendering 461.1 px from centre against a 460.8 px half-window on a 1024px display - over by a third of a pixel. Test group 42 caught it. The floor now leaves 46 px of margin.

### Added
- **Eleven country labels** (`c_label_data`, 11 -> 22 entries): India, Bangladesh, Sri Lanka, Nepal, Bhutan, Brunei, Timor-Leste, South Korea, North Korea, Philippines and Taiwan previously rendered as unnamed landmasses.

### Fixed
- Test group 42 now **parses the zoom clamp out of `radar_ui.py`** instead of restating it. A copied constant drifts from its original; this is the same failure mode the version-lockstep guard exists to prevent.

### Known limitation
Uncached map render is **~26 ms against a 16.7 ms frame budget** (7.4 ms before the expansion). The frame is cached on position, zoom and mode, so steady state is unaffected, but panning and zooming invalidate it every frame and the camera will run at roughly 40 FPS while moving.

## [1.5.1] - 2026-09-12

### Added
- **Windows version resource (`version_info.txt`)**: the executable's Details tab was entirely blank. It now reports ProductName, FileVersion `1.5.1.0`, CompanyName, FileDescription and LegalCopyright.
- **Application icon (`aegis.ico`)**: a PPI radar-scope icon at 256/128/64/48/32/16 px, drawn from the simulation's own phosphor palette. The build previously shipped PyInstaller's default icon.
- **`THIRD_PARTY_NOTICES.md`**: attribution for the 78 native libraries bundled in the executable - pygame (LGPL-2.1), NumPy (BSD-3-Clause), the SDL2 family (zlib), FreeType (FTL), libpng, libjpeg, libogg/libopus, libwebp, PortMidi - plus PyInstaller's bootloader exception and the public-domain Natural Earth data. FreeType, libjpeg, libpng and the BSD-3 components require their notices be retained in redistributions; this was previously not done.
  - Includes the LGPL-2.1 section 6 relinking notice, offering the object files needed to relink against a modified pygame.

### Changed
- **`LICENSE` and `THIRD_PARTY_NOTICES.md` now ship inside the executable.** The spec previously collected `*.json` only, so anyone downloading just the binary received no licence terms at all - which undercuts enforcing them.
- **UPX compression disabled.** UPX-packed entry points are a well-known antivirus heuristic, and the saved megabytes are not worth the false-positive rate on an unsigned binary.

### Known limitation
The executable is **not code-signed**, so Windows SmartScreen will warn on first run. Signing requires a purchased certificate. Separately, a PyInstaller bundle can be unpacked with `pyinstxtractor` and the bytecode decompiled, so the proprietary licence adopted in v1.5.0 is not yet backed by any technical measure.

## [1.5.0] - 2026-09-12

### Changed
- **License: MIT -> Proprietary Source-Available.** The source stays publicly viewable and downloadable for personal, non-commercial evaluation and study. Modification, derivative works, redistribution and commercial use now require written permission from the copyright holder.
  - **Not retroactive.** Releases up to and including v1.4.1 were published under the MIT License and remain available under those terms in perpetuity. Section 3(b) of the new license states this explicitly so the record is unambiguous.
  - Third-party components keep their own licensing (pygame LGPL-2.1, NumPy BSD-3-Clause, SDL2 and friends zlib, FreeType FTL). LGPL permits proprietary applications that link pygame, so the relicense creates no conflict. Geographic outline data remains public-domain Natural Earth.
  - `CONTRIBUTING.md` no longer solicits outside contributions, which would have contradicted the new terms. Its architecture, physics, geodata and audio documentation is retained as internal reference.
  - The repository remains public, so GitHub's Terms of Service continue to permit any user to view and fork it irrespective of these terms. Only making the repository private would prevent that.

### Note on versioning
No code behaviour changed in this release; the simulation is byte-for-byte equivalent to v1.4.1. The MINOR bump marks the licensing change, which materially alters what recipients may do with the software. A case exists for treating a relicense as MAJOR; 1.5.0 was chosen by the project owner.

## [1.4.1] - 2026-09-11

### Added
- **Geodata Theatre Expansion**: Registered nine new sovereign outlines sourced from Natural Earth 1:10m admin-0 - India (`ind.json`), Bangladesh (`bgd.json`), Sri Lanka (`lka.json`), Nepal (`npl.json`), Bhutan (`btn.json`), Brunei (`brn.json`), Timor-Leste (`tls.json`), South Korea (`kor.json`) and North Korea (`prk.json`). Theatre extent grows from 3,716 x 2,930 km to **6,788 x 5,806 km** (+83% east-west, +98% north-south); registered regions 11 -> 20.
  - Outline fidelity is calibrated against the existing `tha.json` rather than guessed: Douglas-Peucker simplification at `eps = 0.005019` deg reproduces Thailand's shipped 1,545 points from the 3,317-point source, and the same tolerance is applied to every new region. No blocky low-vertex outlines of the kind `twn.json` (9 points) shipped with. Rings that simplification collapses to zero enclosed area are discarded rather than left to draw sub-pixel hairlines.
  - Japan, Papua New Guinea and Australia were evaluated and **deliberately excluded**: Japan's north-east extremity (145.341, 44.346) sits 5,912 km from the Bangkok origin, well past the ~4,000 km guidance, and would stretch the theatre far enough that it no longer reads at a usable zoom.
  - Registration only - the `country_files` dict gained nine entries (10 insertions, 1 deletion). The renderer, polygon caching, display modes and `latlon_to_km()` are untouched.
- **Test group 42 - Geodata Theatre Registration & Fidelity**: Locks in the expansion against regression. Asserts the registry and on-disk files agree, every registered region loads at least one >=3-point ring, all 11 v1.4.0 regions survive, all 9 new regions load, new outlines carry >=80 points, the theatre exceeds the v1.4.0 baseline, the furthest point still lands on screen at the 0.10 zoom floor (4,552 km -> 455 px against an 800 px limit), and `GameConfig.VERSION` stays in lockstep with `main.py.__version__`. Suite 41 -> 42 groups.

### Changed
- **Version**: `main.py.__version__` and `GameConfig.VERSION` bumped 1.4.0 -> 1.4.1 in lockstep, now enforced by test group 42 rather than convention. These two strings drifted apart once before (`main.py` at 1.3.1 while `config.py` said 1.3.2).

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

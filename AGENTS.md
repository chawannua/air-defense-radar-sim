# Project Boundaries & Modification Rules

> Reference for anyone or anything modifying this repository, automated tooling included.
> Read this before changing files. The rules exist to keep the geospatial map engine and
> campaign scenarios regression-free; they have been earned through actual breakage.

---

## 1. Protected files — do not modify

These files are load-bearing and must not be edited, refactored, reformatted or
overwritten without an explicit, recorded decision. If a change genuinely requires
touching one, say so in the commit message and state why no alternative existed.

| File / pattern | Why it is protected |
|---|---|
| `map_manager.py` | Natural Earth tactical map engine — 1:10m vector polygons, coastline caching, airbase coordinates, mountain peaks, display modes. The renderer, polygon caching, display modes and `latlon_to_km()` are the parts that matter. Registering a new region in `country_files` is a recognised exception; see §2. |
| `tha.json` | 1,545-point polygon for the Kingdom of Thailand sovereign border. |
| `coastlines.json` | 8,338-point Gulf of Thailand, Andaman Sea and Indian Ocean coastlines. |
| `borders.json` | International land boundaries of Southeast Asia. |
| `mmr.json`, `lao.json`, `khm.json`, `vnm.json`, `mys.json`, `sgp.json`, `idn.json`, `chn.json`, `phl.json`, `twn.json`, `ind.json`, `bgd.json`, `lka.json`, `npl.json`, `btn.json`, `brn.json`, `tls.json`, `kor.json`, `prk.json` | Sovereign boundary vectors for the 20 registered regions. |
| `missions.py` | Base campaign scenarios (`OP-DEFENSE`, `OP-GUARDIAN`, `OP-IRONSWARM`, `OP-GHOST`). |
| `AEGIS_Radar.spec`, `AEGIS_Radar_debug.spec` | PyInstaller deployment packaging. Changes here alter what ships to users — icon, version resource, bundled licence files, compression. Edit only for a deliberate packaging change, and record it. |

## 2. Recognised exception: registering a new map region

The country loader lives inside the protected `map_manager.py`, so adding a region
requires touching it. The loader is fully generic — it iterates `country_files`,
projects each ring through `latlon_to_km()` and stores the result. Adding a dictionary
entry is therefore a data-registration change, not an engine change.

Adding entries to `country_files` is permitted. Changing anything else in that file
is not. State in the commit message that the change was registration-only.

## 3. Freely editable

| File | Scope of work |
|---|---|
| `command_center.py` | Simulation tick, air defence doctrine, weapon kinematics, upgrade trees, ECCM logic, event bus. |
| `targets.py` | Target classes, EW capabilities, RCS characteristics, ESM telemetry attributes. |
| `radar_ui.py` | PPI scope rendering, HUD overlays, status bars, keybindings, visual effects. |
| `sound_engine.py` | Procedural NumPy audio synthesis, sound effects, radio chatter, alarms. |
| `visual_effects.py` | Particle systems, flak detonations, lead reticles, screen trauma, contrails. |
| `scenes.py`, `camera_director.py`, `profiles.py` | Menu, scene management, cinematic camera, simulation profiles. |
| `config.py` | Balance constants, weapon parameters, probabilities, colour themes. |
| `test_logic.py` | Test suite. Append new groups only — never weaken or delete an existing test. |
| `README.md`, `CHANGELOG.md`, `DEVELOPMENT.md` | Documentation and version history. |

---

## 4. Electronic Counter-Countermeasures (ECCM) architecture

Countering standoff jammers (`EA-18G Growler`, `EC-130H Compass Call`, `J-16D`) follows a
three-pillar doctrine:

1. **Radar burn-through (`[F]`)** — transmitter overdrive focuses AESA energy into the
   jamming strobe, raising the range multiplier from 0.3x to **1.5x** in that azimuth
   sector, on a 20-second capacitor cycle with automatic cooldown.
2. **Home-on-jam missile guidance (`[H]`)** — missiles switch from active monopulse
   homing to passive angle-on-jam tracking, extending SAM range from 200 km to **350 km**
   against radiating jammers, with >=85% Pk, bypassing chaff.
3. **Passive ESM cross-bearing (automatic)** — with the Saab 340 AEW&C airborne,
   dual-station bearings from Bangkok HQ `(0, 0)` and the AWACS fix the jammer's exact
   position, setting `is_esm_triangulated` and drawing `[ESM-FIX]` crosshairs.

---

## 5. Verification standard

- Run `python test_logic.py` after any change. All **42 groups** must pass with zero errors.
- Version strings in `main.py` (`__version__`) and `config.py` (`GameConfig.VERSION`) must
  always agree. Test group 42 enforces this; it is not left to convention.
- A green test suite is necessary, not sufficient. Several defects have shipped past green
  tests and were only caught by reading the diff. Inspect what actually changed.
- Headless checks cannot tell you whether the map looks right. Launch `python main.py` and
  look at it before releasing a change that touches rendering or geodata.

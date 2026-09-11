# Project Operational Directives & System Boundaries

> **Notice to AI Agents & Developers**:
> This document specifies strict architectural rules, immutable components, permitted modification boundaries, and workflows for this repository.
> All autonomous agents operating in this workspace must adhere to these directives without exception.

---

## 1. Core Directives

### DIRECTIVE 1: Agent Manager Role & Multi-Agent Delegation
- **Lead Agent is an Agent Manager**: You are an orchestrator and project manager. Do not perform monolithic, end-to-end tasks alone when they can be delegated to specialized subagents.
- **Always Use Multiple Subagents**: Break down complex tasks and deploy specialized subagents (`TDD Architect`, `Core Engineer`, `UI Specialist`, `Quality Auditor`, `Sound Designer`) using `invoke_subagent`.
- **Always Use Skills**: Evaluate and load domain skills (such as `tdd-workflows-tdd-cycle`, `debugger`, `test-automator`) before executing coding workflows. Follow the **Red-Green-Refactor** TDD cycle.
- **Dynamic Model Tiering & Token Conservation**: You are explicitly authorized to use any model tier (`flash_lite`, `flash`, `pro`, `inherit`) when managing tokens or when context tokens run low. Use `flash_lite` / `flash` for research, file reading, and test runs; reserve `pro` / `inherit` for deep reasoning and multi-file architecture refactoring.

### DIRECTIVE 2: Strictly Protected / Immutable Files (DO NOT MODIFY)
The following files are **strictly protected** to guarantee zero regressions in geospatial mapping, geopolitical borders, and base campaign scenarios:

| Protected File / Pattern | Description & Rationale |
|---|---|
| `map_manager.py` | **CRITICAL**: Restored v1.1.0 Natural Earth tactical map engine, 1:10m vector polygons, coastline caching, airbase coordinates, mountain peaks, and display modes. Must NEVER be edited, refactored, or overwritten. |
| `tha.json` | High-fidelity 1,545-point polygon for the Kingdom of Thailand sovereign border. |
| `coastlines.json` | Natural Earth 8,338-point Gulf of Thailand, Andaman Sea, and Indian Ocean coastlines. |
| `borders.json` | International land boundaries of Southeast Asia. |
| `adiz.json` | Bangkok FIR / Thai Air Defense Identification Zone boundaries. |
| `mmr.json`, `lao.json`, `khm.json`, `vnm.json`, `mys.json`, `sgp.json`, `idn.json`, `chn.json`, `phl.json`, `twn.json`, `gbr.json`, `irl.json` | Sovereign international boundaries for regional and reference nations. |
| `missions.py` | Base campaign mission scenarios (`OP-DEFENSE`, `OP-GUARDIAN`, `OP-IRONSWARM`, `OP-GHOST`). |
| `AEGIS_Radar.spec`, `AEGIS_Radar_debug.spec` | PyInstaller deployment packaging specifications. |

### DIRECTIVE 3: Permitted & Extensible Files
Modifications are explicitly allowed and encouraged within these tactical subsystems:

| Permitted File | Permitted Scope of Work |
|---|---|
| `command_center.py` | Simulation tick updates, air defense doctrine, weapon kinematics, upgrade trees, ECCM logic, event bus. |
| `targets.py` | Target classes, EW capabilities, RCS characteristics, ESM cross-bearing telemetry attributes. |
| `radar_ui.py` | Tactical PPI scope rendering, HUD overlays, status bars, weapon override keybindings, visual effects. |
| `sound_engine.py` | Procedural NumPy audio synthesizer, tactical sound effects, radio chatter, alarm loops. |
| `visual_effects.py` | Particle systems, flak detonations, lead reticles, screen trauma, missile contrails. |
| `config.py` | Balance constants, weapon parameters, combat probabilities, color themes. |
| `test_logic.py` | Automated test suites and regression verification. |
| `README.md`, `CHANGELOG.md` | User documentation, tactical field manual, keybindings list, and version history. |

---

## 2. Electronic Counter-Countermeasures (ECCM) Architecture

When countering Electronic Warfare (EW) standoff jammers (`EA-18G Growler`, `EC-130H Compass Call`, `J-16D`), the system adheres to a 3-pillar doctrine:

1. **Radar Burn-Through Mode (`[F]`)**:
   - Transmitter overdrive focuses AESA RF energy into the jamming strobe.
   - Increases radar range multiplier from $0.3\times$ to **$1.5\times$** in the jammer's azimuth sector.
   - Operates on a 20-second overdrive capacitor cycle with automatic cooldown.

2. **Home-On-Jam (HOJ) Missile Guidance (`[H]`)**:
   - Missiles switch from active monopulse radar homing to passive angle-on-jam tracking.
   - Extends SAM maximum engagement range from 200 km to **350 km** against radiating jammers.
   - Grants $\ge 85\%$ $P_k$ lethality and bypasses aircraft chaff decoys.

3. **Passive ESM Cross-Bearing Triangulation (Automated)**:
   - When **Saab 340 AEW&C** is airborne, dual-station cross-bearing fixes between Bangkok HQ `(0, 0)` and the AWACS calculate the exact `(x, y)` coordinates of standoff jammers.
   - Sets `is_esm_triangulated = True` and displays `[ESM-FIX]` diamond crosshairs on the radar scope.

---

## 3. Testing & Verification Standard
- Run `python test_logic.py` after any change.
- All 41 test suites must pass cleanly (`0` errors, `100% OK`).

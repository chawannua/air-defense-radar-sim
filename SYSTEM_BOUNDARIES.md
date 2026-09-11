# Tactical Air Defense Simulator - System Boundaries & Modification Governance

> **Reference Document for Developers**  
> **Status**: ACTIVE & ENFORCED  
> **Last Updated**: 2026-09-09

This document explicitly defines which files are **strictly protected** (immutable) and which files are **permitted for modification**, ensuring that the real-world high-fidelity Natural Earth map geometry restored from v1.1.0 and core missions remain intact.

---

## 1. Strictly Protected Components (IMMUTABLE)

Under no circumstances should refactoring or code-generation tooling alter, delete, or rewrite any part of the following files:

```
[STRICTLY PROTECTED - DO NOT TOUCH]
├── map_manager.py        <-- 1:10m Natural Earth map engine, 15+ airbases, mountain peaks, display modes
├── tha.json              <-- 1,545-point high-resolution Thailand sovereign border
├── coastlines.json       <-- 8,338-point Natural Earth coastlines (Gulf of Thailand & Andaman Sea)
├── borders.json          <-- Southeast Asian international land boundaries
├── adiz.json             <-- Bangkok FIR / Thai Air Defense Identification Zone
├── mmr.json              <-- Myanmar sovereign boundary
├── lao.json              <-- Laos sovereign boundary
├── khm.json              <-- Cambodia sovereign boundary
├── vnm.json              <-- Vietnam sovereign boundary
├── mys.json              <-- Malaysia sovereign boundary
├── sgp.json              <-- Singapore sovereign boundary
├── idn.json              <-- Indonesia sovereign boundary
├── chn.json              <-- China sovereign boundary
├── phl.json              <-- Philippines sovereign boundary
├── twn.json              <-- Taiwan sovereign boundary
├── gbr.json              <-- United Kingdom sovereign boundary
├── irl.json              <-- Ireland sovereign boundary
├── missions.py           <-- Campaign missions (OP-DEFENSE, OP-GUARDIAN, etc.)
├── AEGIS_Radar.spec      <-- PyInstaller build specification
└── AEGIS_Radar_debug.spec<-- PyInstaller debug build specification
```

### Protection Rationale:
- **`map_manager.py` & GeoJSON Data**: Delivers the genuine sovereign geography of Thailand and neighboring nations. Changing coordinates or simplifying algorithms degrades visual fidelity and causes map drift.
- **`missions.py`**: Ensures consistent challenge scenarios and scripted triggers across gameplay sessions.

---

## 2. Permitted Components (EXTENSIBLE)

Modifications, feature expansions, and bug fixes are fully permitted within the following files:

```
[PERMITTED FOR MODIFICATION]
├── command_center.py     <-- Game loop, combat calculations, weapons, upgrade trees, ECCM logic
├── targets.py            <-- Target flight dynamics, EW jamming attributes, ESM fix telemetry
├── radar_ui.py           <-- PPI radar scope drawing, HUD badges, keybindings, flight info panels
├── sound_engine.py       <-- Procedural NumPy audio synthesizer, sound effects, voice chatter
├── visual_effects.py     <-- VFX, explosions, flak particles, lead reticles, screen trauma
├── config.py             <-- Gameplay constants, speed multipliers, weapon ammo, hit chances
├── test_logic.py         <-- TDD regression test suite (All 28 sections must pass)
├── README.md             <-- Documentation, quickstart guide, keybindings reference
└── CHANGELOG.md          <-- Release history and feature notes
```

---

## 3. Anti-Jammer ECCM 3-Pillar Architecture

The 3 anti-jammer Electronic Counter-Countermeasures are implemented across the permitted files:

| Pillar | Control | File(s) | Functionality |
|---|---|---|---|
| **1. Radar Burn-Through** | **`[F]`** | `command_center.py`<br>`radar_ui.py`<br>`sound_engine.py` | Overdrives AESA transmitter power for 20s. Boosts radar detection multiplier from $0.3\times$ to $1.5\times$ inside jamming strobes, cutting through the noise wedge. |
| **2. Home-On-Jam (HOJ)** | **`[H]`** | `command_center.py`<br>`radar_ui.py`<br>`sound_engine.py` | Switches missile guidance to passive RF angle-on-jam homing. Extends SAM range from 200 km to **350 km** against radiating jammers, elevates $P_k \ge 85\%$, and bypasses chaff decoys. |
| **3. Passive ESM Triangulation** | **Automated** | `command_center.py`<br>`targets.py`<br>`radar_ui.py` | When Saab 340 AEW&C is airborne, cross-bearing triangulation between ground C2 and AWACS calculates the exact $(x, y)$ coordinates of standoff jammers (`[ESM-FIX]`). |

---

## 4. Verification Standard
- Always run `python test_logic.py` before and after changes.
- Zero regressions allowed across all 41 test suites.

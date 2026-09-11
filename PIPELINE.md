# Work Pipeline — Handoff Instructions

> Purpose: lets any operator or agent resume work on this repository with no prior
> conversation context. Read this top to bottom before making changes.
> Update the **Status** and **History** sections when you finish a task.

---

## Current State (as of v1.4.0)

| Item | Value |
|---|---|
| Version | `1.4.0` — `main.py:2` (`__version__`) and `config.py:3` (`GameConfig.VERSION`) must always agree |
| Branch | `main`, trunk-based, linear history |
| Test suite | `python test_logic.py` → **41 groups**, must print `ALL TESTS PASSED` |
| Entry point | `python main.py` → menu → mode select → `start_radar(profile=...)` |
| Map coverage | 11 countries, extent x `-900..2815 km`, y `-1632..1299 km` |

### Architecture notes that are easy to get wrong

- `start_radar()` (`radar_ui.py:57`) is a ~980-line monolith. **Do not restructure it.**
  The scene layer runs *before* it; it only gained a `profile=None` kwarg.
- Simulation ticks at **1 Hz**. `tick_count` is incremented by `radar_ui.py`, *not* by
  `CommandCenter`. Spawn/phase logic lives in `detect_airspace()`, **not** `update_world()`.
- New contacts land in `self.unseen_contacts` and only move to `self.contacts` once detected.
- `SimulationProfile` (`profiles.py`) must **never** mutate `GameConfig` class attributes.
  `GameConfig` is the default source, read from only. A test asserts this.
- Weapon prep times are 10–20 ticks. **Any engagement test with a horizon under ~40 ticks
  will read as a false zero** and look like a bug that isn't there.
- `distance_km` is a constructor arg on the `AirContact` base, but subclasses like `Drone`
  take only `track_number`. Construct first, then assign `.distance_km` directly.
  Setting `x_km`/`y_km` does **not** recompute it.

---

## NEXT TASK — Expand the map, then release v1.4.1

### Goal
Increase the geographic coverage of the tactical map beyond the current
3,716 × 2,930 km theatre, then verify, commit and release as **v1.4.1**.

### Blocker you must resolve first

`AGENTS.md` DIRECTIVE 2 lists `map_manager.py` as **strictly protected — must NEVER be
edited**. But the country loader lives inside it:

```python
# map_manager.py, in load_all_data()
country_files = { "THA": "tha.json", ..., "PHL": "phl.json", "TWN": "twn.json" }
```

Registering new regions requires touching that dict. Pick one and state which you chose
in the commit message:

1. **Minimal edit (recommended)** — add entries to `country_files` only. The loader is
   already fully generic: it iterates the dict, projects lat/lon → km via
   `latlon_to_km()`, and stores into `self.country_polys[iso]`. Only `"THA"` is
   special-cased (sovereign highlight). No rendering logic changes. This is how PHL and
   TWN were added in v1.4.0.
2. **External manifest** — move the mapping to a `map_regions.json` the loader reads, so
   future regions need no code edit. Costs one structural change to the protected file now,
   avoids all future ones.

Do **not** refactor the renderer, the caching, the display modes, or `latlon_to_km()`.
Those are the protected parts that matter.

### There is no unused data left

All 11 country files are registered. `gbr.json` / `irl.json` were removed in v1.4.0 as
irrelevant (UK/Ireland, left over from before the project was localised to SEA).
**Expanding coverage requires acquiring new outline data.**

### Data format (match exactly)

Each country file is a JSON **array of rings**; each ring is an array of `[lon, lat]`
pairs in decimal degrees, WGS84. Rings with fewer than 3 points are skipped by the loader.

```json
[[[121.777818, 24.394274], [121.175632, 22.790857], ...], ...]
```

Source used for existing data: **Natural Earth 1:10m** admin-0 country polygons.
Keep new files at comparable fidelity — `tha.json` is ~30 KB / 1,545 points, whereas
`twn.json` is only 225 bytes. Very coarse outlines render as blocky shapes and look
worse than omitting the country.

### Suggested regions (in rough order of tactical relevance)

India, Bangladesh, Sri Lanka, Japan, South Korea, North Korea, Brunei, Timor-Leste,
Papua New Guinea, Australia (northern coast), Nepal, Bhutan.

Caution: adding very distant land (e.g. all of Australia) pushes the extent far enough
that the theatre no longer reads at a usable zoom. Prefer regions within roughly
4,000 km of the Bangkok origin (`RADAR_LAT 13.7563`, `RADAR_LON 100.5018`).

### Zoom floor

`radar_ui.py:367` clamps zoom to `max(0.10, min(10.0, zoom_level))`. The floor was lowered
from `0.2` to `0.10` in v1.4.0 so the wider theatre fits. If the extent grows substantially
again, verify the furthest point still fits on screen:
`furthest_km × zoom_floor` must be **less than** half the window width in pixels.

---

## Verification — all must pass before committing

```bash
# 1. Test suite — must print ALL TESTS PASSED
python test_logic.py

# 2. Map loads every region and extent actually grew
python -c "
import os; os.environ['SDL_VIDEODRIVER']='dummy'
import pygame; pygame.init(); pygame.display.set_mode((800,600))
from map_manager import MapManager
m=MapManager(); xs=[];ys=[]
for r in m.country_polys.values():
    for ring in r: xs+=[p[0] for p in ring]; ys+=[p[1] for p in ring]
print('regions:', len(m.country_polys), sorted(m.country_polys))
print(f'x span {max(xs)-min(xs):.0f} km, y span {max(ys)-min(ys):.0f} km')"

# 3. Renders without error at the zoom floor and at default zoom
python -c "
import os; os.environ['SDL_VIDEODRIVER']='dummy'
import pygame; pygame.init(); s=pygame.display.set_mode((1600,900))
from map_manager import MapManager
m=MapManager(); f=pygame.font.SysFont('consolas',12)
for z in (0.10,0.8,3.0): s.fill((0,0,0)); m.render(s,800,450,z,1600,900,f,f,f)
print('render OK')"

# 4. Launch and look at it. Headless checks cannot tell you whether it looks right.
python main.py
```

Baseline to beat: **11 regions, x span 3,716 km, y span 2,930 km.**

---

## Release procedure for v1.4.1

1. Bump **both** version strings — `main.py:2` and `config.py:3`. They must match; they
   drifted once before (`main.py` sat at 1.3.1 while `config.py` said 1.3.2).
2. Add a `## [1.4.1] - <date>` entry to `CHANGELOG.md` (Keep a Changelog format, newest
   on top, above the `[1.4.0]` heading).
3. Update `README.md` **current-state** references only:
   - line ~16 current-release banner
   - the changelog link and the `Verification (N/N)` badge — count actual test groups with
     `python test_logic.py | grep -cE "^=== [0-9]+\."`, do not guess
   - the release-history heading and version-evolution chain
   Leave historical version mentions intact — they document past releases.
4. Commit with a Conventional Commits message (`feat:` / `fix:` / `chore(release):`).
5. `git push origin main`.
6. Tagging is **manual** — the auto-tagging CI workflow was deliberately removed in v1.3.3
   because it tagged every push, including commits that changed no shippable code.

### SemVer note
Adding map coverage is arguably a **feature** (MINOR → 1.5.0) rather than a patch.
`1.4.1` was explicitly requested by the project owner; use it, but flag the discrepancy
if the change turns out larger than data registration.

---

## Hard rules

- **No third-party assistant attribution anywhere.** Not in commit messages, PR
  descriptions, code comments, or documentation — and **not inside a policy that forbids
  them either**, since writing the names out reproduces the very thing being banned. This
  has already cost one history rewrite plus a follow-up README fix. Before claiming the
  repo is clean, grep the *current* tree across `git ls-files` for the assistant and
  vendor names in question (case-insensitive) and confirm zero matches. Re-grep if the
  tree has moved — other tooling also writes to this repository.
- **Never weaken or delete an existing test.** Append new groups only.
- **Verify, do not assume.** Run the suite and inspect diffs; a passing report from a
  delegated task is a claim, not proof. Several defects in v1.4.0 were found only by an
  adversarial review pass after the tests were already green.
- `work/` is a 176 MB local build environment. It is gitignored and must stay untracked.

---

## Known open items (not blocking v1.4.1)

From the v1.4.0 adversarial review — none can lose a game, all still open:

| Severity | Location | Issue |
|---|---|---|
| WARNING | `command_center.py` CIWS ranking | `calculate_threat_score()` returns a flat 50 for `UNIDENTIFIED`/`IDENTIFYING`, so a close un-IDed leaker can lose its slot to a further identified one |
| WARNING | `command_center.py` jammer detection | Naive `"EW" in ...` substring match misses hostile platforms named "A-50 Mainstay AWACS" / "KJ-500 AWACS". Wants an explicit `is_ew` flag set at construction |
| WARNING | `radar_ui.py` panel + `command_center.py` | Re-designating a friendly AWACS to `"U"` can scramble interceptors at our own AEW&C |
| NIT | `command_center.py` chaff | `chaff_remaining` decrements only on success, so attempts are unbounded |
| NIT | `command_center.py` CIWS | `get_eta()` returns 999 for `speed_mach == 0`, permanently holding fire on zero-speed contacts under a SAM |
| NIT | `scenes.py` | `VIDEORESIZE` updates width/height but never re-calls `pygame.display.set_mode` |
| NIT | `scenes.py` | `MenuScene` constructs a second `MapManager`, re-parsing every country JSON already loaded at import |

Test coverage gap: the suite is UI-free. No test exercises the Spectator input gate over
*mouse* paths. Three of four critical defects in v1.4.0 lived in paths no test touched.

---

## History

| Version | Summary |
|---|---|
| v1.4.0 | Main menu + cinematic camera, Spectator/Player mode separation, context-aware skill triggers (CIWS / chaff / EW flood), map extended to PHL + TWN (+57% east-west), repo cleanup 3,725 → 37 tracked files, suite 31 → 41 groups |
| v1.4.1 | *(pending — map expansion, this document's next task)* |

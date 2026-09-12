# Work Pipeline — Handoff Instructions

> Purpose: lets anyone resume work on this repository with no prior context.
> Read this top to bottom before making changes, and update the **Current State**
> and **History** sections when you finish a task.
>
> **This file holds current state only** — what shipped last, what is next, which defects
> are open. The durable rules (protected files, permitted scope, verification standard)
> live in [`AGENTS.md`](AGENTS.md) and must not be restated here. Keeping rules in one
> place is deliberate: a second copy previously drifted and began contradicting the first.

---

## Current State (as of v1.8.0)

| Item | Value |
|---|---|
| Version | `1.8.0` — `main.py:2` (`__version__`) and `config.py:3` (`GameConfig.VERSION`) must always agree; **test group 42 now enforces this**, it is no longer convention |
| Branch | `main`, trunk-based, linear history |
| Test suite | `python test_logic.py` → **46 groups**, must print `ALL TESTS PASSED` |
| Entry point | `python main.py` → menu → mode select → `start_radar(profile=...)` |
| Map coverage | 21 countries on the window `lon 68-146, lat -11-46`; x span `8,399 km`, y span `6,294 km`, furthest `5,968 km`; 97k drawable points. Only `lat 46.0` cuts the theatre and the loader trims it, so no clip edge is ever drawn |

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

## NEXT TASK — pick one; none is blocking

v1.4.1 shipped the map expansion. Candidates for the next unit of work, roughly by value:

### 1. Label the nine new regions (needs the same authorization call as v1.4.1)
`country_labels` is built from `c_label_data` in `map_manager.py:250-253`, which still lists
only the pre-v1.4.0 set. India, Korea, Bangladesh and the rest therefore **render as unlabelled
landmasses**. Fixing this means touching the protected file again. v1.4.1 used PIPELINE option 1
(minimal edit, `country_files` only) and deliberately did **not** extend that licence to the
label table — decide explicitly before editing, and say which option you chose in the commit.
The module docstring (`map_manager.py:4-5`) is likewise still pre-v1.4.0 and lists the old set.

### 2. Re-cut the two coarse outlines
`twn.json` is 9 points and `phl.json` 110, against 1,545 for `tha.json`. Both render visibly
blockier than their neighbours now that high-fidelity outlines sit beside them. Both are listed
as protected in `AGENTS.md` DIRECTIVE 2, so this needs the same explicit decision as above.
The v1.4.1 converter method reproduces `tha.json` fidelity exactly and can regenerate them:
Douglas-Peucker at `eps = 0.005019` deg over Natural Earth 1:10m admin-0.

### 3. Close the v1.4.0 open items
The seven WARNING/NIT findings listed below are all still open.

### 4. Cover the UI input paths
The suite is still UI-free. Three of four critical v1.4.0 defects lived in paths no test touches,
and no test exercises the Spectator input gate over *mouse* paths.

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
  passing report is a claim, not proof. Several defects in v1.4.0 were found only by a
  line-by-line review pass after the tests were already green.
- `work/` is a 176 MB local build environment. It is gitignored and must stay untracked.

---

## Known open items (not blocking v1.4.1)

From the v1.4.0 review pass — none can lose a game, all still open:

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
| v1.8.0 | Spawn rates left `detect_airspace()` for `GameConfig`: `THREAT_PHASES` (per-phase rates), `THREAT_WEIGHTS` (relative rarity) and a rolling `THREAT_MAX_PER_HOUR` ceiling that wave spawns obey. Ballistic launches ~90/hour -> 4/hour measured over a full simulated hour. `CAPFighter` no longer carries a private, latitude-flipped copy of the airbase table - home reads `GameConfig.wing_home()` off `AIRBASES`; CAP rotates across the four `CAP_STATIONS` wings instead of two. Mouse wheel anchors zoom on the cursor (exactly; residual is sub-pixel integer truncation) instead of magnifying about Bangkok. Ceilings scale per profile via `SimulationProfile.threat_ceiling_scale` (Player 0.5, Spectator 1.5), resolved once per CommandCenter. Waves are drawn before they are announced - the review found 73% of waves logging BATTLE STATIONS and spawning nothing once the ceilings bound. ARM weight 8 -> 5, ceiling 8 -> 3. Suite 44 -> 46 groups |
| v1.7.0 | Clip edges were being drawn as coastline (chn.json alone ~3,000 km of fake straight border, plus a hard frame round the theatre); cuts are now detected from the geometry and trimmed. Labels tiered, zoom-gated and collision-culled. Theatre re-cut to `lon 68-146, lat -11-46` adding JPN whole, reversing the v1.4.1 ~4,000 km exclusion; zoom floor 0.09 -> 0.07. Render 23.4 -> 17.9 ms worst case on 39% more geometry via bbox culling, LOD and an inlined projection. Suite 42 -> 44 groups |
| v1.4.0 | Main menu + cinematic camera, Spectator/Player mode separation, context-aware skill triggers (CIWS / chaff / EW flood), map extended to PHL + TWN (+57% east-west), repo cleanup 3,725 → 37 tracked files, suite 31 → 41 groups |
| v1.6.0 | Uniform theatre detail: coastlines 8,338 -> 27,639 pts, borders 2,873 -> 7,785, PHL 110 -> 3,608, TWN 9 -> 256; chn/idn/mys/mmr/kor re-cut from the old SEA box onto the shared frame, removing the mid-map rectangle; 11 region labels; zoom floor 0.10 -> 0.09. Uncached render ~26 ms vs 16.7 ms budget |
| v1.5.1 | Packaging hardened: Windows version resource, radar-scope icon, THIRD_PARTY_NOTICES.md for 78 bundled libraries, LICENSE shipped inside the EXE, UPX disabled. Still unsigned; bundle still unpackable with pyinstxtractor |
| v1.5.0 | Licence changed MIT -> proprietary source-available; explicitly non-retroactive (v1.4.1 and earlier stay MIT); third-party licensing preserved; CONTRIBUTING.md realigned. No code behaviour change |
| v1.4.1 | Map expansion 11 -> 20 regions (IND, BGD, LKA, NPL, BTN, BRN, TLS, KOR, PRK) from Natural Earth 1:10m; theatre 3,716 x 2,930 -> 6,788 x 5,806 km (+83% / +98%); registration-only edit to the protected loader (10 ins / 1 del); suite 41 -> 42 groups with per-ISO bounding-box and real version-lockstep assertions; JPN/PNG/AUS excluded as beyond the ~4,000 km guidance |

---

## Outstanding after v1.4.1

- **Gate 4 was never run.** `python main.py` visual confirmation is still outstanding — every
  other gate in this document passed headless. The theatre nearly doubled north-south, so if
  India and the Koreas make it read too wide at default zoom, drop regions and re-cut.
- **No GitHub Release object.** `v1.4.1` is tagged and pushed, but the `gh` CLI is not installed
  on this machine, so no Release was published. The README download badge points at
  `releases/latest` and will not resolve to v1.4.1 until one is created from the tag.
- **Zoom-floor margin is thin.** At the 0.10 floor the furthest point (North Korea, 4,552 km)
  renders 455 px from centre; on a 1024px-wide display the half-window is 461 px. Six pixels of
  margin. Adding anything further out requires lowering the floor again, or dropping PRK/KOR.

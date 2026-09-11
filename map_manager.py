# map_manager.py
"""
High-Fidelity Real Tactical Map Engine for AEGIS Air Defense Radar Simulator.
Renders real-world 1:10m scale geographical data for Thailand and neighboring countries:
- Myanmar, Laos, Cambodia, Vietnam, Malaysia, Singapore, Indonesia, China, Hainan,
  the Philippines, Taiwan, the Korean peninsula and the Japanese archipelago.
- High-resolution coastlines and international land borders.
- Bangkok FIR / Thai ADIZ (Air Defense Identification Zone).
- Maritime body labels (Gulf of Thailand, Andaman Sea, South China Sea, Malacca Strait).
- Country name labels and strategic RTAF/neighbor airbases and waypoints.
- Elevation contours for mountain peaks.
- High-performance surface caching for seamless 60 FPS rendering.
"""

import pygame
import math
import json
import os
import sys

RADAR_LAT = 13.7563  # Bangkok, Thailand (Origin 0, 0)
RADAR_LON = 100.5018

def latlon_to_km(lon, lat):
    """Convert longitude and latitude to relative kilometers from Bangkok radar origin."""
    dx = (lon - RADAR_LON) * 111.32 * math.cos(math.radians(RADAR_LAT))
    dy = (lat - RADAR_LAT) * 110.574
    return (dx, dy)

# Every geodata file here was cut from Natural Earth against one rectangular
# window. A polygon that straddles the window comes back closed along the cut,
# so the window itself gets drawn as if it were coastline - the straight
# "border" across northern China and the hard frame around the theatre.
#
# The window is found from the geometry rather than hard-coded: a cut shows up
# as a perfectly axis-aligned run of vertices sitting at the extreme edge of the
# data, and real coastline is never both perfectly straight and extremal. Those
# runs are dropped and what remains of the ring is drawn open.
CLIP_TOL = 0.05       # degrees a cut may sit inside the data extent
CLIP_MIN_RUN = 0.05   # degrees; shorter axis-aligned runs are real geography
CLIP_MIN_TOTAL = 2.0  # degrees of accumulated run before a line is believed
CUT_EPS = 1e-6        # tolerance matching a segment to a detected cut
#
# Residual hazard, deliberately accepted: a window edge placed exactly on a real
# straight border cannot be told apart from a cut. The Indonesia-Papua New
# Guinea border runs dead straight along the 141st meridian, so a future re-cut
# at lon 141.0 would delete it. Do not choose a window edge that lies on one.


def detect_clip_lines(rings):
    """Return (cut_lons, cut_lats): the meridians/parallels the data was cut on."""
    lons = [p[0] for r in rings for p in r]
    lats = [p[1] for r in rings for p in r]
    if not lons:
        return frozenset(), frozenset()
    lo_lon, hi_lon = min(lons), max(lons)
    lo_lat, hi_lat = min(lats), max(lats)
    lon_runs, lat_runs = {}, {}
    for ring in rings:
        for a, b in zip(ring, ring[1:]):
            if a[0] == b[0] and abs(a[1] - b[1]) > CLIP_MIN_RUN:
                if abs(a[0] - lo_lon) <= CLIP_TOL or abs(a[0] - hi_lon) <= CLIP_TOL:
                    lon_runs[a[0]] = lon_runs.get(a[0], 0.0) + abs(a[1] - b[1])
            if a[1] == b[1] and abs(a[0] - b[0]) > CLIP_MIN_RUN:
                if abs(a[1] - lo_lat) <= CLIP_TOL or abs(a[1] - hi_lat) <= CLIP_TOL:
                    lat_runs[a[1]] = lat_runs.get(a[1], 0.0) + abs(a[0] - b[0])
    # One coincidental straight stretch at the edge of the data is not a cut; a
    # real one runs for hundreds of kilometres.
    return (frozenset(v for v, run in lon_runs.items() if run >= CLIP_MIN_TOTAL),
            frozenset(v for v, run in lat_runs.items() if run >= CLIP_MIN_TOTAL))


def _is_cut(a, b, clip):
    """True when segment a->b lies along a detected cut rather than on land.

    Matched within CUT_EPS rather than by exact equality: the cut values and the
    vertices come from the same export today, but an export that re-rounded
    46.0 to 45.99998 would otherwise disable the trimming silently.
    """
    cut_lons, cut_lats = clip
    if a[0] == b[0] and any(abs(a[0] - c) <= CUT_EPS for c in cut_lons):
        return True
    if a[1] == b[1] and any(abs(a[1] - c) <= CUT_EPS for c in cut_lats):
        return True
    return False


def split_ring_on_frame(ring, clip):
    """Drop cut edges from a closed ring.

    Returns [(points, closed), ...]. A ring the cut never touched comes back
    intact and still closed; one it did is returned as the open runs of genuine
    geography that survive.
    """
    pts = list(ring)
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    n = len(pts)
    if n < 3:
        return []
    if not clip[0] and not clip[1]:
        return [(pts, True)]
    # segment i runs pts[i] -> pts[(i + 1) % n]
    drop = [_is_cut(pts[i], pts[(i + 1) % n], clip) for i in range(n)]
    if not any(drop):
        return [(pts, True)]
    if all(drop):
        return []
    start = drop.index(True)
    runs, cur = [], []
    for k in range(1, n + 1):
        i = (start + k) % n
        if drop[i]:
            if len(cur) >= 2:
                runs.append((cur, False))
            cur = []
        else:
            if not cur:
                cur.append(pts[i])
            cur.append(pts[(i + 1) % n])
    # No trailing flush: the walk starts just past a cut segment and runs a full
    # lap, so its final iteration lands back on that same cut and has already
    # flushed whatever was open.
    return runs


def split_line_on_frame(line, clip):
    """Drop cut edges from an open polyline, returning the surviving runs."""
    pts = list(line)
    n = len(pts)
    if n < 2:
        return []
    if not clip[0] and not clip[1]:
        return [pts]
    runs, cur = [], []
    for i in range(n - 1):
        if _is_cut(pts[i], pts[i + 1], clip):
            if len(cur) >= 2:
                runs.append(cur)
            cur = []
        else:
            if not cur:
                cur.append(pts[i])
            cur.append(pts[i + 1])
    if len(cur) >= 2:
        runs.append(cur)
    return runs


# Vertex budget. The theatre carries ~97k drawable points; transforming all of
# them costs more than a 60 FPS frame, and the surface cache misses on every
# pan. Two cheap filters keep the cost proportional to what is actually visible:
# a bounding-box reject, and thinning strokes whose vertices land closer than
# LOD_MIN_PX apart - detail finer than that cannot be resolved anyway.
#
# At the default 0.8 zoom every mainland outline keeps all its vertices; the
# strokes that do thin there are sub-pixel islets, a few hundred pixels of
# coastline in total across the whole theatre. Thinning stops entirely at 2.0.
LOD_MIN_PX = 4.0


def stroke_meta(pts):
    """(min_x, min_y, max_x, max_y, mean_segment_km) for one projected stroke."""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    n = len(pts) - 1
    if n > 0:
        total = 0.0
        for i in range(n):
            total += math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        seg = total / n
    else:
        seg = 0.0
    return (min(xs), min(ys), max(xs), max(ys), seg)


def thin_stroke(pts, seg_km, zoom_level):
    """Drop vertices a stroke is too small on screen to resolve.

    Module level rather than a closure in render() so the output guard below is
    reachable from the test suite.
    """
    step_px = seg_km * zoom_level
    if len(pts) <= 8 or step_px <= 0.0 or step_px >= LOD_MIN_PX:
        return pts
    stride = int(LOD_MIN_PX / step_px)
    if stride <= 1:
        return pts
    thinned = pts[::stride]
    if thinned[-1] != pts[-1]:
        thinned.append(pts[-1])
    # Guard the OUTPUT, not just the input length. A closed island loop repeats
    # its first vertex last, so the append above never fires for one, and a hard
    # stride can collapse it to a single point which the draw calls then discard
    # outright. Below four points a stroke is no longer a shape worth thinning.
    if len(thinned) < 4:
        return pts
    return thinned


def draw_dashed_polygon(surface, color, points, dash_len=8, space_len=6, width=1):
    """Draw an anti-aliased dashed polygon border."""
    if len(points) < 3:
        return
    for i in range(len(points)):
        p1 = points[i]
        p2 = points[(i + 1) % len(points)]
        dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if dist < 1e-3:
            continue
        dx = (p2[0] - p1[0]) / dist
        dy = (p2[1] - p1[1]) / dist
        curr = 0.0
        while curr < dist:
            seg_end = min(curr + dash_len, dist)
            sp = (p1[0] + dx * curr, p1[1] + dy * curr)
            ep = (p1[0] + dx * seg_end, p1[1] + dy * seg_end)
            pygame.draw.line(surface, color, sp, ep, width)
            curr += dash_len + space_len

class MapManager:
    # Map display modes
    MODE_FULL_TACTICAL = 0
    MODE_SOVEREIGN_FOCUS = 1
    MODE_MINIMAL = 2
    MODE_OFF = 3

    # Label tiers: (priority, min zoom in px/km). Lower priority wins a
    # collision; below min zoom the tier is not worth drawing at all. Without
    # this every tier renders at every scale and the theatre turns into an
    # unreadable smear as soon as the operator zooms out.
    #
    # Operational labels outrank decorative ones. This is an air defence
    # display: an RTAF wing must never be suppressed by a country name. Ordered
    # the obvious way round - SOVEREIGN above BASE - the word THAILAND is wide
    # enough to kill WING 4 (TAKHLI) at the default zoom, 40 px away from it.
    LBL_HQ = (0, 0.00)
    LBL_BASE = (1, 0.17)
    LBL_SOVEREIGN = (2, 0.00)
    LBL_COUNTRY = (3, 0.06)
    LBL_MARITIME = (4, 0.15)
    LBL_ADIZ = (5, 0.20)
    LBL_SUBTITLE = (6, 0.22)
    LBL_HUB = (7, 0.26)
    LBL_PEAK = (8, 0.34)

    MODE_NAMES = {
        MODE_FULL_TACTICAL: "FULL TACTICAL (ALL BORDERS & LABELS)",
        MODE_SOVEREIGN_FOCUS: "SOVEREIGN FOCUS (THAILAND & ADIZ)",
        MODE_MINIMAL: "MINIMAL RADAR (COASTS & BASES ONLY)",
        MODE_OFF: "TACTICAL DARK (MAP OVERLAY OFF)"
    }

    def __init__(self, base_dir=None):
        if base_dir is None:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
        else:
            self.base_dir = base_dir
            
        self.map_mode = self.MODE_FULL_TACTICAL
        
        # Geodata containers (in km relative to Bangkok)
        self.country_polys = {}  # iso -> list of rings (each ring is [(x_km, y_km), ...])
        self.country_closed = {} # iso -> list of bools, parallel to country_polys
        self.country_meta = {}   # iso -> list of stroke_meta, parallel to country_polys
        self.coast_meta = []     # parallel to coastlines_km
        self.border_meta = []    # parallel to borders_km
        self.data_frame = (frozenset(), frozenset())  # meridians/parallels the data was cut on
        self.coastlines_km = []  # list of [(x_km, y_km), ...]
        self.borders_km = []     # list of [(x_km, y_km), ...]
        self.adiz_km = []        # list of (x_km, y_km)
        
        # Strategic points
        self.airbases = []       # [(x_km, y_km, name, type, color), ...]
        self.peaks_km = []       # [(x_km, y_km, name, alt), ...]
        self.contours_km = []    # [list of (x_km, y_km), ...]
        
        # Typography / labels
        self.country_labels = [] # [(x_km, y_km, name, subtitle, color), ...]
        self.maritime_labels = []# [(x_km, y_km, name), ...]
        
        # Surface caching for 60 FPS
        self._cache_surface = None
        self._cache_key = None
        
        self.load_all_data()

    def _resolve_file(self, filename):
        """Locate file in base_dir or PyInstaller _MEIPASS."""
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            p = os.path.join(sys._MEIPASS, filename)
            if os.path.exists(p):
                return p
        p = os.path.join(self.base_dir, filename)
        if os.path.exists(p):
            return p
        return filename

    def load_all_data(self):
        """Load and project all geographical data into relative km."""
        # 1. Country Polygons
        country_files = {
            "THA": "tha.json",
            "MMR": "mmr.json",
            "LAO": "lao.json",
            "KHM": "khm.json",
            "VNM": "vnm.json",
            "MYS": "mys.json",
            "SGP": "sgp.json",
            "IDN": "idn.json",
            "CHN": "chn.json",
            "PHL": "phl.json",
            "TWN": "twn.json",
            "IND": "ind.json",
            "BGD": "bgd.json",
            "LKA": "lka.json",
            "NPL": "npl.json",
            "BTN": "btn.json",
            "BRN": "brn.json",
            "TLS": "tls.json",
            "KOR": "kor.json",
            "PRK": "prk.json",
            "JPN": "jpn.json"
        }

        raw_polys = {}
        for iso, fname in country_files.items():
            fpath = self._resolve_file(fname)
            if os.path.exists(fpath):
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        raw_polys[iso] = json.load(f)
                except Exception as e:
                    print(f"[MAP] Error loading {fname}: {e}")

        # 2. Coastlines
        raw_coast = []
        c_path = self._resolve_file("coastlines.json")
        if os.path.exists(c_path):
            try:
                with open(c_path, "r", encoding="utf-8") as f:
                    raw_coast = json.load(f)
            except Exception as e:
                print(f"[MAP] Error loading coastlines: {e}")

        # 3. Land Boundaries
        raw_borders = []
        b_path = self._resolve_file("borders.json")
        if os.path.exists(b_path):
            try:
                with open(b_path, "r", encoding="utf-8") as f:
                    raw_borders = json.load(f)
            except Exception as e:
                print(f"[MAP] Error loading borders: {e}")

        # The clip window is whatever rectangle bounds every loaded file, so this
        # keeps working untouched if the geodata is ever re-cut to a wider theatre.
        # Country rings are polygons, so detection must see the implicit closing
        # segment that split_ring_on_frame will evaluate - roughly half of them
        # are stored without a repeated final vertex. Coastlines and borders are
        # open lines; wrapping those would invent a segment that is not there.
        all_rings = [r if (len(r) > 1 and r[0] == r[-1]) else list(r) + [r[0]]
                     for rings in raw_polys.values() for r in rings if r]
        all_rings.extend(raw_coast)
        all_rings.extend(raw_borders)
        self.data_frame = detect_clip_lines(all_rings)
        frame = self.data_frame

        for iso, rings_raw in raw_polys.items():
            rings_km, closed_km = [], []
            for ring in rings_raw:
                for run, is_closed in split_ring_on_frame(ring, frame):
                    r_km = [latlon_to_km(lon, lat) for lon, lat in run]
                    if len(r_km) >= (3 if is_closed else 2):
                        rings_km.append(r_km)
                        closed_km.append(is_closed)
            self.country_polys[iso] = rings_km
            self.country_closed[iso] = closed_km
            self.country_meta[iso] = [stroke_meta(r) for r in rings_km]

        for seg in raw_coast:
            for run in split_line_on_frame(seg, frame):
                seg_km = [latlon_to_km(lon, lat) for lon, lat in run]
                if len(seg_km) >= 2:
                    self.coastlines_km.append(seg_km)
                    self.coast_meta.append(stroke_meta(seg_km))

        for seg in raw_borders:
            for run in split_line_on_frame(seg, frame):
                seg_km = [latlon_to_km(lon, lat) for lon, lat in run]
                if len(seg_km) >= 2:
                    self.borders_km.append(seg_km)
                    self.border_meta.append(stroke_meta(seg_km))

        # Fallback if tha.json is somehow missing
        if "THA" not in self.country_polys or not self.country_polys["THA"]:
            fallback = [
                (-200, 400), (-100, 500), (100, 450), (200, 200),
                (300, 100), (350, -100), (200, -200), (100, -400),
                (-50, -600), (-150, -300), (-250, 100)
            ]
            self.country_polys["THA"] = [fallback]
            self.country_closed["THA"] = [True]
            self.country_meta["THA"] = [stroke_meta(fallback)]

        # 4. Bangkok FIR / Thai ADIZ
        adiz_coords = [
            (20.45, 99.88), (20.15, 100.55), (19.50, 101.30), (18.20, 101.10),
            (17.90, 102.50), (18.30, 103.50), (17.40, 104.80), (16.50, 104.80),
            (15.30, 105.50), (14.40, 105.00), (14.30, 103.00), (13.60, 102.30),
            (11.70, 102.90), (11.50, 103.00), (10.15, 101.80), (08.00, 102.30),
            (06.45, 102.15), (05.60, 101.10), (06.70, 100.15), (06.50, 99.30),
            (07.00, 97.50), (09.50, 95.70), (10.00, 98.40), (11.80, 99.60),
            (13.30, 99.20), (14.60, 98.40), (15.20, 98.30), (16.30, 98.60),
            (17.80, 97.90), (19.30, 97.90), (19.80, 98.90)
        ]
        self.adiz_km = [latlon_to_km(lon, lat) for lat, lon in adiz_coords]

        # 5. Strategic Airbases & Waypoints
        airbase_data = [
            ("BANGKOK (C2 HQ)", 13.7563, 100.5018, "HQ", (0, 255, 180)),
            ("WING 1 (KORAT)", 14.933, 102.083, "RTAF", (0, 190, 255)),
            ("WING 4 (TAKHLI)", 15.266, 100.333, "RTAF", (0, 190, 255)),
            ("WING 7 (SURAT THANI)", 9.133, 99.133, "RTAF", (0, 190, 255)),
            ("WING 21 (UBON)", 15.250, 104.866, "RTAF", (0, 190, 255)),
            ("WING 23 (UDON)", 17.383, 102.783, "RTAF", (0, 190, 255)),
            ("WING 41 (CHIANG MAI)", 18.766, 98.962, "RTAF", (0, 190, 255)),
            ("WING 56 (HAT YAI)", 6.933, 100.393, "RTAF", (0, 190, 255)),
            ("RTN UTAPAO (SATTAHIP)", 12.679, 101.005, "RTN", (0, 230, 220)),
            ("PHUKET AIRPORT", 8.113, 98.316, "CIVIL", (120, 180, 200)),
            ("NAYPYIDAW [MMR]", 19.623, 96.200, "NEIGHBOR", (100, 140, 170)),
            ("YANGON [MMR]", 16.907, 96.133, "NEIGHBOR", (100, 140, 170)),
            ("VIENTIANE [LAO]", 17.988, 102.563, "NEIGHBOR", (100, 140, 170)),
            ("PHNOM PENH [KHM]", 11.546, 104.844, "NEIGHBOR", (100, 140, 170)),
            ("SIHANOUKVILLE [KHM]", 10.579, 103.636, "NEIGHBOR", (100, 140, 170)),
            ("HO CHI MINH [VNM]", 10.818, 106.651, "NEIGHBOR", (100, 140, 170)),
            ("DA NANG [VNM]", 16.043, 108.199, "NEIGHBOR", (100, 140, 170)),
            ("HANOI [VNM]", 21.221, 105.807, "NEIGHBOR", (100, 140, 170)),
            ("KUALA LUMPUR [MYS]", 2.745, 101.709, "NEIGHBOR", (100, 140, 170)),
            ("PENANG [MYS]", 5.297, 100.276, "NEIGHBOR", (100, 140, 170)),
            ("SINGAPORE CHANGI", 1.364, 103.991, "NEIGHBOR", (100, 140, 170)),
            ("SANYA (HAINAN)", 18.302, 109.412, "NEIGHBOR", (100, 140, 170)),
            ("TOKYO [JPN]", 35.689, 139.692, "NEIGHBOR", (100, 140, 170)),
            ("OKINAWA [JPN]", 26.334, 127.805, "NEIGHBOR", (100, 140, 170)),
        ]
        self.airbases = []
        for name, lat, lon, btype, col in airbase_data:
            x_km, y_km = latlon_to_km(lon, lat)
            self.airbases.append((x_km, y_km, name, btype, col))

        # 6. Mountain Peaks & Contours
        peaks_data = [
            (18.588, 98.487, "DOI INTHANON 8415FT"),
            (8.544, 99.736, "KHAO LUANG 6024FT"),
            (16.883, 101.783, "PHU KRADUENG 4301FT"),
            (13.5, 99.3, "TENASSERIM 3500FT"),
            (14.3, 102.0, "KHAO YAI 4400FT"),
            (19.9, 99.0, "DOI PHA HOM POK 7500FT")
        ]
        self.peaks_km = []
        for lat, lon, name in peaks_data:
            x_km, y_km = latlon_to_km(lon, lat)
            self.peaks_km.append((x_km, y_km, name))
        self.generate_topo_contours()

        # 7. Country Name Labels (Geographic Centroids)
        c_label_data = [
            ("THAILAND", "SOVEREIGN AIRSPACE", 15.2, 100.8, (0, 220, 100)),
            ("MYANMAR", "BURMA", 19.5, 96.0, (70, 120, 80)),
            ("LAOS", "PDR", 18.2, 103.5, (70, 120, 80)),
            ("CAMBODIA", "", 12.8, 104.9, (70, 120, 80)),
            ("VIETNAM", "", 15.5, 107.8, (70, 120, 80)),
            ("MALAYSIA", "PENINSULAR", 4.2, 102.0, (70, 120, 80)),
            ("SINGAPORE", "", 1.35, 103.82, (70, 120, 80)),
            ("INDONESIA", "SUMATRA", 3.2, 98.6, (60, 100, 75)),
            ("CHINA", "YUNNAN", 23.6, 101.5, (60, 100, 75)),
            ("HAINAN", "ISLAND", 19.2, 109.7, (60, 100, 75)),
            ("PHILIPPINES", "", 12.5, 122.5, (60, 100, 75)),
            ("TAIWAN", "", 23.7, 120.9, (60, 100, 75)),
            ("INDIA", "", 22.0, 79.0, (60, 100, 75)),
            ("BANGLADESH", "", 23.8, 90.3, (60, 100, 75)),
            ("SRI LANKA", "", 7.6, 80.7, (60, 100, 75)),
            ("NEPAL", "", 28.3, 84.1, (60, 100, 75)),
            ("BHUTAN", "", 27.5, 90.4, (60, 100, 75)),
            ("BRUNEI", "", 4.5, 114.7, (60, 100, 75)),
            ("TIMOR-LESTE", "", -8.8, 125.9, (60, 100, 75)),
            ("SOUTH KOREA", "ROK", 36.4, 127.8, (60, 100, 75)),
            ("NORTH KOREA", "DPRK", 40.0, 127.0, (60, 100, 75)),
            ("JAPAN", "", 36.4, 138.2, (60, 100, 75)),
        ]
        self.country_labels = []
        for name, sub, lat, lon, col in c_label_data:
            x_km, y_km = latlon_to_km(lon, lat)
            self.country_labels.append((x_km, y_km, name, sub, col))

        # 8. Maritime Labels
        maritime_data = [
            ("GULF OF THAILAND", 10.5, 101.2),
            ("ANDAMAN SEA", 10.0, 96.2),
            ("SOUTH CHINA SEA", 10.0, 109.5),
            ("STRAIT OF MALACCA", 3.5, 99.8),
            ("GULF OF MARTABAN", 16.0, 96.5),
            ("GULF OF TONKIN", 19.8, 107.0),
            ("EAST CHINA SEA", 28.5, 125.0),
            ("PHILIPPINE SEA", 20.0, 133.0),
            ("SEA OF JAPAN", 40.0, 135.0),
        ]
        self.maritime_labels = []
        for name, lat, lon in maritime_data:
            x_km, y_km = latlon_to_km(lon, lat)
            self.maritime_labels.append((x_km, y_km, name))

    def generate_topo_contours(self):
        """Generate organic elevation contours around major mountain peaks."""
        self.contours_km = []
        for px, py, name in self.peaks_km:
            height_str = ''.join(filter(str.isdigit, name))
            height = int(height_str) if height_str else 3000
            num_rings = max(2, height // 1200)

            for ring_idx in range(1, num_rings + 1):
                base_radius = ring_idx * 15  # km
                ring_points = []
                num_points = 48
                seed1 = (px * 13.7 + ring_idx * 7.1) % 100
                seed2 = (py * 17.3 + ring_idx * 3.3) % 100

                for i in range(num_points):
                    angle = math.radians(i * (360.0 / num_points))
                    n1 = math.sin(angle * 3 + seed1) * (base_radius * 0.15)
                    n2 = math.cos(angle * 5 + seed2) * (base_radius * 0.05)
                    r = base_radius + n1 + n2
                    cx = px + r * math.cos(angle)
                    cy = py + r * math.sin(angle)
                    ring_points.append((cx, cy))
                self.contours_km.append(ring_points)

    def cycle_mode(self):
        """Cycle through map display modes."""
        self.map_mode = (self.map_mode + 1) % 4
        self.invalidate_cache()
        return self.map_mode, self.MODE_NAMES[self.map_mode]

    def invalidate_cache(self):
        """Force map surface to re-render on next frame."""
        self._cache_key = None

    def render(self, screen, cx, cy, zoom_level, width, height, font_xs, font_sm, font_md):
        """
        High-performance map renderer with Surface caching.
        Only performs geometry transformations when camera/zoom/dimensions change.
        """
        if self.map_mode == self.MODE_OFF:
            return

        cache_key = (cx, cy, round(zoom_level, 4), width, height, self.map_mode)
        
        # Check if cached surface is valid
        if self._cache_key == cache_key and self._cache_surface is not None:
            screen.blit(self._cache_surface, (0, 0))
            return

        # Allocate/clear cache surface
        if self._cache_surface is None or self._cache_surface.get_size() != (width, height):
            self._cache_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        else:
            self._cache_surface.fill((0, 0, 0, 0))

        surf = self._cache_surface

        # The three linework passes below inline this transform instead of
        # calling it: at ~97k vertices a Python call per point is the single
        # largest cost in the frame.
        def km_to_screen(x_km, y_km):
            sx = cx + x_km * zoom_level
            sy = cy - y_km * zoom_level
            return (sx, sy)

        # Everything outside the viewport is rejected on its bounding box before
        # a single vertex is transformed, and what survives is thinned to the
        # resolution the current zoom can actually show.
        inv = 1.0 / max(zoom_level, 1e-6)
        pad = 48.0 * inv
        view_x0 = (0 - cx) * inv - pad
        view_x1 = (width - cx) * inv + pad
        view_y0 = (cy - height) * inv - pad
        view_y1 = cy * inv + pad

        def on_screen(meta):
            return not (meta[2] < view_x0 or meta[0] > view_x1
                        or meta[3] < view_y0 or meta[1] > view_y1)

        def lod(pts, meta):
            return thin_stroke(pts, meta[4], zoom_level)

        # Text is queued rather than blitted so it lands on top of all linework,
        # thins out by zoom, and yields to whatever matters more where two
        # labels want the same pixels.
        labels = []

        def queue(spec, text_surf, x, y, parent=None):
            """Queue one label. Returns a handle, or -1 if it will not be drawn.

            Pass a parent handle to tie a label to another one: a subtitle whose
            country name lost its collision must not be left stranded on the map
            on its own, which is what "SOVEREIGN AIRSPACE" did with no THAILAND
            above it once airbases started outranking country names.
            """
            if parent == -1:
                return -1
            tier, min_zoom = spec
            if zoom_level < min_zoom:
                return -1
            handle = len(labels)
            labels.append((tier, handle, text_surf, int(x), int(y), parent))
            return handle

        # ----------------------------------------------------
        # 1. Maritime Water Labels (MODE 0 & 1)
        # ----------------------------------------------------
        if self.map_mode in (self.MODE_FULL_TACTICAL, self.MODE_SOVEREIGN_FOCUS):
            for mx_km, my_km, mname in self.maritime_labels:
                sx, sy = km_to_screen(mx_km, my_km)
                if -150 <= sx <= width + 150 and -50 <= sy <= height + 50:
                    lbl = font_sm.render(f"~ {mname} ~", True, (0, 110, 130))
                    queue(self.LBL_MARITIME, lbl,
                          sx - lbl.get_width() // 2, sy - lbl.get_height() // 2)

        # ----------------------------------------------------
        # 2. Neighboring Country Borders (MODE 0 & 1)
        # ----------------------------------------------------
        if self.map_mode == self.MODE_FULL_TACTICAL:
            # Render neighbor country polygons in muted olive green
            for iso, rings in self.country_polys.items():
                if iso == "THA":
                    continue  # Thailand rendered with sovereign styling below
                flags = self.country_closed.get(iso, ())
                metas = self.country_meta.get(iso, ())
                for idx, ring in enumerate(rings):
                    closed = flags[idx] if idx < len(flags) else True
                    if idx < len(metas):
                        if not on_screen(metas[idx]):
                            continue
                        ring = lod(ring, metas[idx])
                    pts = [(cx + x * zoom_level, cy - y * zoom_level) for x, y in ring]
                    if closed and len(pts) >= 3:
                        pygame.draw.aalines(surf, (30, 70, 35), True, pts)
                    elif len(pts) >= 2:
                        pygame.draw.aalines(surf, (30, 70, 35), False, pts)

            # Render international land borders
            for idx, seg in enumerate(self.borders_km):
                if idx < len(self.border_meta):
                    if not on_screen(self.border_meta[idx]):
                        continue
                    seg = lod(seg, self.border_meta[idx])
                pts = [(cx + x * zoom_level, cy - y * zoom_level) for x, y in seg]
                if len(pts) >= 2:
                    pygame.draw.aalines(surf, (45, 95, 50), False, pts)

        # ----------------------------------------------------
        # 3. High-Resolution Coastlines (All Active Modes)
        # ----------------------------------------------------
        if self.coastlines_km:
            for idx, seg in enumerate(self.coastlines_km):
                if idx < len(self.coast_meta):
                    if not on_screen(self.coast_meta[idx]):
                        continue
                    seg = lod(seg, self.coast_meta[idx])
                pts = [(cx + x * zoom_level, cy - y * zoom_level) for x, y in seg]
                if len(pts) >= 2:
                    # Crisp anti-aliased maritime coastlines
                    pygame.draw.aalines(surf, (0, 175, 155), False, pts)

        # ----------------------------------------------------
        # 4. Thailand Sovereign Territory & Islands (High Priority)
        # ----------------------------------------------------
        if "THA" in self.country_polys:
            tha_flags = self.country_closed.get("THA", ())
            tha_metas = self.country_meta.get("THA", ())
            for idx, ring in enumerate(self.country_polys["THA"]):
                closed = tha_flags[idx] if idx < len(tha_flags) else True
                if idx < len(tha_metas):
                    if not on_screen(tha_metas[idx]):
                        continue
                    ring = lod(ring, tha_metas[idx])
                pts = [(cx + x * zoom_level, cy - y * zoom_level) for x, y in ring]
                # Sharp sovereign emerald green for Thailand
                if closed and len(pts) >= 3:
                    pygame.draw.aalines(surf, (0, 210, 80), True, pts)
                elif len(pts) >= 2:
                    pygame.draw.aalines(surf, (0, 210, 80), False, pts)

        # ----------------------------------------------------
        # 5. Bangkok FIR / Thai ADIZ Boundary (MODE 0 & 1)
        # ----------------------------------------------------
        if self.map_mode in (self.MODE_FULL_TACTICAL, self.MODE_SOVEREIGN_FOCUS):
            adiz_pts = [km_to_screen(x, y) for x, y in self.adiz_km]
            if len(adiz_pts) >= 3:
                # Amber-gold tactical dashed boundary
                draw_dashed_polygon(surf, (185, 140, 35), adiz_pts, dash_len=10, space_len=7, width=1)
                
                # ADIZ Label in the northern sector & southern sector
                if len(adiz_pts) > 14:
                    lbl_adiz = font_xs.render("[THAI ADIZ / BANGKOK FIR VTBB]", True, (185, 140, 35))
                    queue(self.LBL_ADIZ, lbl_adiz, adiz_pts[2][0] - 80, adiz_pts[2][1] - 14)
                    queue(self.LBL_ADIZ, lbl_adiz, adiz_pts[14][0] - 60, adiz_pts[14][1] + 6)

        # ----------------------------------------------------
        # 6. Topographic Elevation Contours & Mountain Peaks
        # ----------------------------------------------------
        if self.map_mode == self.MODE_FULL_TACTICAL and zoom_level >= self.LBL_PEAK[1]:
            for ring in self.contours_km:
                pts = [km_to_screen(x, y) for x, y in ring]
                if len(pts) >= 3:
                    pygame.draw.aalines(surf, (28, 48, 20), True, pts)

            for px_km, py_km, pname in self.peaks_km:
                sx, sy = km_to_screen(px_km, py_km)
                if -50 <= sx <= width + 50 and -50 <= sy <= height + 50:
                    pygame.draw.polygon(surf, (80, 110, 40), [(sx, sy - 4), (sx - 4, sy + 4), (sx + 4, sy + 4)], 1)
                    queue(self.LBL_PEAK, font_xs.render(pname, True, (80, 110, 40)), sx + 6, sy - 4)

        # ----------------------------------------------------
        # 7. Country Name Labels (MODE 0)
        # ----------------------------------------------------
        if self.map_mode == self.MODE_FULL_TACTICAL:
            for cx_km, cy_km, cname, csub, col in self.country_labels:
                sx, sy = km_to_screen(cx_km, cy_km)
                if -100 <= sx <= width + 100 and -50 <= sy <= height + 50:
                    c_txt = font_md.render(cname, True, col)
                    tier = self.LBL_SOVEREIGN if cname == "THAILAND" else self.LBL_COUNTRY
                    parent = queue(tier, c_txt, sx - c_txt.get_width() // 2, sy - 10)
                    if csub:
                        s_txt = font_xs.render(csub, True, (col[0] // 2 + 30, col[1] // 2 + 30, col[2] // 2 + 30))
                        queue(self.LBL_SUBTITLE, s_txt, sx - s_txt.get_width() // 2, sy + 8,
                              parent=parent)

        # ----------------------------------------------------
        # 8. Strategic Airbases & Regional Hubs
        # ----------------------------------------------------
        for bx_km, by_km, bname, btype, bcol in self.airbases:
            sx, sy = km_to_screen(bx_km, by_km)
            if not (-80 <= sx <= width + 80 and -40 <= sy <= height + 40):
                continue

            if btype == "HQ":
                # Central Command Reticle
                pygame.draw.circle(surf, bcol, (int(sx), int(sy)), 6, 1)
                pygame.draw.circle(surf, bcol, (int(sx), int(sy)), 2, 0)
                queue(self.LBL_HQ, font_xs.render(bname, True, bcol), sx + 10, sy - 4)
            elif btype in ("RTAF", "RTN"):
                # Military Base Icon (Circle + Inset Square)
                pygame.draw.circle(surf, bcol, (int(sx), int(sy)), 4, 1)
                pygame.draw.rect(surf, bcol, (int(sx - 3), int(sy - 3), 7, 7), 1)
                queue(self.LBL_BASE, font_xs.render(bname, True, bcol), sx + 8, sy - 4)
            elif (btype == "NEIGHBOR" and self.map_mode == self.MODE_FULL_TACTICAL
                    and zoom_level >= self.LBL_HUB[1]):
                # Neighboring Strategic Hub (Small Diamond)
                pygame.draw.polygon(surf, bcol, [(sx, sy - 3), (sx + 3, sy), (sx, sy + 3), (sx - 3, sy)], 1)
                queue(self.LBL_HUB, font_xs.render(bname, True, bcol), sx + 6, sy - 4)

        # ----------------------------------------------------
        # 9. Label pass - priority order, first claim on the pixels wins
        # ----------------------------------------------------
        occupied = []
        drawn = set()
        # Sorted by tier, so a parent is always resolved before its dependants.
        for _tier, handle, text_surf, tx, ty, parent in sorted(labels, key=lambda l: (l[0], l[1])):
            if parent is not None and parent not in drawn:
                continue
            rect = pygame.Rect(tx, ty, text_surf.get_width(), text_surf.get_height())
            if rect.right < 0 or rect.left > width or rect.bottom < 0 or rect.top > height:
                continue
            probe = rect.inflate(2, 2)
            if any(probe.colliderect(taken) for taken in occupied):
                continue
            occupied.append(rect)
            drawn.add(handle)
            surf.blit(text_surf, (tx, ty))

        # Save cache and blit to screen
        self._cache_key = cache_key
        screen.blit(surf, (0, 0))

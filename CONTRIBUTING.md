# Contributing to AEGIS Radar Simulator

Thank you for your interest in contributing to **AEGIS Radar** (`air-defense-radar-sim`)! We welcome contributions from military aviation enthusiasts, Python developers, radar engineers, and game designers alike.

Whether you want to model a new hypersonic threat, implement advanced radar signal processing, refine the CRT phosphor rendering, or add new airbase geodata, this guide provides everything you need to get started.

---

## Table of Contents
1. [Development Setup](#1-development-setup)
2. [Project Architecture & Directory Layout](#2-project-architecture--directory-layout)
3. [How to Add New Air Contacts & Threats](#3-how-to-add-new-air-contacts--threats)
4. [How to Contribute Radar Physics & DSP Algorithms](#4-how-to-contribute-radar-physics--dsp-algorithms)
5. [How to Add New Airbases & Geographic Data](#5-how-to-add-new-airbases--geographic-data)
6. [How to Synthesize Procedural Audio in NumPy](#6-how-to-synthesize-procedural-audio-in-numpy)
7. [Running the Automated Test Suite](#7-running-the-automated-test-suite)
8. [Code Style & Best Practices](#8-code-style--best-practices)
9. [Submitting a Pull Request](#9-submitting-a-pull-request)

---

## 1. Development Setup

### Prerequisites
- **Python 3.10** or higher
- **Git**
- Basic dependencies listed in `requirements.txt`: `pygame >= 2.0.0`, `numpy >= 1.20.0`

### Quick Start
```bash
# 1. Fork and clone the repository
git clone https://github.com/<your-username>/air-defense-radar-sim.git
cd air-defense-radar-sim

# 2. Create and activate a virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# 3. Install runtime dependencies
pip install -r requirements.txt

# 4. Run the simulation
python main.py

# 5. Run the headless logic test suite
python test_logic.py
```

---

## 2. Project Architecture & Directory Layout

The codebase follows a modular Object-Oriented architecture with clear separation between domain physics, presentation, and AI systems:

```
air-defense-radar-sim/
├── main.py              # Application entry point
├── command_center.py    # Core simulation engine, combat resolution, weapon salvoes
├── targets.py           # Domain models: AirContact ABC and 10 polymorphic target subclasses
├── radar_ui.py          # Presentation layer: Pygame AESA sweep, CRT shaders, HUD overlays
├── visual_effects.py    # Juice engine: T² camera shake, shockwaves, shrapnel, missile contrails
├── sound_engine.py      # Procedural NumPy audio synthesizer (zero external sound files)
├── personnel.py         # AI crew agents: RadarOperator and WeaponOfficer
├── config.py            # Simulation balance constants, airbase coordinates, weapon envelopes
├── test_logic.py        # Automated headless test suite (runnable in CI)
└── *.json               # GeoJSON border contours for regional geographic rendering
```

---

## 3. How to Add New Air Contacts & Threats

All airborne entities inherit from the abstract base class `AirContact` in `targets.py`.

### Step 1: Subclass `AirContact`
Create your new unit class in `targets.py`:

```python
from targets import AirContact, MACH_TO_KM_PER_SEC
import random
import math

class HypersonicGlideVehicle(AirContact):
    """Hypersonic Glide Vehicle (HGV) skipping along the upper atmosphere."""

    def __init__(self, track_number: int, distance_km: float = 1800.0):
        super().__init__(track_number, distance_km)
        self.speed_mach = random.uniform(8.0, 15.0)
        self.altitude_ft = random.randint(120000, 250000)
        self.rcs = random.uniform(0.05, 0.2)  # Low radar cross-section
        self.is_friendly = False
        self.has_transponder = False
        self.true_type = "DF-ZF Hypersonic Glide Vehicle"
        self.scenario = "HYPERSONIC_STRIKE"

    def identify_target(self) -> None:
        """Called by the radar operator when target identification completes."""
        self.type_name = self.true_type
        self.status = "HOSTILE"
        self.id_code = f"HGV-{self.track_number}"

    def calculate_threat_score(self) -> int:
        """Determines AI priority ranking in the Active Operations tactical queue."""
        return 800000 + int(2000 / max(1, self.distance_km))

    def move(self, *args, **kwargs) -> None:
        """Custom skip-glide trajectory dynamics."""
        super().move(*args, **kwargs)
        # Add trajectory weaving or altitude oscillation if applicable
```

### Step 2: Register in `command_center.py`
To enable manual spawning via debug hotkeys or automated wave generation during Phase 3 (Wartime):
1. In `command_center.py`, import your class from `targets.py`.
2. Add a spawn handler under `CommandCenter.manual_spawn(self, threat_type: str)`.
3. If applicable, add your threat to the randomized wartime wave spawn tables in `CommandCenter.detect_airspace()`.

---

## 4. How to Contribute Radar Physics & DSP Algorithms

We aim for realistic military radar concepts simplified into intuitive, performant algorithms. Areas open for contribution:

- **Radar Range Equation**: Refinements to the 4th-root SNR equation:
  $$R_{\text{max}} = R_0 \cdot \left(\frac{\text{RCS}}{\text{RCS}_0}\right)^{1/4} \cdot F_{\text{jamming}}$$
- **Atmospheric Attenuation & Weather Clutter**: Rain cell clutter scattering in X-band vs S-band.
- **Doppler Notch Filtering**: Modeling radial velocity thresholds where beaming aircraft (flying perpendicular to the radar beam) temporarily drop off moving target indicator (MTI) scopes.
- **AESA Multi-Beam Scheduling**: Enhancing time-shared electronic tracking beam allocation algorithms in `radar_ui.py`.

*Location of physics code*: `targets.py` (`is_detectable_by_radar()`, `is_line_of_sight_masked()`) and `command_center.py`.

---

## 5. How to Add New Airbases & Geographic Data

Airbase definitions are maintained in `config.py`:

```python
# Format: (X_KM_OFFSET, Y_KM_OFFSET, WING_NAME) relative to simulation origin
AIRBASES = [
    (0.0, 0.0, "Wing 6 Don Mueang (HQ)"),
    (170.0, -130.0, "Wing 1 Korat"),
    (-18.0, -167.0, "Wing 4 Takhli"),
    (-148.0, -511.0, "Wing 7 Surat Thani"),
    (470.0, -165.0, "Wing 21 Ubon Ratchathani"),
    (280.0, 480.0, "Wing 23 Udon Thani")
]
```

When adding an airbase:
1. Verify coordinate projection (Cartesian km from Bangkok origin: $+X$ = East, $+Y$ = North).
2. Ensure fighter scramble routing in `command_center.py` correctly resolves the nearest active base.
3. GeoJSON geographic boundaries are stored in `tha.json`, `mmr.json`, `lao.json`, etc. Use WGS84 GeoJSON polygons with simplified vertex densities to maintain 60 FPS rendering.

---

## 6. How to Synthesize Procedural Audio in NumPy

Our simulation relies on zero pre-recorded audio assets. All sound effects in `sound_engine.py` are mathematically synthesized at 44,100 Hz stereo:

```python
def synthesize_custom_sound(sample_rate: int = 44100, duration: float = 0.5) -> pygame.mixer.Sound:
    """Generate a stereo 16-bit signed PCM audio waveform."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    
    # 1. Generate primary waveform (sin, square, saw, or filtered noise)
    waveform = np.sin(2 * np.pi * 440.0 * t)
    
    # 2. Apply envelope shaping (attack, decay, sustain, release)
    envelope = np.exp(-3.0 * t / duration)
    
    # 3. Scale to 16-bit integer range (-32768 to 32767)
    pcm_mono = (waveform * envelope * 32767).astype(np.int16)
    
    # 4. Interleave into contiguous 2-channel stereo buffer
    pcm_stereo = np.ascontiguousarray(np.column_stack((pcm_mono, pcm_mono)))
    
    return pygame.sndarray.make_sound(pcm_stereo)
```

**Golden Rules for Audio Synthesis:**
- Always apply an attack/decay envelope to prevent transient popping or clicking at buffer edges.
- Ensure contiguous memory layout using `np.ascontiguousarray()`.
- Keep generation fast; sounds are cached during engine initialization.

---

## 7. Running the Automated Test Suite

Before opening a pull request, verify that all headless unit tests pass cleanly:

```bash
python test_logic.py
```

The test suite validates:
- Target kinematic step integration and velocity vectors.
- Threat score computation order.
- Weapon engagement ranges and ammunition depletion.
- EMCON transitions (ACTIVE $\rightarrow$ SECTOR $\rightarrow$ SILENT) and RF Decoy seduction logic.
- Radar horizon and RCS detection limits.

If you add a new feature, please include corresponding unit tests in `test_logic.py`!

---

## 8. Code Style & Best Practices

- **Python Version**: Write code compatible with Python 3.10+.
- **Type Annotations**: Use standard `typing` annotations (`Optional`, `Tuple`, `List`, `Dict`) for public functions and class methods.
- **Performance Awareness**: Pygame renders at 60 FPS. Avoid allocating heavy temporary objects or loading files inside `draw()` or per-frame update loops.
- **Dependencies**: Do not add heavy external C-libraries or frameworks without prior discussion. The goal is a lightweight, self-contained project that compiles seamlessly into a single-file executable via PyInstaller.

---

## 9. Submitting a Pull Request

1. **Create a topic branch**:
   ```bash
   git checkout -b feature/hgv-threat-model
   ```
2. **Commit your changes with clear, descriptive commit messages**:
   ```bash
   git commit -m "feat(targets): add Hypersonic Glide Vehicle with custom skip-glide trajectory"
   ```
3. **Run tests**:
   Ensure `python test_logic.py` passes with zero regressions.
4. **Push to your fork and submit a PR**:
   Open a Pull Request against the `main` branch with a clear summary of your changes, referencing any related issues.

Thank you for helping defend the digital skies! 📡✈️

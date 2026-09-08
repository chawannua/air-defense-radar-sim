"""
sound_engine.py - Procedural Military Audio Engine for Tactical Air Defense Simulator.

Provides realistic procedural military sound effects synthesized on-the-fly using NumPy
and Pygame Mixer:
  1. radar_ping: AESA radar sweep electronic chirp (1600 Hz -> 850 Hz over 90ms).
  2. defcon1_alarm: Dual-tone pulsating military emergency horn (820 Hz & 640 Hz in 250ms bursts).
  3. missile_launch: Rocket ignition transient crack + deep rising thrust rumble (90 Hz -> 240 Hz).
  4. explosion_flak: Supersonic detonation transient + sub-bass boom (160 Hz -> 35 Hz) with decay rumble.
     Also supports heavy=True for massive detonations (ICBMs / base impacts).
  5. ciws_burst: 3,900 RPM Gatling BRRRRT burst (65 Hz pulse train with buzzsaw harmonics).
  6. contact_alert: Short tactical high-pitched warning pip (1200 Hz, 60ms).
  7. radio_chatter: Radio squawk mic click + asynchronous Windows SAPI voice callouts
     (with fallback tactical telemetry beeps).

Includes safe initialization, graceful mock fallbacks when audio hardware is unavailable,
and thread-safe async radio callouts.
"""

import os
import sys
import time
import math
import queue
import logging
import threading
from typing import Optional, Any, Union

import numpy as np
import pygame

# Configure logging
logger = logging.getLogger("SoundEngine")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[%(levelname)s] [SoundEngine] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Optional SAPI support for Windows TTS
HAS_SAPI = False
try:
    import pythoncom
    import win32com.client
    HAS_SAPI = True
except Exception:
    HAS_SAPI = False

# Audio specifications
SAMPLE_RATE = 44100
CHANNELS = 2  # Stereo
BUFFER_SIZE = 512  # Low-latency buffer


# ============================================================================
# MOCK AUDIO CLASSES (FOR HEADLESS / NO-AUDIO HARDWARE FALLBACK)
# ============================================================================

class MockSound:
    """Safe no-op Sound mock when audio hardware is disabled or unavailable."""

    def __init__(self, name: str = "MockSound"):
        self.name = name

    def play(self, loops: int = 0, maxtime: int = 0, fade_ms: int = 0) -> Any:
        return MockChannel()

    def stop(self) -> None:
        pass

    def fadeout(self, time_ms: int) -> None:
        pass

    def set_volume(self, value: float) -> None:
        pass

    def get_volume(self) -> float:
        return 1.0

    def get_length(self) -> float:
        return 0.0


class MockChannel:
    """Safe no-op Channel mock when audio hardware is disabled or unavailable."""

    def play(self, sound: Any, loops: int = 0, maxtime: int = 0, fade_ms: int = 0) -> None:
        pass

    def stop(self) -> None:
        pass

    def pause(self) -> None:
        pass

    def unpause(self) -> None:
        pass

    def fadeout(self, time_ms: int) -> None:
        pass

    def set_volume(self, volume: float, volume2: Optional[float] = None) -> None:
        pass

    def get_busy(self) -> bool:
        return False


# ============================================================================
# PROCEDURAL DSP SYNTHESIS FUNCTIONS
# ============================================================================

def _gaussian_lowpass(sig: np.ndarray, cutoff_hz: float, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Fast Gaussian FIR low-pass filter using pure NumPy convolution."""
    if cutoff_hz <= 0 or cutoff_hz >= sr / 2:
        return sig
    sigma = sr / (2.0 * math.pi * cutoff_hz)
    kw = int(sigma * 6) | 1
    if kw < 3:
        kw = 3
    kx = np.arange(-kw // 2 + 1, kw // 2 + 1)
    kernel = np.exp(-0.5 * (kx / sigma) ** 2)
    kernel /= np.sum(kernel)
    return np.convolve(sig, kernel, mode="same")


def _to_stereo_sound(audio_array: np.ndarray, sr: int = SAMPLE_RATE) -> Union[pygame.mixer.Sound, MockSound]:
    """
    Converts a 1D (mono) or 2D (stereo) float array to a 16-bit stereo pygame.mixer.Sound.
    Applies soft-clipping via tanh and peak normalization to prevent distortion.
    """
    try:
        if not pygame.mixer.get_init():
            return MockSound()

        if audio_array.ndim == 1:
            stereo = np.column_stack((audio_array, audio_array))
        else:
            stereo = np.copy(audio_array)

        # Smooth 3ms attack ramp to eliminate sample 0 DC step discontinuities/clicks
        ramp_len = min(len(stereo), int(0.003 * SAMPLE_RATE))
        if ramp_len > 0:
            ramp = np.linspace(0.0, 1.0, ramp_len)[:, np.newaxis]
            stereo[:ramp_len] *= ramp

        # Peak normalization and soft-limiting (preserve relative dynamic range)
        peak = np.max(np.abs(stereo))
        if peak > 1.0:
            stereo = np.tanh(stereo)

        # Scale to 16-bit signed PCM with C-contiguous guarantee
        int16_pcm = np.ascontiguousarray(np.clip(stereo * 32767.0, -32768, 32767).astype(np.int16))
        return pygame.sndarray.make_sound(int16_pcm)
    except Exception as ex:
        logger.warning(f"Failed to create Sound from sndarray: {ex}")
        return MockSound()


def synth_radar_ping(sr: int = SAMPLE_RATE) -> np.ndarray:
    """
    Synthesizes an AESA radar sweep electronic chirp:
    Sweeps 1600 Hz down to 850 Hz over 90ms with exponential decay envelope.
    """
    dur = 0.090  # 90ms
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)

    f0, f1 = 1600.0, 850.0
    # Phase for linear frequency sweep: phi(t) = 2*pi * (f0*t + ((f1-f0)/(2*T)) * t^2)
    phase = 2.0 * np.pi * (f0 * t + ((f1 - f0) / (2.0 * dur)) * (t ** 2))

    # Electronic carrier with crisp high-tech radar overtones
    carrier = np.sin(phase) + 0.25 * np.sin(2.0 * phase) + 0.08 * np.sin(3.0 * phase)

    # Fast 2.5ms attack to avoid digital clicks, followed by exponential decay
    attack = np.minimum(t / 0.0025, 1.0)
    decay = np.exp(-4.2 * (t / dur))
    env = attack * decay

    mono = carrier * env * 0.90

    # Phased-array micro-spatialization: 6 sample micro-delay on right channel
    l_chan = mono
    r_chan = np.roll(mono, 6)
    r_chan[:6] = 0.0

    return np.column_stack((l_chan, r_chan * 0.95))


def synth_defcon1_alarm(sr: int = SAMPLE_RATE) -> np.ndarray:
    """
    Synthesizes a dual-tone pulsating military emergency horn:
    Alternating 820 Hz and 640 Hz in 250ms bursts with saturated horn harmonics.
    Seamless 1.0s loop pattern (4 bursts total).
    """
    burst_len = 0.250  # 250ms
    active_len = 0.225  # 225ms active tone + 25ms gap
    t_burst = np.linspace(0, burst_len, int(sr * burst_len), endpoint=False)

    def generate_horn_burst(freq: float) -> np.ndarray:
        # Emergency acoustic horn: fundamental + strong odd harmonics (3rd & 5th)
        horn = (
            np.sin(2.0 * np.pi * freq * t_burst)
            + 0.38 * np.sin(2.0 * np.pi * 3.0 * freq * t_burst)
            + 0.14 * np.sin(2.0 * np.pi * 5.0 * freq * t_burst)
        )
        # Saturated acoustic horn distortion (PA speaker character)
        horn = np.tanh(1.8 * horn)

        # Pulse envelope: 10ms attack, sustained tone, 20ms release, then brief silence
        env = np.ones_like(t_burst)
        att_idx = int(sr * 0.010)
        env[:att_idx] = np.linspace(0.0, 1.0, att_idx)

        act_idx = int(sr * active_len)
        rel_idx = int(sr * 0.020)
        env[act_idx - rel_idx:act_idx] = np.linspace(1.0, 0.0, rel_idx)
        env[act_idx:] = 0.0

        return horn * env * 0.88

    b_820 = generate_horn_burst(820.0)
    b_640 = generate_horn_burst(640.0)

    # 1.0-second seamless emergency cycle: [820, 640, 820, 640]
    cycle = np.concatenate([b_820, b_640, b_820, b_640])
    return np.column_stack((cycle, cycle))


def synth_missile_launch(sr: int = SAMPLE_RATE) -> np.ndarray:
    """
    Synthesizes a missile launch:
    Rocket ignition transient crack + deep rising thrust rumble (90 Hz -> 240 Hz)
    with low-pass filtered exhaust noise and combustion turbulence flutter.
    """
    dur = 1.40  # 1.4 seconds
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    n_samples = len(t)

    # Component 1: Initial ignition transient crack (first 60ms)
    rng = np.random.default_rng(42)
    raw_noise_l = rng.uniform(-1.0, 1.0, n_samples)
    raw_noise_r = rng.uniform(-1.0, 1.0, n_samples)

    crack_env = np.exp(-t / 0.020)
    ignition_pop = np.sin(2.0 * np.pi * 140.0 * t) * np.exp(-t / 0.035)
    crack_l = (raw_noise_l * crack_env * 0.90 + ignition_pop * 0.70)
    crack_r = (raw_noise_r * crack_env * 0.90 + ignition_pop * 0.70)

    # Component 2: Deep rising thrust rumble (90 Hz -> 240 Hz)
    f0, f1 = 90.0, 240.0
    phase_rumble = 2.0 * np.pi * (f0 * t + ((f1 - f0) / (1.8 * (dur ** 0.8))) * (t ** 1.8))
    rumble = (
        np.sin(phase_rumble)
        + 0.45 * np.sin(2.0 * phase_rumble)
        + 0.25 * np.sin(3.0 * phase_rumble)
        + 0.35 * np.sin(0.5 * phase_rumble)
    )
    rumble = np.tanh(rumble * 1.6)

    # Component 3: Filtered exhaust roar + combustion turbulence flutter
    flt_l = _gaussian_lowpass(raw_noise_l, 780.0, sr=sr)
    flt_r = _gaussian_lowpass(raw_noise_r, 780.0, sr=sr)
    flutter = 0.70 + 0.30 * np.sin(2.0 * np.pi * 23.0 * t) * np.sin(2.0 * np.pi * 37.0 * t)
    exhaust_l = flt_l * flutter
    exhaust_r = flt_r * flutter

    # Thrust envelope: rises behind ignition crack, sustains, then fades as missile flies away
    thrust_env = np.ones_like(t)
    att_idx = int(sr * 0.070)
    thrust_env[:att_idx] = np.linspace(0.1, 1.0, att_idx)
    decay_start = 0.75
    decay_mask = t > decay_start
    thrust_env[decay_mask] = np.exp(-3.8 * (t[decay_mask] - decay_start) / (dur - decay_start))

    mix_l = crack_l + (0.50 * rumble + 0.75 * exhaust_l) * thrust_env
    mix_r = crack_r + (0.50 * rumble + 0.75 * exhaust_r) * thrust_env

    return np.column_stack((np.tanh(mix_l * 1.3) * 0.92, np.tanh(mix_r * 1.3) * 0.92))


def synth_explosion_flak(heavy: bool = False, sr: int = SAMPLE_RATE) -> np.ndarray:
    """
    Synthesizes a supersonic flak detonation or heavy warhead explosion:
    Supersonic detonation transient + sub-bass boom (160 Hz -> 35 Hz) with decay rumble.
    If heavy=True: deeper pitch drop (135 Hz -> 25 Hz), longer duration, massive sub-bass.
    """
    dur = 2.20 if heavy else 1.40
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    n_samples = len(t)

    rng = np.random.default_rng(101 if heavy else 202)
    noise_l = rng.uniform(-1.0, 1.0, n_samples)
    noise_r = rng.uniform(-1.0, 1.0, n_samples)

    # Component 1: Detonation shockwave transient
    trans_decay = 0.022 if heavy else 0.013
    shock_impulse = np.sin(2.0 * np.pi * 1150.0 * t) * np.exp(-t / 0.005) * 0.65
    trans_l = noise_l * np.exp(-t / trans_decay) * 0.95 + shock_impulse
    trans_r = noise_r * np.exp(-t / trans_decay) * 0.95 + shock_impulse

    # Component 2: Sub-bass boom pitch drop (160 -> 35 Hz or 135 -> 25 Hz)
    f0, f1 = (135.0, 25.0) if heavy else (160.0, 35.0)
    k = 4.2 if heavy else 6.5
    phase_boom = 2.0 * np.pi * (f1 * t + ((f0 - f1) / k) * (1.0 - np.exp(-k * t)))
    boom = np.sin(phase_boom) + 0.40 * np.sin(2.0 * phase_boom) + 0.20 * np.sin(3.0 * phase_boom)

    boom_decay = 0.65 if heavy else 0.38
    boom_env = np.minimum(t / 0.003, 1.0) * np.exp(-t / boom_decay)
    boom = np.tanh(boom * 2.2) * boom_env

    # Component 3: Atmospheric reverberation and rolling flak decay rumble
    cutoff = 220.0 if heavy else 320.0
    rumble_l = _gaussian_lowpass(noise_l, cutoff, sr=sr)
    rumble_r = _gaussian_lowpass(noise_r, cutoff, sr=sr)

    rumble_mod = 0.60 + 0.25 * np.sin(2.0 * np.pi * 15.0 * t) + 0.15 * np.sin(2.0 * np.pi * 27.0 * t)
    rumble_decay = 0.90 if heavy else 0.52
    rumble_l = rumble_l * rumble_mod * np.exp(-t / rumble_decay) * 1.25
    rumble_r = rumble_r * rumble_mod * np.exp(-t / rumble_decay) * 1.25

    mix_l = 0.40 * trans_l + 0.60 * boom + 0.50 * rumble_l
    mix_r = 0.40 * trans_r + 0.60 * boom + 0.50 * rumble_r

    return np.column_stack((np.tanh(mix_l * 1.4) * 0.92, np.tanh(mix_r * 1.4) * 0.92))


def synth_ciws_burst(sr: int = SAMPLE_RATE) -> np.ndarray:
    """
    Synthesizes a 3,900 RPM Gatling BRRRRT burst:
    65 Hz pulse train with high-frequency buzzsaw harmonics and muzzle blast impulses.
    """
    dur = 0.48  # 480ms burst (~30 rounds)
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)

    # 1. 65 Hz Gatling fundamental + rich buzzsaw harmonics (up to 40 harmonics)
    harmonics = np.zeros_like(t)
    for k in range(1, 40):
        amp = 1.0 / (k ** 0.6)
        harmonics += amp * np.sin(2.0 * np.pi * 65.0 * k * t)
    buzzsaw = np.tanh(harmonics * 0.40)

    # 2. Muzzle blast shockwave pulse train at 65 Hz (every 15.38 ms)
    shots_l = np.zeros_like(t)
    shots_r = np.zeros_like(t)
    shot_interval = 1.0 / 65.0
    n_shots = int((dur - 0.08) / shot_interval)
    k_len = int(sr * 0.006)
    t_k = np.linspace(0, 0.006, k_len, endpoint=False)

    rng = np.random.default_rng(303)
    shot_k_l = rng.uniform(-1.0, 1.0, k_len) * np.exp(-t_k / 0.0012) + np.sin(2.0 * np.pi * 160.0 * t_k) * np.exp(-t_k / 0.0025)
    shot_k_r = rng.uniform(-1.0, 1.0, k_len) * np.exp(-t_k / 0.0012) + np.sin(2.0 * np.pi * 160.0 * t_k) * np.exp(-t_k / 0.0025)

    for s in range(n_shots):
        idx = int(s * shot_interval * sr)
        end_idx = min(idx + k_len, len(t))
        shots_l[idx:end_idx] += shot_k_l[:end_idx - idx]
        shots_r[idx:end_idx] += shot_k_r[:end_idx - idx]

    # 3. Burst envelope: rapid rise, sustained roar, sharp cutoff with reverb tail
    env = np.ones_like(t)
    att_idx = int(sr * 0.020)
    env[:att_idx] = np.linspace(0.0, 1.0, att_idx)
    fire_end = int(sr * (dur - 0.08))
    rel_samples = len(t) - fire_end
    env[fire_end:] = np.exp(-np.linspace(0.0, 4.5, rel_samples))

    # 4. Rotary motor spool whine
    motor_freq = 550.0 + 150.0 * np.sin(np.pi * t / dur)
    motor = 0.18 * np.sin(2.0 * np.pi * motor_freq * t)

    mix_l = (0.50 * buzzsaw + 0.60 * shots_l + motor) * env
    mix_r = (0.50 * buzzsaw + 0.60 * shots_r + motor) * env

    return np.column_stack((np.tanh(mix_l * 1.5) * 0.90, np.tanh(mix_r * 1.5) * 0.90))


def synth_contact_alert(sr: int = SAMPLE_RATE) -> np.ndarray:
    """
    Synthesizes a short tactical high-pitched warning pip:
    1200 Hz tone for 60ms with exponential decay envelope.
    """
    dur = 0.060  # 60ms
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    wave = np.sin(2.0 * np.pi * 1200.0 * t) + 0.15 * np.sin(2.0 * np.pi * 2400.0 * t)
    env = np.minimum(t / 0.003, 1.0) * np.exp(-3.2 * (t / dur))
    mono = wave * env * 0.88
    return np.column_stack((mono, mono))


def synth_radio_squawk(sr: int = SAMPLE_RATE) -> np.ndarray:
    """
    Synthesizes a radio mic squawk key-click:
    45ms bandpassed white noise burst + mic transient click.
    """
    dur = 0.045
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    rng = np.random.default_rng(404)
    raw = rng.uniform(-1.0, 1.0, len(t))
    flt = _gaussian_lowpass(raw, 2400.0, sr=sr)
    click = np.sin(2.0 * np.pi * 1800.0 * t) * np.exp(-t / 0.007)
    env = np.exp(-3.0 * t / dur)
    mono = np.tanh((flt * 1.6 + click * 0.70) * env) * 0.85
    return np.column_stack((mono, mono))


def synth_radio_roger(sr: int = SAMPLE_RATE) -> np.ndarray:
    """
    Synthesizes a radio transmission roger beep / squelch release:
    60ms dual-tone NATO roger beep (1500 Hz -> 2000 Hz) + squelch tail.
    """
    dur = 0.060
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    tone1 = np.sin(2.0 * np.pi * 1500.0 * t) * (t < 0.025)
    tone2 = np.sin(2.0 * np.pi * 2000.0 * t) * (t >= 0.025) * (t < 0.050)
    rng = np.random.default_rng(505)
    raw = rng.uniform(-1.0, 1.0, len(t))
    tail_noise = raw * (t >= 0.045) * np.exp(-(t - 0.045) / 0.005) * 0.30
    env = np.minimum(t / 0.002, 1.0)
    mono = np.tanh((tone1 + tone2 + tail_noise) * 0.75 * env) * 0.85
    return np.column_stack((mono, mono))


def synth_radio_beeps(sr: int = SAMPLE_RATE) -> np.ndarray:
    """
    Synthesizes clean tactical telemetry beeps (fallback when SAPI is unavailable):
    3 rapid tactical telemetry pips (850 Hz, 1250 Hz, 1700 Hz).
    """
    tones = [850.0, 1250.0, 1700.0]
    chunks = []
    pip_dur = 0.035
    t_pip = np.linspace(0, pip_dur, int(sr * pip_dur), endpoint=False)
    env = np.sin(np.pi * t_pip / pip_dur)  # Half-sine bell envelope
    gap = np.zeros(int(sr * 0.015))
    for f in tones:
        pip = np.sin(2.0 * np.pi * f * t_pip) * env * 0.75
        chunks.append(pip)
        chunks.append(gap)
    mono = np.concatenate(chunks)
    return np.column_stack((mono, mono))


def synth_eccm_burn(sr: int = SAMPLE_RATE) -> np.ndarray:
    """
    Synthesizes AESA transmitter overdrive burn-through chirp:
    High-power electronic rising sweep (450 Hz -> 2400 Hz over 220ms) with saturated
    phase harmonics and an energetic discharge crackle.
    """
    dur = 0.220
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    # Exponential frequency sweep from 450 to 2400 Hz
    f0, f1 = 450.0, 2400.0
    phase = 2.0 * np.pi * f0 * ((f1 / f0) ** (t / dur) - 1.0) / np.log(f1 / f0)
    
    # Overdriven RF pulse with 2nd and 3rd harmonics
    carrier = np.sin(phase) + 0.45 * np.sin(2.0 * phase) + 0.25 * np.sin(3.0 * phase)
    # 50 Hz amplitude modulation for transmitter hum
    carrier *= (0.80 + 0.20 * np.sin(2.0 * np.pi * 50.0 * t))
    
    # Envelope: 10ms rise, sustained overdrive, 30ms exponential decay
    env = np.ones_like(t)
    att_idx = int(sr * 0.010)
    env[:att_idx] = np.linspace(0.0, 1.0, att_idx)
    rel_idx = int(sr * 0.030)
    env[-rel_idx:] = np.linspace(1.0, 0.0, rel_idx)
    
    # Saturated overdrive distortion
    mono = np.tanh(carrier * 2.2) * env * 0.90
    return np.column_stack((mono, mono))


def synth_hoj_lock(sr: int = SAMPLE_RATE) -> np.ndarray:
    """
    Synthesizes Home-On-Jam passive RF seeker tone:
    1850 Hz carrier frequency rapidly modulated by a 35 Hz vibrato warble
    for 180ms, signaling passive emitter lock.
    """
    dur = 0.180
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    # Frequency modulation: 1850 Hz center +/- 120 Hz at 35 Hz
    freq_mod = 1850.0 + 120.0 * np.sin(2.0 * np.pi * 35.0 * t)
    phase = 2.0 * np.pi * np.cumsum(freq_mod) / sr
    carrier = np.sin(phase) + 0.30 * np.sin(2.0 * phase)
    
    # Bell-like envelope
    env = np.minimum(t / 0.005, 1.0) * np.exp(-2.5 * (t / dur))
    mono = np.tanh(carrier * 1.5) * env * 0.85
    return np.column_stack((mono, mono))


# ============================================================================
# SOUND MANAGER CLASS
# ============================================================================

class SoundManager:
    """
    Complete Tactical Audio Manager for the Air Defense Simulator.

    Provides a clean, unified API for playback of procedural military sound effects,
    looping alarms, volume control, muting, and asynchronous radio callouts.
    Gracefully falls back to mock implementations if audio hardware is unavailable.
    """

    _instance: Optional["SoundManager"] = None

    def __init__(self, master_volume: float = 1.0, enable_sapi: bool = True):
        self._muted: bool = False
        self._master_volume: float = max(0.0, min(1.0, master_volume))
        self._audio_available: bool = False
        self._enable_sapi: bool = enable_sapi and HAS_SAPI

        # Looping alarm tracking
        self._alarm_playing: bool = False
        self._alarm_channel: Any = MockChannel()

        # Pre-rendered procedural Sound objects
        self._snd_ping: Any = MockSound("ping")
        self._snd_alarm: Any = MockSound("alarm")
        self._snd_launch: Any = MockSound("launch")
        self._snd_explosion_flak: Any = MockSound("explosion_flak")
        self._snd_explosion_heavy: Any = MockSound("explosion_heavy")
        self._snd_ciws: Any = MockSound("ciws")
        self._snd_contact_alert: Any = MockSound("contact_alert")
        self._snd_radio_squawk: Any = MockSound("radio_squawk")
        self._snd_radio_roger: Any = MockSound("radio_roger")
        self._snd_radio_beeps: Any = MockSound("radio_beeps")
        self._snd_eccm_burn: Any = MockSound("eccm_burn")
        self._snd_hoj_lock: Any = MockSound("hoj_lock")

        # Asynchronous radio chatter worker
        self._radio_queue: queue.Queue = queue.Queue(maxsize=8)
        self._shutdown_flag: bool = False
        self._radio_thread: Optional[threading.Thread] = None

        # Initialize audio subsystem
        self._init_mixer_and_sounds()
        self._start_radio_worker()

    @classmethod
    def get_instance(cls, master_volume: float = 1.0) -> "SoundManager":
        """Singleton accessor for SoundManager."""
        if cls._instance is None:
            cls._instance = SoundManager(master_volume=master_volume)
        return cls._instance

    def _init_mixer_and_sounds(self) -> None:
        """Safely initializes pygame.mixer and synthesizes all procedural audio effects."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(
                    frequency=SAMPLE_RATE,
                    size=-16,
                    channels=CHANNELS,
                    buffer=BUFFER_SIZE
                )

            # Allocate 32 playback channels for polyphony
            pygame.mixer.set_num_channels(32)

            # Reserve Channel 0 for looping DEFCON 1 alarm
            pygame.mixer.set_reserved(1)
            self._alarm_channel = pygame.mixer.Channel(0)

            # Procedural synthesis of sound library
            self._snd_ping = _to_stereo_sound(synth_radar_ping())
            self._snd_alarm = _to_stereo_sound(synth_defcon1_alarm())
            self._snd_launch = _to_stereo_sound(synth_missile_launch())
            self._snd_explosion_flak = _to_stereo_sound(synth_explosion_flak(heavy=False))
            self._snd_explosion_heavy = _to_stereo_sound(synth_explosion_flak(heavy=True))
            self._snd_ciws = _to_stereo_sound(synth_ciws_burst())
            self._snd_contact_alert = _to_stereo_sound(synth_contact_alert())
            self._snd_radio_squawk = _to_stereo_sound(synth_radio_squawk())
            self._snd_radio_roger = _to_stereo_sound(synth_radio_roger())
            self._snd_radio_beeps = _to_stereo_sound(synth_radio_beeps())
            self._snd_eccm_burn = _to_stereo_sound(synth_eccm_burn())
            self._snd_hoj_lock = _to_stereo_sound(synth_hoj_lock())

            self._audio_available = True
            self._apply_volume()
            logger.info("Procedural audio engine initialized successfully (44100 Hz, 16-bit stereo).")

        except Exception as ex:
            self._audio_available = False
            self._alarm_channel = MockChannel()
            logger.warning(f"Audio hardware initialization bypassed ({ex}). Running in silent mock mode.")

    def _apply_volume(self) -> None:
        """Applies current master volume and mute state to all pre-rendered sounds."""
        effective_vol = 0.0 if self._muted else self._master_volume
        sounds = [
            self._snd_ping,
            self._snd_alarm,
            self._snd_launch,
            self._snd_explosion_flak,
            self._snd_explosion_heavy,
            self._snd_ciws,
            self._snd_contact_alert,
            self._snd_radio_squawk,
            self._snd_radio_roger,
            self._snd_radio_beeps,
            self._snd_eccm_burn,
            self._snd_hoj_lock,
        ]
        for s in sounds:
            try:
                s.set_volume(effective_vol)
            except Exception:
                pass

        try:
            self._alarm_channel.set_volume(effective_vol)
        except Exception:
            pass

    def _play_sound(self, sound: Any) -> Optional[Any]:
        """Helper to safely play a Sound object respecting mute and availability."""
        if not self._audio_available or self._muted:
            return None
        try:
            return sound.play()
        except Exception as ex:
            logger.debug(f"Playback error: {ex}")
            return None

    # ========================================================================
    # PUBLIC TACTICAL AUDIO INTERFACE
    # ========================================================================

    def play_ping(self) -> None:
        """Plays AESA radar sweep chirp (1600 Hz -> 850 Hz)."""
        self._play_sound(self._snd_ping)

    def play_launch(self) -> None:
        """Plays missile launch rocket ignition and deep rising thrust rumble."""
        self._play_sound(self._snd_launch)

    def play_explosion(self, heavy: bool = False) -> None:
        """
        Plays explosion sound:
        - heavy=False: supersonic flak / SAM detonation (160 Hz -> 35 Hz).
        - heavy=True: catastrophic warhead / ICBM / base hit detonation (135 Hz -> 25 Hz).
        """
        snd = self._snd_explosion_heavy if heavy else self._snd_explosion_flak
        self._play_sound(snd)

    def play_ciws(self) -> None:
        """Plays Phalanx CIWS 3,900 RPM Gatling BRRRRT burst (65 Hz pulse train)."""
        self._play_sound(self._snd_ciws)

    def start_alarm(self) -> None:
        """Starts looping DEFCON 1 emergency horn (820 Hz & 640 Hz alternating bursts)."""
        if self._alarm_playing:
            return
        self._alarm_playing = True
        if self._audio_available and not self._muted:
            try:
                self._alarm_channel.play(self._snd_alarm, loops=-1)
            except Exception as ex:
                logger.debug(f"Alarm play error: {ex}")

    def stop_alarm(self) -> None:
        """Stops DEFCON 1 emergency horn."""
        self._alarm_playing = False
        try:
            self._alarm_channel.fadeout(120)
        except Exception:
            try:
                self._alarm_channel.stop()
            except Exception:
                pass

    def play_contact_alert(self) -> None:
        """Plays tactical high-pitched warning pip (1200 Hz, 60ms)."""
        self._play_sound(self._snd_contact_alert)

    def play_eccm_burn(self) -> None:
        """Plays AESA transmitter overdrive burn-through chirp (450 Hz -> 2400 Hz sweep)."""
        self._play_sound(self._snd_eccm_burn)

    def play_hoj_lock(self) -> None:
        """Plays Home-On-Jam passive RF seeker homing tone (1850 Hz warble)."""
        self._play_sound(self._snd_hoj_lock)

    def radio_callout(self, text: str) -> None:
        """
        Dispatches an asynchronous tactical voice callout:
        Plays radio mic squawk click, calls Windows SAPI voice in a background thread,
        and finishes with a roger beep. Falls back to tactical telemetry beeps if SAPI
        is unavailable.
        """
        if not text:
            return
        try:
            # Don't let queue grow excessively during intense combat
            if self._radio_queue.full():
                try:
                    self._radio_queue.get_nowait()
                except queue.Empty:
                    pass
            self._radio_queue.put_nowait(text)
        except Exception as ex:
            logger.debug(f"Failed to queue radio callout: {ex}")

    def toggle_mute(self) -> bool:
        """
        Toggles mute state. Returns True if now muted, False if unmuted.
        """
        self._muted = not self._muted
        self._apply_volume()

        if self._muted:
            if self._alarm_playing:
                try:
                    self._alarm_channel.pause()
                except Exception:
                    pass
        else:
            if self._alarm_playing:
                try:
                    self._alarm_channel.unpause()
                    if not self._alarm_channel.get_busy():
                        self._alarm_channel.play(self._snd_alarm, loops=-1)
                except Exception:
                    pass

        logger.info(f"Audio {'MUTED' if self._muted else 'UNMUTED'}")
        return self._muted

    # ========================================================================
    # CONVENIENCE / LIFECYCLE METHODS
    # ========================================================================

    @property
    def is_muted(self) -> bool:
        """Returns True if audio is currently muted."""
        return self._muted

    @property
    def is_available(self) -> bool:
        """Returns True if audio hardware is initialized and available."""
        return self._audio_available

    def set_volume(self, volume: float) -> None:
        """Sets master volume between 0.0 and 1.0."""
        self._master_volume = max(0.0, min(1.0, float(volume)))
        self._apply_volume()

    def get_volume(self) -> float:
        """Returns current master volume."""
        return self._master_volume

    def stop_all(self) -> None:
        """Stops all playing sounds and alarms."""
        self.stop_alarm()
        if self._audio_available:
            try:
                pygame.mixer.stop()
            except Exception:
                pass

    def shutdown(self) -> None:
        """Shuts down radio worker thread and stops audio subsystem."""
        self._shutdown_flag = True
        try:
            self._radio_queue.put_nowait(None)
        except Exception:
            pass
        self.stop_all()

    # ========================================================================
    # ASYNCHRONOUS RADIO CHATTER WORKER
    # ========================================================================

    def _start_radio_worker(self) -> None:
        """Starts background daemon thread for asynchronous radio chatter."""
        self._radio_thread = threading.Thread(
            target=self._radio_worker_loop,
            name="TacticalRadioWorker",
            daemon=True
        )
        self._radio_thread.start()

    def _radio_worker_loop(self) -> None:
        """Background loop processing queued radio chatter messages."""
        while not self._shutdown_flag:
            try:
                msg = self._radio_queue.get(timeout=0.25)
            except queue.Empty:
                continue

            if msg is None or self._shutdown_flag:
                break

            if self._muted:
                self._radio_queue.task_done()
                continue

            # 1. Play mic key squawk click
            if self._audio_available and not self._muted:
                self._play_sound(self._snd_radio_squawk)
                time.sleep(0.05)

            # 2. Asynchronous voice transmission via Windows SAPI
            spoken = False
            if self._enable_sapi and self._audio_available and not self._muted:
                try:
                    import pythoncom
                    import win32com.client
                    pythoncom.CoInitialize()
                    try:
                        voice = win32com.client.Dispatch("SAPI.SpVoice")
                        voice.Rate = 1  # Crisp tactical dispatch speed
                        voice.Volume = int(self._master_volume * 100)
                        voice.Speak(str(msg))
                        spoken = True
                    finally:
                        pythoncom.CoUninitialize()
                except Exception as ex:
                    logger.debug(f"SAPI voice error: {ex}")
                    spoken = False

            # 3. Fallback: Clean tactical telemetry beeps if SAPI is unavailable
            if not spoken and self._audio_available and not self._muted:
                self._play_sound(self._snd_radio_beeps)
                time.sleep(0.18)

            # 4. Play roger beep / squelch release
            if self._audio_available and not self._muted:
                self._play_sound(self._snd_radio_roger)

            self._radio_queue.task_done()


# Module-level convenience function
def get_sound_manager() -> SoundManager:
    """Returns the shared SoundManager singleton instance."""
    return SoundManager.get_instance()

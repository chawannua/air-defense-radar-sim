"""Simulation profiles: Spectator vs Player mode spawn/behavior knobs.

Profiles are plain, immutable data objects that are READ by the simulation.
They must never mutate GameConfig class-level attributes -- GameConfig remains
the single default source of truth, and profiles simply override specific
values when consulted via `get()` / `resolve_config()`.
"""
from dataclasses import dataclass, fields
from typing import Optional

from config import GameConfig


@dataclass(frozen=True)
class SimulationProfile:
    name: str

    # Wave / spawn knobs. Leave as None to fall back to GameConfig defaults.
    wave_chance: Optional[float] = None
    wave_size_min: Optional[int] = None
    wave_size_max: Optional[int] = None
    wave_cooldown_initial: Optional[int] = None
    wave_cooldown_after: Optional[int] = None

    # Behavior flags
    autonomous_weapons: bool = True
    player_input_enabled: bool = False

    def resolve(self, attr_name, config_attr=None):
        """Return this profile's value for `attr_name`, falling back to the
        matching GameConfig attribute (named `config_attr`, defaulting to the
        upper-cased `attr_name`) if the profile's own value is None."""
        value = getattr(self, attr_name)
        if value is not None:
            return value
        config_attr = config_attr or attr_name.upper()
        return getattr(GameConfig, config_attr)

    def resolve_config(self):
        """Return a plain dict of every spawn knob resolved against
        GameConfig, without mutating GameConfig itself."""
        return {
            "WAVE_CHANCE": self.resolve("wave_chance", "WAVE_CHANCE"),
            "WAVE_SIZE_MIN": self.resolve("wave_size_min", "WAVE_SIZE_MIN"),
            "WAVE_SIZE_MAX": self.resolve("wave_size_max", "WAVE_SIZE_MAX"),
            "WAVE_COOLDOWN_INITIAL": self.resolve("wave_cooldown_initial", "WAVE_COOLDOWN_INITIAL"),
            "WAVE_COOLDOWN_AFTER": self.resolve("wave_cooldown_after", "WAVE_COOLDOWN_AFTER"),
        }


# Spectator: maximum spawn volume/complexity, the AI runs the whole engagement.
SPECTATOR_PROFILE = SimulationProfile(
    name="SPECTATOR",
    wave_chance=min(1.0, GameConfig.WAVE_CHANCE * 1.5),
    wave_size_min=GameConfig.WAVE_SIZE_MIN,
    wave_size_max=int(GameConfig.WAVE_SIZE_MAX * 1.5),
    wave_cooldown_initial=max(1, int(GameConfig.WAVE_COOLDOWN_INITIAL * 0.5)),
    wave_cooldown_after=max(1, int(GameConfig.WAVE_COOLDOWN_AFTER * 0.5)),
    autonomous_weapons=True,
    player_input_enabled=False,
)

# Player: reduced/balanced spawn volume, human holds the trigger.
PLAYER_PROFILE = SimulationProfile(
    name="PLAYER",
    wave_chance=GameConfig.WAVE_CHANCE * 0.5,
    wave_size_min=max(1, GameConfig.WAVE_SIZE_MIN // 2),
    wave_size_max=max(1, GameConfig.WAVE_SIZE_MAX // 2),
    wave_cooldown_initial=int(GameConfig.WAVE_COOLDOWN_INITIAL * 1.5),
    wave_cooldown_after=int(GameConfig.WAVE_COOLDOWN_AFTER * 1.5),
    autonomous_weapons=False,
    player_input_enabled=True,
)


# Default profile: mirrors today's un-profiled behaviour (pure GameConfig
# defaults), used when start_radar() is called with profile=None.
DEFAULT_PROFILE = SimulationProfile(
    name="DEFAULT",
    # Un-profiled callers (e.g. running radar_ui.py directly) are a human
    # at the console, not a spectator: they must retain command input.
    player_input_enabled=True,
)

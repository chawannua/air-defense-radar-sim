"""Cinematic camera director for the menu background.

Produces slow, smooth (eased) camera motion drifting between waypoints,
by default the RTAF airbase positions from GameConfig.AIRBASES, so the
menu background pans across real map features rather than jumping.
"""
import math
from config import GameConfig


def _smoothstep(t):
    """Smoothstep easing: 3t^2 - 2t^3, clamped to [0, 1]."""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


class CameraDirector:
    def __init__(self, waypoints=None, seconds_per_leg=14.0,
                 zoom_min=0.55, zoom_max=0.95):
        if waypoints is None:
            waypoints = [(x, y) for (x, y, _name) in GameConfig.AIRBASES]
        if len(waypoints) < 2:
            waypoints = waypoints * 2 if waypoints else [(0.0, 0.0), (0.0, 0.0)]

        self._waypoints = list(waypoints)
        self._seconds_per_leg = max(0.01, float(seconds_per_leg))
        self._zoom_min = zoom_min
        self._zoom_max = zoom_max

        self._t = 0.0  # elapsed time within the current leg
        self._leg = 0  # index of the origin waypoint for the current leg

        self._camera_x = self._waypoints[0][0]
        self._camera_y = self._waypoints[0][1]
        self._zoom_level = (zoom_min + zoom_max) / 2.0

    def update(self, dt):
        dt = max(0.0, float(dt))
        self._t += dt

        while self._t >= self._seconds_per_leg:
            self._t -= self._seconds_per_leg
            self._leg = (self._leg + 1) % len(self._waypoints)

        origin = self._waypoints[self._leg % len(self._waypoints)]
        dest = self._waypoints[(self._leg + 1) % len(self._waypoints)]

        progress = _smoothstep(self._t / self._seconds_per_leg)

        self._camera_x = origin[0] + (dest[0] - origin[0]) * progress
        self._camera_y = origin[1] + (dest[1] - origin[1]) * progress

        # Slow oscillating zoom breathing, eased with cosine so it never jumps.
        total_progress = (self._leg + progress) / len(self._waypoints)
        zoom_phase = (math.cos(total_progress * math.pi * 2.0) + 1.0) / 2.0
        self._zoom_level = self._zoom_min + (self._zoom_max - self._zoom_min) * zoom_phase

        return self.values

    @property
    def camera_x(self):
        return self._camera_x

    @property
    def camera_y(self):
        return self._camera_y

    @property
    def zoom_level(self):
        return self._zoom_level

    @property
    def values(self):
        return (self._camera_x, self._camera_y, self._zoom_level)

"""visual_effects.py - High-Performance Game Feel & Visual FX Engine ("Juice Engine")
Tactical Air Defense Simulator
"""

import pygame
import math
import random
from typing import Tuple, List, Optional

# Predefined Color Palettes
COLOR_WHITE = (255, 255, 255)
COLOR_YELLOW = (255, 235, 75)
COLOR_ORANGE = (255, 125, 20)
COLOR_EMBER = (140, 75, 25)
COLOR_SMOKE = (100, 95, 95)
COLOR_DARK_SMOKE = (50, 50, 50)
COLOR_HUD_CYAN = (0, 240, 210)
COLOR_HUD_AMBER = (255, 200, 40)
COLOR_HUD_GREEN = (0, 230, 80)
COLOR_ROCKET_HEAD = (255, 255, 210)
COLOR_ROCKET_FLAME = (255, 140, 30)
COLOR_VIGNETTE_RED = (255, 20, 20)


def lerp_color(c1: Tuple[int, int, int], c2: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    """Linear interpolation between two RGB color tuples."""
    t = max(0.0, min(1.0, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t)
    )


class ShrapnelParticle:
    """High-velocity explosion shrapnel & ember particle with drag, gravity/drift,
    and multi-stage color decay (White -> Bright Yellow -> Amber/Orange -> Smoke Grey).
    """
    __slots__ = (
        'x', 'y', 'vx', 'vy', 'lifetime', 'age', 'initial_size',
        'size', 'drag', 'gravity', 'drift_x', 'custom_color', 'active'
    )

    def __init__(self, x: float, y: float, vx: float, vy: float,
                 lifetime: float, size: float = 2.5,
                 drag: float = 1.8, gravity: float = 25.0,
                 drift_x: float = 0.0, custom_color: Optional[Tuple[int, int, int]] = None):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.lifetime = max(0.05, float(lifetime))
        self.age = 0.0
        self.initial_size = float(size)
        self.size = float(size)
        self.drag = float(drag)
        self.gravity = float(gravity)
        self.drift_x = float(drift_x)
        self.custom_color = custom_color
        self.active = True

    def update(self, dt: float) -> bool:
        self.age += dt
        if self.age >= self.lifetime:
            self.active = False
            return False

        # Physics integration with aerodynamic drag & drift/gravity
        self.x += self.vx * dt
        self.y += self.vy * dt

        drag_factor = max(0.0, 1.0 - self.drag * dt)
        self.vx = self.vx * drag_factor + self.drift_x * dt
        self.vy = self.vy * drag_factor + self.gravity * dt

        # Thermal shrinkage
        progress = self.age / self.lifetime
        self.size = max(1.0, self.initial_size * (1.0 - progress * 0.55))
        return True

    def get_color_and_alpha(self) -> Tuple[Tuple[int, int, int], int]:
        progress = min(1.0, max(0.0, self.age / self.lifetime))

        if self.custom_color is None:
            # Color Decay: White -> Bright Yellow -> Amber/Orange -> Smoke Grey
            if progress < 0.15:
                # White -> Bright Yellow
                t = progress / 0.15
                col = lerp_color(COLOR_WHITE, COLOR_YELLOW, t)
            elif progress < 0.45:
                # Bright Yellow -> Amber/Orange
                t = (progress - 0.15) / 0.30
                col = lerp_color(COLOR_YELLOW, COLOR_ORANGE, t)
            elif progress < 0.75:
                # Amber/Orange -> Ember
                t = (progress - 0.45) / 0.30
                col = lerp_color(COLOR_ORANGE, COLOR_EMBER, t)
            else:
                # Ember -> Smoke Grey -> Dark Charcoal
                t = (progress - 0.75) / 0.25
                col = lerp_color(COLOR_SMOKE, COLOR_DARK_SMOKE, t)
        else:
            # Custom tint color decay support
            if progress < 0.20:
                t = progress / 0.20
                col = lerp_color(COLOR_WHITE, self.custom_color, t)
            elif progress < 0.65:
                col = self.custom_color
            else:
                t = (progress - 0.65) / 0.35
                col = lerp_color(self.custom_color, COLOR_DARK_SMOKE, t)

        # Alpha decay: full opacity for initial 55%, smoothly fades to 0 in smoke phase
        if progress < 0.55:
            alpha = 255
        else:
            alpha = max(0, int(255 * (1.0 - (progress - 0.55) / 0.45)))

        return col, alpha

    def draw(self, surface: pygame.Surface, offset_x: float = 0.0, offset_y: float = 0.0):
        if not self.active:
            return

        col, alpha = self.get_color_and_alpha()
        if alpha <= 0:
            return

        px = int(self.x + offset_x)
        py = int(self.y + offset_y)
        w, h = surface.get_size()
        if px < -10 or px > w + 10 or py < -10 or py > h + 10:
            return

        sz = int(round(self.size))
        if sz <= 1:
            if alpha >= 240 and 0 <= px < w and 0 <= py < h:
                surface.set_at((px, py), col)
            else:
                dot = pygame.Surface((3, 3), pygame.SRCALPHA)
                dot.fill((*col, alpha))
                surface.blit(dot, (px - 1, py - 1))
        else:
            dim = sz * 2 + 2
            p_surf = pygame.Surface((dim, dim), pygame.SRCALPHA)
            pygame.draw.circle(p_surf, (*col, alpha), (dim // 2, dim // 2), sz)
            surface.blit(p_surf, (px - dim // 2, py - dim // 2))


class ShockwaveRing:
    """Expanding circular shockwave ring.
    Radius expands from start_radius (e.g. 5px) to max_radius (e.g. 45px),
    width shrinks from start_width (3px) down to end_width (1px),
    while alpha fades smoothly to 0.
    """
    __slots__ = (
        'x', 'y', 'start_radius', 'max_radius', 'start_width',
        'end_width', 'lifetime', 'age', 'radius', 'width', 'color', 'active'
    )

    def __init__(self, x: float, y: float, start_radius: float = 5.0,
                 max_radius: float = 45.0, start_width: float = 3.0,
                 end_width: float = 1.0, lifetime: float = 0.45,
                 color: Tuple[int, int, int] = (255, 255, 255)):
        self.x = float(x)
        self.y = float(y)
        self.start_radius = float(start_radius)
        self.max_radius = float(max_radius)
        self.start_width = float(start_width)
        self.end_width = float(end_width)
        self.lifetime = max(0.05, float(lifetime))
        self.age = 0.0
        self.radius = self.start_radius
        self.width = self.start_width
        self.color = color
        self.active = True

    def update(self, dt: float) -> bool:
        self.age += dt
        if self.age >= self.lifetime:
            self.active = False
            return False

        # Non-linear expansion curve: rapid explosive burst decelerating at boundary
        progress = self.age / self.lifetime
        eased_progress = progress ** 0.65
        self.radius = self.start_radius + (self.max_radius - self.start_radius) * eased_progress
        self.width = max(1.0, self.start_width - (self.start_width - self.end_width) * progress)
        return True

    def draw(self, surface: pygame.Surface, offset_x: float = 0.0, offset_y: float = 0.0):
        if not self.active:
            return

        progress = min(1.0, max(0.0, self.age / self.lifetime))
        alpha = max(0, int(255 * (1.0 - progress)))
        if alpha <= 0:
            return

        r_int = int(round(self.radius))
        w_int = max(1, int(round(self.width)))
        if r_int <= 0:
            return

        dim = (r_int + w_int + 2) * 2
        ring_surf = pygame.Surface((dim, dim), pygame.SRCALPHA)
        center = dim // 2

        # Primary shockwave ring
        pygame.draw.circle(ring_surf, (*self.color, alpha), (center, center), r_int, w_int)

        # Faint inner refraction ripple
        if r_int > 10 and alpha > 60:
            inner_alpha = int(alpha * 0.35)
            pygame.draw.circle(ring_surf, (*self.color, inner_alpha), (center, center), max(1, r_int - w_int - 2), 1)

        px = int(self.x + offset_x) - center
        py = int(self.y + offset_y) - center
        surface.blit(ring_surf, (px, py))


class FlashBloom:
    """High-intensity epicenter flash bloom that lasts exactly 3 frames."""
    __slots__ = ('x', 'y', 'max_radius', 'total_frames', 'frame_idx', 'color', 'active')

    def __init__(self, x: float, y: float, max_radius: float = 25.0,
                 total_frames: int = 3, color: Tuple[int, int, int] = (255, 255, 240)):
        self.x = float(x)
        self.y = float(y)
        self.max_radius = float(max_radius)
        self.total_frames = int(total_frames)
        self.frame_idx = 0
        self.color = color
        self.active = True

    def update(self, dt: float = 0.0) -> bool:
        self.frame_idx += 1
        if self.frame_idx >= self.total_frames:
            self.active = False
            return False
        return True

    def draw(self, surface: pygame.Surface, offset_x: float = 0.0, offset_y: float = 0.0):
        if not self.active:
            return

        # 3-frame bloom decay curve
        if self.frame_idx == 0:
            rad = self.max_radius * 0.8
            alpha = 245
            halo_alpha = 120
        elif self.frame_idx == 1:
            rad = self.max_radius * 1.05
            alpha = 150
            halo_alpha = 60
        else:
            rad = self.max_radius * 1.3
            alpha = 65
            halo_alpha = 20

        rad_int = max(2, int(round(rad)))
        dim = rad_int * 2 + 4
        bloom_surf = pygame.Surface((dim, dim), pygame.SRCALPHA)
        center = dim // 2

        # Outer soft glow halo
        pygame.draw.circle(bloom_surf, (*self.color, halo_alpha), (center, center), rad_int)
        # Inner super-bright core
        core_rad = max(1, int(rad_int * 0.45))
        pygame.draw.circle(bloom_surf, (255, 255, 255, alpha), (center, center), core_rad)

        px = int(self.x + offset_x) - center
        py = int(self.y + offset_y) - center
        surface.blit(bloom_surf, (px, py))


class MissileTracer:
    """Rocket tracer with a glowing rocket head and fading contrail history segments."""
    __slots__ = (
        'start_x', 'start_y', 'target_x', 'target_y', 'duration_ticks',
        'current_tick', 'color', 'head_size', 'contrail', 'head_x',
        'head_y', 'active', 'completed'
    )

    def __init__(self, start_pos: Tuple[float, float], target_pos: Tuple[float, float],
                 duration_ticks: int = 30, color: Tuple[int, int, int] = COLOR_ROCKET_FLAME,
                 head_size: float = 3.0):
        self.start_x = float(start_pos[0])
        self.start_y = float(start_pos[1])
        self.target_x = float(target_pos[0])
        self.target_y = float(target_pos[1])
        self.duration_ticks = max(1, int(duration_ticks))
        self.current_tick = 0
        self.color = color
        self.head_size = float(head_size)
        self.contrail: List[Tuple[float, float, float]] = []  # (x, y, age)
        self.head_x = self.start_x
        self.head_y = self.start_y
        self.active = True
        self.completed = False

    def update(self, dt: float = 0.0) -> bool:
        if not self.completed:
            self.current_tick += 1
            progress = min(1.0, self.current_tick / float(self.duration_ticks))
            self.head_x = self.start_x + (self.target_x - self.start_x) * progress
            self.head_y = self.start_y + (self.target_y - self.start_y) * progress

            # Append current position to contrail history
            self.contrail.append((self.head_x, self.head_y, 0.0))
            if progress >= 1.0:
                self.completed = True

        # Age and prune contrail points
        dt_effective = dt if dt > 0 else 0.016
        updated_contrail = []
        for cx, cy, age in self.contrail:
            new_age = age + dt_effective
            if new_age < 0.5:  # Contrail fades out over 0.5s
                updated_contrail.append((cx, cy, new_age))
        self.contrail = updated_contrail

        if self.completed and not self.contrail:
            self.active = False
            return False
        return True

    def draw(self, surface: pygame.Surface, offset_x: float = 0.0, offset_y: float = 0.0):
        if not self.active:
            return

        # 1. Draw contrail segments
        num_points = len(self.contrail)
        if num_points >= 2:
            for i in range(num_points - 1):
                p1 = self.contrail[i]
                p2 = self.contrail[i + 1]
                t = i / float(num_points)  # 0.0 at oldest tail, 1.0 near rocket head

                age_factor = max(0.0, 1.0 - p1[2] / 0.5)
                # Color transitions from smoke grey at tail to radiant flame near head
                flame_col = lerp_color(COLOR_SMOKE, self.color, t * age_factor)
                width = max(1, int(1.0 + 2.0 * t))

                x1 = int(p1[0] + offset_x)
                y1 = int(p1[1] + offset_y)
                x2 = int(p2[0] + offset_x)
                y2 = int(p2[1] + offset_y)

                pygame.draw.line(surface, flame_col, (x1, y1), (x2, y2), width)

        # 2. Draw glowing rocket head
        if not self.completed:
            hx = int(self.head_x + offset_x)
            hy = int(self.head_y + offset_y)

            glow_rad = int(self.head_size * 2 + 3)
            glow_surf = pygame.Surface((glow_rad * 2, glow_rad * 2), pygame.SRCALPHA)
            center = glow_rad

            # Outer exhaust flame halo
            pygame.draw.circle(glow_surf, (*self.color, 160), (center, center), glow_rad)
            # Inner white rocket point
            pygame.draw.circle(glow_surf, (*COLOR_ROCKET_HEAD, 255), (center, center), max(1, int(self.head_size)))

            surface.blit(glow_surf, (hx - center, hy - center))


class VFXManager:
    """High-Performance Visual Feedback and Juice Engine for Tactical Air Defense.

    Features:
    - Explosion Flak & Shockwaves with 3-frame bloom, expanding rings, and ember shrapnel.
    - Camera Trauma Screen Shake implementing the T^2 trauma model.
    - Missile Flight Contrails & Tracers.
    - Animated Tactical Targeting Lead Reticle with rotating brackets and marching dashed lead vector.
    - Emergency Base Damage Vignette with pulsing CRT edge glow when base HP < 30.
    """

    def __init__(self, max_offset: float = 15.0, decay_rate: float = 1.0):
        # Camera Trauma (T^2 model)
        self.trauma: float = 0.0
        self.decay_rate: float = float(decay_rate)
        self.max_offset: float = float(max_offset)
        self.time: float = 0.0

        # VFX Entities
        self.particles: List[ShrapnelParticle] = []
        self.shockwaves: List[ShockwaveRing] = []
        self.flash_blooms: List[FlashBloom] = []
        self.tracers: List[MissileTracer] = []

        # Font setup for HUD targeting reticle
        if not pygame.font.get_init():
            try:
                pygame.font.init()
            except Exception:
                pass

        try:
            self.font_reticle = pygame.font.SysFont('consolas', 10, bold=True)
            self.font_warn = pygame.font.SysFont('consolas', 14, bold=True)
        except Exception:
            try:
                self.font_reticle = pygame.font.Font(None, 14)
                self.font_warn = pygame.font.Font(None, 20)
            except Exception:
                self.font_reticle = None
                self.font_warn = None

        # Cached Vignette Surface for zero-allocation 60 FPS performance
        self._vignette_surface: Optional[pygame.Surface] = None
        self._vignette_size: Tuple[int, int] = (0, 0)

    # --------------------------------------------------------------------------
    # a. Explosion Flak & Shockwaves
    # --------------------------------------------------------------------------
    def create_explosion(self, x: float, y: float, is_heavy: bool = False,
                         color: Optional[Tuple[int, int, int]] = None):
        """Spawns an expanding circular shockwave ring, shrapnel ember particles,
        and epicenter flash bloom.

        Args:
            x, y: Epicenter coordinates.
            is_heavy: If True, triggers large detonation (e.g. ICBM, TBM, base hit).
            color: Optional custom color tint for particles/shockwave.
        """
        # 1. Shockwave Ring
        if is_heavy:
            start_rad, max_rad, start_w, end_w = 8.0, 75.0, 4.0, 1.0
            sw_life = 0.55
        else:
            # Specification: radius grows from 5 to 45px, width from 3 to 1px, alpha fades to 0
            start_rad, max_rad, start_w, end_w = 5.0, 45.0, 3.0, 1.0
            sw_life = 0.40

        sw_color = color if color else COLOR_WHITE
        self.shockwaves.append(
            ShockwaveRing(
                x, y,
                start_radius=start_rad,
                max_radius=max_rad,
                start_width=start_w,
                end_width=end_w,
                lifetime=sw_life,
                color=sw_color
            )
        )

        # 2. Shrapnel Ember Particles
        # Specification: Spawns 25 to 50 shrapnel ember particles (heavy: 55 to 90)
        particle_count = random.randint(55, 90) if is_heavy else random.randint(25, 50)
        min_speed = 70.0 if is_heavy else 45.0
        max_speed = 360.0 if is_heavy else 240.0

        for _ in range(particle_count):
            angle = random.uniform(0.0, 2.0 * math.pi)
            speed = random.uniform(min_speed, max_speed)
            vx = speed * math.cos(angle)
            vy = speed * math.sin(angle)

            lifetime = random.uniform(0.35, 0.85) if is_heavy else random.uniform(0.25, 0.65)
            p_size = random.uniform(2.5, 4.0) if is_heavy else random.uniform(1.8, 3.0)
            drag = random.uniform(1.4, 2.2)
            gravity = random.uniform(15.0, 35.0)
            drift_x = random.uniform(-10.0, 10.0)

            self.particles.append(
                ShrapnelParticle(
                    x=x, y=y,
                    vx=vx, vy=vy,
                    lifetime=lifetime,
                    size=p_size,
                    drag=drag,
                    gravity=gravity,
                    drift_x=drift_x,
                    custom_color=color
                )
            )

        # 3. Flash Bloom at epicenter for 3 frames
        bloom_radius = 42.0 if is_heavy else 24.0
        bloom_color = color if color else (255, 255, 240)
        self.flash_blooms.append(
            FlashBloom(x, y, max_radius=bloom_radius, total_frames=3, color=bloom_color)
        )

    def add_shockwave(self, x: float, y: float, max_radius: float = 45.0,
                      start_radius: float = 5.0, start_width: float = 3.0,
                      end_width: float = 1.0, lifetime: float = 0.6,
                      color: Tuple[int, int, int] = (255, 255, 255)) -> ShockwaveRing:
        """Adds an independent expanding shockwave ring to the scene."""
        sw = ShockwaveRing(
            x=x, y=y,
            start_radius=start_radius,
            max_radius=max_radius,
            start_width=start_width,
            end_width=end_width,
            lifetime=lifetime,
            color=color
        )
        self.shockwaves.append(sw)
        return sw

    # --------------------------------------------------------------------------
    # b. Camera Trauma Screen Shake (T^2 Model)
    # --------------------------------------------------------------------------
    def add_trauma(self, amount: float):
        """Adds trauma according to the T^2 trauma screen shake model.

        Typical values:
        - Base hit: +0.6
        - ICBM detonation: +0.8
        - Normal kill: +0.15
        """
        self.trauma = min(1.0, max(0.0, self.trauma + float(amount)))

    def get_camera_offset(self) -> Tuple[float, float]:
        """Returns (dx, dy) proportional to trauma^2 * max_offset.
        Uses randomized directional jitter when trauma > 0.
        """
        if self.trauma <= 0.001:
            return 0.0, 0.0

        shake_mag = (self.trauma ** 2) * self.max_offset
        angle = random.uniform(0.0, 2.0 * math.pi)
        dist = random.uniform(0.6, 1.0) * shake_mag
        return dist * math.cos(angle), dist * math.sin(angle)

    # --------------------------------------------------------------------------
    # c. Missile Flight Contrails & Tracers
    # --------------------------------------------------------------------------
    def add_missile_tracer(self, start_pos: Tuple[float, float],
                           target_pos: Tuple[float, float],
                           duration_ticks: int = 30,
                           color: Optional[Tuple[int, int, int]] = None):
        """Spawns an animated missile tracer with glowing rocket head and fading contrails."""
        tracer_color = color if color else COLOR_ROCKET_FLAME
        self.tracers.append(
            MissileTracer(start_pos, target_pos, duration_ticks=duration_ticks, color=tracer_color)
        )

    # --------------------------------------------------------------------------
    # d. Targeting Lead Reticle
    # --------------------------------------------------------------------------
    def draw_lead_reticle(self, surface: pygame.Surface,
                          target_pos: Tuple[float, float],
                          lead_pos: Tuple[float, float],
                          id_code: str):
        """Draws animated rotating/pulsing targeting brackets around contact,
        with a marching dashed lead vector to the calculated future intercept point.
        """
        tx, ty = float(target_pos[0]), float(target_pos[1])
        lx, ly = float(lead_pos[0]), float(lead_pos[1])

        # 1. Pulsing Bracket Radius
        pulse = math.sin(self.time * 6.5)
        bracket_rad = 18.0 + 2.5 * pulse
        bracket_len = 6.0

        # Tactical targeting color
        hud_color = COLOR_HUD_CYAN

        # 4 Corner Brackets: Top-Left, Top-Right, Bottom-Left, Bottom-Right
        corners = [
            # Top-Left
            [(tx - bracket_rad, ty - bracket_rad + bracket_len),
             (tx - bracket_rad, ty - bracket_rad),
             (tx - bracket_rad + bracket_len, ty - bracket_rad)],
            # Top-Right
            [(tx + bracket_rad - bracket_len, ty - bracket_rad),
             (tx + bracket_rad, ty - bracket_rad),
             (tx + bracket_rad, ty - bracket_rad + bracket_len)],
            # Bottom-Left
            [(tx - bracket_rad, ty + bracket_rad - bracket_len),
             (tx - bracket_rad, ty + bracket_rad),
             (tx - bracket_rad + bracket_len, ty + bracket_rad)],
            # Bottom-Right
            [(tx + bracket_rad - bracket_len, ty + bracket_rad),
             (tx + bracket_rad, ty + bracket_rad),
             (tx + bracket_rad, ty + bracket_rad - bracket_len)]
        ]

        for pts in corners:
            pygame.draw.lines(surface, hud_color, False, pts, 2)

        # 2. Animated Rotating Outer Notches
        rot_angle = (self.time * 50.0) % 360.0
        notch_r1 = bracket_rad + 3.0
        notch_r2 = bracket_rad + 7.0
        for i in range(4):
            ang_rad = math.radians(rot_angle + i * 90.0)
            cos_a = math.cos(ang_rad)
            sin_a = math.sin(ang_rad)
            p1 = (tx + notch_r1 * cos_a, ty + notch_r1 * sin_a)
            p2 = (tx + notch_r2 * cos_a, ty + notch_r2 * sin_a)
            pygame.draw.line(surface, COLOR_HUD_AMBER, p1, p2, 1)

        # 3. Dashed Lead Intercept Vector
        dx = lx - tx
        dy = ly - ty
        dist = math.hypot(dx, dy)

        if dist > 3.0:
            ux = dx / dist
            uy = dy / dist
            dash_len = 6.0
            gap_len = 4.0
            cycle = dash_len + gap_len
            marching_offset = (self.time * 24.0) % cycle

            curr_d = marching_offset
            while curr_d < dist:
                d_end = min(dist, curr_d + dash_len)
                if d_end > curr_d:
                    sp = (tx + ux * curr_d, ty + uy * curr_d)
                    ep = (tx + ux * d_end, ty + uy * d_end)
                    pygame.draw.line(surface, COLOR_HUD_AMBER, sp, ep, 1)
                curr_d += cycle

            # Lead Pip Reticle at Intercept Position
            pip_x, pip_y = int(round(lx)), int(round(ly))
            pygame.draw.circle(surface, COLOR_HUD_AMBER, (pip_x, pip_y), 4, 1)
            pygame.draw.line(surface, COLOR_HUD_AMBER, (pip_x - 6, pip_y), (pip_x + 6, pip_y), 1)
            pygame.draw.line(surface, COLOR_HUD_AMBER, (pip_x, pip_y - 6), (pip_x, pip_y + 6), 1)

            if self.font_reticle:
                lead_txt = self.font_reticle.render("LEAD", True, COLOR_HUD_AMBER)
                surface.blit(lead_txt, (pip_x + 7, pip_y - 5))

        # 4. Target ID Code Label
        if self.font_reticle and id_code:
            tag_str = f"[{id_code}]"
            tag_surf = self.font_reticle.render(tag_str, True, hud_color)
            surface.blit(tag_surf, (int(tx + bracket_rad + 4), int(ty - bracket_rad - 2)))

    # --------------------------------------------------------------------------
    # e. Emergency Base Damage Vignette
    # --------------------------------------------------------------------------
    def _rebuild_vignette_surface(self, width: int, height: int):
        """Generates a cached perimeter edge gradient surface."""
        self._vignette_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        glow_depth = 55

        # Multi-layer rectangular perimeter gradient
        for step in range(glow_depth):
            t = step / float(glow_depth)
            # Quadratic falloff toward interior
            alpha = int(255 * ((1.0 - t) ** 1.8))
            rect = pygame.Rect(step, step, width - 2 * step, height - 2 * step)
            if rect.width > 0 and rect.height > 0:
                pygame.draw.rect(self._vignette_surface, (*COLOR_VIGNETTE_RED, alpha), rect, 1)

        self._vignette_size = (width, height)

    def draw_damage_vignette(self, surface: pygame.Surface, base_hp: float):
        """Renders a pulsing red CRT edge glow around the screen perimeter
        when base HP < 30. Intensity and pulse rate escalate as HP drops.
        """
        if base_hp >= 30:
            return

        w, h = surface.get_size()
        if self._vignette_surface is None or self._vignette_size != (w, h):
            self._rebuild_vignette_surface(w, h)

        # Danger severity from 0.0 (hp=30) to 1.0 (hp=0)
        severity = max(0.0, min(1.0, (30.0 - float(base_hp)) / 30.0))

        # Escalating pulse frequency (4 Hz to 12 Hz)
        pulse_freq = 4.0 + 8.0 * severity
        pulse = 0.55 + 0.45 * math.sin(self.time * pulse_freq)
        alpha = max(10, min(240, int(210 * severity * pulse)))

        if self._vignette_surface and alpha > 0:
            self._vignette_surface.set_alpha(alpha)
            surface.blit(self._vignette_surface, (0, 0))

        # Critical damage warning banner when base is near collapse (HP < 15)
        if base_hp < 15 and self.font_warn and pulse > 0.7:
            warn_str = f"! WARNING: BASE INTEGRITY CRITICAL [{int(base_hp)}%] !"
            warn_surf = self.font_warn.render(warn_str, True, (255, 60, 60))
            wx = (w - warn_surf.get_width()) // 2
            surface.blit(warn_surf, (wx, 18))

    # --------------------------------------------------------------------------
    # f. Update and Render Methods
    # --------------------------------------------------------------------------
    def update(self, dt: float):
        """Updates physics, decay, and lifetimes of all active visual effects."""
        self.time += dt

        # Camera trauma exponential decay
        if self.trauma > 0.0:
            self.trauma = max(0.0, self.trauma - self.decay_rate * dt)

        # Update Shockwaves
        self.shockwaves = [sw for sw in self.shockwaves if sw.update(dt)]

        # Update Shrapnel Particles
        self.particles = [p for p in self.particles if p.update(dt)]

        # Update Flash Blooms
        self.flash_blooms = [fb for fb in self.flash_blooms if fb.update(dt)]

        # Update Missile Tracers
        self.tracers = [tr for tr in self.tracers if tr.update(dt)]

    def draw(self, surface: pygame.Surface, cx_offset: float = 0.0, cy_offset: float = 0.0):
        """Renders all active visual effects to the target surface."""
        # 1. Shockwaves (rendered beneath particles)
        for sw in self.shockwaves:
            sw.draw(surface, cx_offset, cy_offset)

        # 2. Missile Contrails & Tracers
        for tr in self.tracers:
            tr.draw(surface, cx_offset, cy_offset)

        # 3. Shrapnel Ember Particles
        for p in self.particles:
            p.draw(surface, cx_offset, cy_offset)

        # 4. Epicenter Flash Blooms
        for fb in self.flash_blooms:
            fb.draw(surface, cx_offset, cy_offset)

    # --------------------------------------------------------------------------
    # Utility Methods
    # --------------------------------------------------------------------------
    def clear(self):
        """Clears all active visual effects and resets camera trauma."""
        self.trauma = 0.0
        self.particles.clear()
        self.shockwaves.clear()
        self.flash_blooms.clear()
        self.tracers.clear()

    @property
    def active_effect_count(self) -> int:
        """Returns the total number of currently active visual entities."""
        return len(self.particles) + len(self.shockwaves) + len(self.flash_blooms) + len(self.tracers)

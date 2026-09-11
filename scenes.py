"""Scene / state machine for pre-simulation UI (main menu, etc.).

Runs entirely BEFORE start_radar() is invoked. This module intentionally
knows nothing about, and never touches, the internals of radar_ui.py's
start_radar() -- it only decides which profile to hand off with once the
player picks a mode.
"""
import sys
import pygame

from config import GameConfig
from map_manager import MapManager
from camera_director import CameraDirector
from profiles import SPECTATOR_PROFILE, PLAYER_PROFILE

# --- Dark tactical C2 palette -------------------------------------------------
COLOR_BG = (2, 4, 3)
COLOR_GREEN = (0, 255, 140)
COLOR_GREEN_DIM = (0, 110, 65)
COLOR_AMBER = (255, 180, 40)
COLOR_SCANLINE = (0, 0, 0, 40)
COLOR_VIGNETTE = (0, 0, 0, 160)


class Scene:
    """Base class for menu-style scenes running before the simulation starts."""

    def __init__(self):
        self.next_scene = None   # set to a Scene instance to transition
        self.done = False        # set True to hand off out of the scene manager
        self.result = None       # arbitrary payload for the scene manager to read

    def handle_event(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, screen):
        pass


class MenuScene(Scene):
    ITEMS = [
        ("SPECTATOR MODE", SPECTATOR_PROFILE, "AUTONOMOUS AI SHOWCASE // VIEW ONLY"),
        ("PLAYER MODE", PLAYER_PROFILE, "MANUAL C2 // YOU HOLD THE TRIGGER"),
        ("EXIT", None, "TERMINATE SIMULATION"),
    ]

    def __init__(self, width, height):
        super().__init__()
        self.width = width
        self.height = height
        self.selected = 0
        self.map_mgr = MapManager()
        self.map_mgr.map_mode = self.map_mgr.MODE_FULL_TACTICAL
        self.camera = CameraDirector()
        self._t = 0.0

        self.font_xs = pygame.font.SysFont('consolas', 10)
        self.font_sm = pygame.font.SysFont('consolas', 12)
        self.font_md = pygame.font.SysFont('consolas', 16, bold=True)
        self.font_title = pygame.font.SysFont('consolas', 64, bold=True)
        self.font_subtitle = pygame.font.SysFont('consolas', 18, bold=True)
        self.font_item = pygame.font.SysFont('consolas', 26, bold=True)
        self.font_desc = pygame.font.SysFont('consolas', 14)
        self.font_footer = pygame.font.SysFont('consolas', 12)

        self._item_rects = [None] * len(self.ITEMS)
        self._scanline_surface = None
        self._vignette_surface = None

    # -- input -----------------------------------------------------------
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.done = True
            self.result = ("EXIT", None)
            return

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.ITEMS)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.ITEMS)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._activate(self.selected)
            elif event.key == pygame.K_ESCAPE:
                self.done = True
                self.result = ("EXIT", None)

        elif event.type == pygame.MOUSEMOTION:
            for i, rect in enumerate(self._item_rects):
                if rect and rect.collidepoint(event.pos):
                    self.selected = i
                    break

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self._item_rects):
                if rect and rect.collidepoint(event.pos):
                    self.selected = i
                    self._activate(i)
                    break

    def _activate(self, index):
        label, profile, _desc = self.ITEMS[index]
        if label == "EXIT":
            self.done = True
            self.result = ("EXIT", None)
        else:
            self.done = True
            self.result = (label, profile)

    # -- update/draw -------------------------------------------------------
    def update(self, dt):
        self._t += dt
        self.camera.update(dt)

    def draw(self, screen):
        width, height = screen.get_size()
        screen.fill(COLOR_BG)

        cx, cy, zoom = self.camera.values
        # Camera drift is expressed as an offset of the map's own pan center,
        # producing a slow filmic pan/zoom across real map features.
        self.map_mgr.render(screen, width // 2 - cx * zoom, height // 2 + cy * zoom,
                             zoom, width, height, self.font_xs, self.font_sm, self.font_md)

        self._draw_dark_overlay(screen, width, height)
        self._draw_title(screen, width, height)
        self._draw_menu(screen, width, height)
        self._draw_footer(screen, width, height)
        self._draw_scanlines(screen, width, height)
        self._draw_vignette(screen, width, height)

    def _draw_dark_overlay(self, screen, width, height):
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 5, 3, 120))
        screen.blit(overlay, (0, 0))

    def _draw_title(self, screen, width, height):
        title_surf = self.font_title.render("AEGIS", True, COLOR_GREEN)
        screen.blit(title_surf, (width // 2 - title_surf.get_width() // 2, height // 6))

        subtitle_surf = self.font_subtitle.render(
            "TACTICAL AIR DEFENSE C2", True, COLOR_AMBER)
        screen.blit(subtitle_surf,
                    (width // 2 - subtitle_surf.get_width() // 2,
                     height // 6 + title_surf.get_height() + 6))

    def _draw_menu(self, screen, width, height):
        start_y = height // 2 - 20
        spacing = 56

        for i, (label, _profile, desc) in enumerate(self.ITEMS):
            is_selected = (i == self.selected)
            color = COLOR_AMBER if is_selected else COLOR_GREEN_DIM
            text = f"{'>> ' if is_selected else '   '}{label}"
            item_surf = self.font_item.render(text, True, color)
            item_rect = item_surf.get_rect(
                center=(width // 2, start_y + i * spacing))
            screen.blit(item_surf, item_rect)
            # Hit-test rect a bit taller/wider than the glyphs for easy mouse use.
            self._item_rects[i] = item_rect.inflate(60, 20)

        desc_text = self.ITEMS[self.selected][2]
        desc_surf = self.font_desc.render(desc_text, True, COLOR_GREEN)
        screen.blit(desc_surf,
                    (width // 2 - desc_surf.get_width() // 2,
                     start_y + len(self.ITEMS) * spacing + 20))

    def _draw_footer(self, screen, width, height):
        footer_text = f"AEGIS v{GameConfig.VERSION}  //  RTAF SOC"
        footer_surf = self.font_footer.render(footer_text, True, COLOR_GREEN_DIM)
        screen.blit(footer_surf, (12, height - footer_surf.get_height() - 8))

    def _draw_scanlines(self, screen, width, height):
        if self._scanline_surface is None or self._scanline_surface.get_size() != (width, height):
            surf = pygame.Surface((width, height), pygame.SRCALPHA)
            for y in range(0, height, 3):
                pygame.draw.line(surf, COLOR_SCANLINE, (0, y), (width, y))
            self._scanline_surface = surf
        screen.blit(self._scanline_surface, (0, 0))

    def _draw_vignette(self, screen, width, height):
        if self._vignette_surface is None or self._vignette_surface.get_size() != (width, height):
            surf = pygame.Surface((width, height), pygame.SRCALPHA)
            steps = 60
            for i in range(steps):
                t = i / steps
                alpha = int(COLOR_VIGNETTE[3] * (t ** 2))
                rect = pygame.Rect(i, i, width - 2 * i, height - 2 * i)
                if rect.width <= 0 or rect.height <= 0:
                    break
                pygame.draw.rect(surf, (0, 0, 0, alpha), rect, width=2)
            self._vignette_surface = surf
        screen.blit(self._vignette_surface, (0, 0))


class SceneManager:
    """Owns the currently active scene and runs its own 60fps loop until
    the scene signals completion (`scene.done`), at which point the manager
    returns the scene's result to the caller."""

    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()

    def run(self, scene):
        while not scene.done:
            dt = self.clock.tick(60) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    scene.done = True
                    scene.result = ("EXIT", None)
                    break
                if event.type == pygame.VIDEORESIZE:
                    scene.width, scene.height = event.w, event.h
                scene.handle_event(event)

            scene.update(dt)
            scene.draw(self.screen)
            pygame.display.flip()

        return scene.result

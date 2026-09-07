import pygame
import math
import sys
import random
import json
import os
import re
from command_center import CommandCenter
from config import GameConfig
from targets import AWACS, AntiRadiationMissile, CruiseMissile
from sound_engine import SoundManager
from visual_effects import VFXManager
from map_manager import MapManager

# Fix DPI scaling issues on Windows
try:
    import ctypes
    ctypes.windll.user32.SetProcessDPIAware()
except:
    pass

def clean_ansi(text):
    return re.sub(r'\033\[[0-9;]*m', '', text)

def get_log_color(log_str):
    if "\033[41" in log_str or "\033[91" in log_str: return (255, 80, 80)
    if "\033[92" in log_str: return (80, 255, 80)
    if "\033[94" in log_str: return (100, 180, 255)
    if "\033[95" in log_str: return (220, 100, 220)
    if "\033[93" in log_str or "\033[43" in log_str: return (255, 220, 50)
    if "\033[96" in log_str: return (100, 255, 255)
    if "\033[90" in log_str: return (150, 150, 150)
    return (200, 200, 200)

def lerp_color(c1, c2, t):
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t)
    )

# Real-world high-fidelity map engine
global_map_manager = MapManager()

def load_real_map():
    shapes = []
    for rings in global_map_manager.country_polys.values():
        shapes.extend(rings)
    peaks = [(x, y, name) for x, y, name in global_map_manager.peaks_km]
    airbases = [(x, y, name) for x, y, name, btype, col in global_map_manager.airbases]
    return shapes, peaks, airbases

MAP_SHAPES_KM, MAP_PEAKS_KM, MAP_AIRBASES_KM = load_real_map()
MAP_CONTOURS_KM = global_map_manager.contours_km

def start_radar():
    pygame.init()
    
    info = pygame.display.Info()
    MONITOR_W, MONITOR_H = info.current_w, info.current_h
    
    # start windowed at 90% of screen
    WIDTH, HEIGHT = int(MONITOR_W * 0.9), int(MONITOR_H * 0.9)
    is_fullscreen = False
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE) 
    pygame.display.set_caption(f"AEGIS Tactical Air Defense Radar v{GameConfig.VERSION}")

    BG_COLOR = (0, 0, 0) # Pitch black like real radar
    GRID_COLOR = (0, 40, 0) # Very faint green for grid
    RADAR_COLOR = (0, 200, 50)
    MISSILE_COLOR = (255, 120, 0)
    
    RADAR_AREA = WIDTH 
    RADAR_MAX_KM = 800.0 
    
    camera_x = 0.0
    camera_y = 0.0
    zoom_level = 0.8
    
    def km_to_px(km): return km * zoom_level

    font_xs = pygame.font.SysFont('consolas', 10)
    font_sm = pygame.font.SysFont('consolas', 12)
    font_md = pygame.font.SysFont('consolas', 16, bold=True)
    font_lg = pygame.font.SysFont('consolas', 22, bold=True)

    cmd = CommandCenter()
    sound_mgr = SoundManager()
    vfx_mgr = VFXManager()
    map_mgr = global_map_manager
    sweep_angle = 0.0
    sweep_speed = 2.8
    clock = pygame.time.Clock()
    LAST_TICK_TIME = pygame.time.get_ticks()

    selected_contact = None  
    CX = WIDTH // 2
    CY = HEIGHT // 2
    show_upgrades = False

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        current_time = pygame.time.get_ticks()

        # Update Visual FX
        vfx_mgr.update(dt)

        # ---------------------------------------------------
        # Process Event Bus from Simulation Core
        # ---------------------------------------------------
        while cmd.event_bus:
            ev = cmd.event_bus.pop(0)
            etype = ev.get("type")
            if etype == "INTERCEPT_KILL":
                tx = ev.get("x", 0)
                ty = ev.get("y", 0)
                spx = CX + km_to_px(tx)
                spy = CY - km_to_px(ty)
                ttype = ev.get("threat_type", "")
                is_heavy = ttype in ["ICBM", "TacticalBM", "CruiseMissile"]
                vfx_mgr.create_explosion(spx, spy, is_heavy=is_heavy)
                sound_mgr.play_explosion(heavy=is_heavy)
                vfx_mgr.add_trauma(0.35 if is_heavy else 0.15)
                sound_mgr.radio_callout("Splash one bandit!")
            elif etype == "BASE_DAMAGE":
                sound_mgr.play_explosion(heavy=True)
                vfx_mgr.add_trauma(0.7)
                vfx_mgr.create_explosion(CX, CY, is_heavy=True)
                sound_mgr.radio_callout("Warning! Command base hit!")
            elif etype == "MISSILE_LAUNCH":
                sound_mgr.play_launch()
                tx = ev.get("target_x", 0)
                ty = ev.get("target_y", 0)
                vfx_mgr.add_missile_tracer((CX, CY), (CX + km_to_px(tx), CY - km_to_px(ty)), duration_ticks=35)
                sound_mgr.radio_callout("Fox Two away!")
            elif etype == "CIWS_FIRE":
                sound_mgr.play_ciws()
                vfx_mgr.add_trauma(0.06)
            elif etype == "DEFCON_CHANGE":
                d = ev.get("defcon", 5)
                if d == 1:
                    sound_mgr.start_alarm()
                    sound_mgr.radio_callout("Vampire! Vampire inbound!")
                elif d > 2:
                    sound_mgr.stop_alarm()
            elif etype == "PROMOTION":
                r = ev.get("rank", "Officer")
                sound_mgr.radio_callout(f"Attention on deck! Promoted to {r}!")
            elif etype == "COURT_MARTIAL":
                sound_mgr.start_alarm()
                sound_mgr.radio_callout("Cease fire! Civilian flight splashed!")

        # ---------------------------------------------------
        # Game Tick Update
        # ---------------------------------------------------
        if current_time - LAST_TICK_TIME >= 1000:
            if cmd.base_hp > 0:
                cmd.tick_count += 1
                cmd.detect_airspace()
                cmd.process_reloads()
                cmd.process_personnel()
                cmd.process_engagements()
                cmd.process_auto_ciws()
                cmd.update_world()
            
            if selected_contact and not selected_contact.active:
                selected_contact = None
                
            LAST_TICK_TIME = current_time

        # ---------------------------------------------------
        # Input Handling (Manual Override, Resize & Selection)
        # ---------------------------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False; sys.exit()

            # Window resizing event
            if event.type == pygame.VIDEORESIZE:
                if not is_fullscreen:
                    WIDTH, HEIGHT = event.w, event.h
                    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
                    RADAR_AREA = WIDTH
                    RADAR_RADIUS_PX = (HEIGHT // 2) - 20
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: running = False; sys.exit()
                
                # Fire weapon at selected target
                if selected_contact:
                    wpn = None
                    if event.key == pygame.K_1: wpn = 'THAAD'
                    elif event.key == pygame.K_2: wpn = 'SAM'
                    elif event.key == pygame.K_3: wpn = 'CIWS'
                    elif event.key == pygame.K_4: wpn = 'FIGHTER' 
                    
                    if wpn:
                        cmd.manual_override_fire(selected_contact, wpn)

                # abort engagement
                if event.key == pygame.K_BACKSPACE and selected_contact:
                    cmd.manual_override_abort(selected_contact)

                # Tactical Systems Controls
                if event.key == pygame.K_e:
                    cmd.toggle_emcon()
                elif event.key == pygame.K_s:
                    cmd.toggle_salvo()
                elif event.key == pygame.K_d:
                    cmd.deploy_decoy()
                elif event.key == pygame.K_u:
                    is_muted = sound_mgr.toggle_mute()
                    cmd.add_log(f"\033[93m[AUDIO] Audio muted: {is_muted}\033[0m")
                elif event.key == pygame.K_TAB:
                    show_upgrades = not show_upgrades
                elif event.key == pygame.K_F1:
                    m = cmd.mission_mgr.cycle_mission(cmd)
                    selected_contact = None
                    sound_mgr.radio_callout("New operational orders received.")
                    cmd.add_log(f"\033[93m[CAMPAIGN] ACTIVATED: {m.name}\033[0m")
                elif event.key == pygame.K_F2:
                    mode, mode_name = map_mgr.cycle_mode()
                    sound_mgr.radio_callout("Map layer toggled.")
                    cmd.add_log(f"\033[96m[MAP] DISPLAY MODE: {mode_name}\033[0m")
                elif event.key == pygame.K_r:
                    cmd = CommandCenter()
                    selected_contact = None
                    sound_mgr.stop_alarm()
                    cmd.add_log("\033[92m[SYS] SORTIE RE-INITIALIZED. COMMAND CENTER ONLINE.\033[0m")

                # Tech Upgrades Purchasing (when Upgrades panel is open)
                if show_upgrades:
                    upgrade_map = {
                        pygame.K_1: "AESA_RANGE",
                        pygame.K_2: "DOPPLER_FILTER",
                        pygame.K_3: "DECOY_PACK",
                        pygame.K_4: "RAPID_CIWS",
                        pygame.K_5: "AESA_SEEKERS"
                    }
                    if event.key in upgrade_map:
                        uid = upgrade_map[event.key]
                        ok, reason = cmd.unlock_upgrade(uid)
                        if ok:
                            sound_mgr.radio_callout("Systems upgraded.")
                        else:
                            cmd.add_log(f"\033[91m[UPGRADE] {reason}\033[0m")

                # dev: manual threat spawn
                if not selected_contact:
                    if event.key == pygame.K_5: cmd.manual_spawn("ICBM")
                    elif event.key == pygame.K_6: cmd.manual_spawn("FIGHTER")
                    elif event.key == pygame.K_7: cmd.manual_spawn("DRONE")
                    elif event.key == pygame.K_8: cmd.manual_spawn("AIRLINER")
                    elif event.key == pygame.K_9: cmd.manual_spawn("EW")
                    elif event.key == pygame.K_0: cmd.manual_spawn("AWACS")
                    elif event.key == pygame.K_m: cmd.manual_spawn("ARM")
                    elif event.key == pygame.K_c: cmd.manual_spawn("CRUISE")
                    elif event.key == pygame.K_w: cmd.manual_spawn("WAVE")
                    elif event.key == pygame.K_p:
                        cmd.tick_count = 360
                        cmd.detect_airspace()
                        cmd.add_log("\033[41;97m[COMMAND] PHASE 3 (WARTIME) ENGAGED. AIRSPACE CLOSED. DEFCON 1.\033[0m")
                        sound_mgr.start_alarm()
                        sound_mgr.radio_callout("Vampire! Vampire inbound!")
                # Toggle fullscreen mode
                if event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    if is_fullscreen:
                        # (0,0) tells pygame to fill the display natively
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                        info_fs = pygame.display.Info()
                        WIDTH, HEIGHT = info_fs.current_w, info_fs.current_h 
                    else:
                        WIDTH, HEIGHT = int(MONITOR_W * 0.9), int(MONITOR_H * 0.9) 
                        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
                    
                    RADAR_AREA = WIDTH

                # Restart game after base is destroyed
                if event.key == pygame.K_r and cmd.base_hp <= 0:
                    cmd = CommandCenter()
                    selected_contact = None
                    sweep_angle = 0.0
                    LAST_TICK_TIME = pygame.time.get_ticks()

            if event.type == pygame.MOUSEWHEEL:
                zoom_level += event.y * 0.15
                zoom_level = max(0.2, min(10.0, zoom_level))

            # Handle mouse click for selection
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                
                # Check Flight Info Panel buttons first
                panel_clicked = False
                if selected_contact:
                    panel_x, panel_y = 20, 120
                    btn_y = panel_y + 165
                    labels = ["H", "S", "F", "U"]
                    for i, lbl in enumerate(labels):
                        bx = panel_x + 70 + (i * 30)
                        brect = pygame.Rect(bx, btn_y, 25, 20)
                        if brect.collidepoint(mx, my):
                            if lbl == "H": selected_contact.status = "HOSTILE"
                            elif lbl == "S": selected_contact.status = "SUSPECT"
                            elif lbl == "F": selected_contact.status = "FRIENDLY"
                            elif lbl == "U": selected_contact.status = "UNIDENTIFIED"
                            panel_clicked = True
                            cmd.add_log(f"\033[94m[SYS] OPERATOR CHANGED {selected_contact.id_code} ID TO {selected_contact.status}\033[0m")
                            break
                
                # Check Active Operations Panel Click
                list_w, list_h = 360, 480
                list_x, list_y = 20, HEIGHT - list_h - 20
                if not panel_clicked and list_x <= mx <= list_x + list_w and list_y <= my <= list_y + list_h:
                    sorted_contacts = sorted(cmd.contacts, key=lambda c: c.calculate_threat_score(), reverse=True)
                    click_idx = (my - (list_y + 30)) // 22 # Updated row height
                    if 0 <= click_idx < len(sorted_contacts[:20]):
                        selected_contact = sorted_contacts[click_idx]
                        panel_clicked = True
                            
                if not panel_clicked and mx < RADAR_AREA:
                    closest_c = None
                    min_dist = 20 
                    for c in cmd.contacts:
                        if not c.active: continue
                        tx = CX + km_to_px(c.x_km)
                        ty = CY - km_to_px(c.y_km)
                        
                        dist_to_mouse = math.hypot(mx - tx, my - ty)
                        if dist_to_mouse < min_dist:
                            min_dist = dist_to_mouse
                            closest_c = c
                    selected_contact = closest_c

        # Smooth panning with WASD, Arrows, or Mouse Drag
        keys = pygame.key.get_pressed()
        pan_speed = 10
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: camera_x += pan_speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: camera_x -= pan_speed
        if keys[pygame.K_UP] or keys[pygame.K_w]: camera_y += pan_speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: camera_y -= pan_speed

        mouse_dx, mouse_dy = pygame.mouse.get_rel()
        if pygame.mouse.get_pressed()[1] or pygame.mouse.get_pressed()[2]: # Middle or Right Click
            camera_x += mouse_dx
            camera_y += mouse_dy

        shake_x, shake_y = vfx_mgr.get_camera_offset()
        CX = (WIDTH // 2) + int(camera_x + shake_x)
        CY = (HEIGHT // 2) + int(camera_y + shake_y)

        screen.fill(BG_COLOR)

        # --- 1. Weapon Engagement Zones (WEZ) ---
        # Only display the Weapon Engagement Zones (WEZ)
        pygame.draw.circle(screen, (0, 30, 80), (CX, CY), int(km_to_px(400)), 1) # THAAD Optimal Range
        pygame.draw.circle(screen, (80, 80, 0), (CX, CY), int(km_to_px(200)), 1) # SAM Anti-Ballistic Range
        pygame.draw.circle(screen, (80, 50, 0), (CX, CY), int(km_to_px(80)), 1)  # SAM Anti-Aircraft Range
        pygame.draw.circle(screen, (80, 0, 0), (CX, CY), int(km_to_px(20)), 1)   # CIWS Range

        # Draw Real-World Tactical Map (Thailand, Neighbors, Coastlines, ADIZ, Bases)
        map_mgr.render(screen, CX, CY, zoom_level, WIDTH, HEIGHT, font_xs, font_sm, font_md)

        r_max = km_to_px(RADAR_MAX_KM)

        # --- 2. Rotary AESA Radar Sweep ---
        ew_active = any(getattr(c, 'is_heavy_ew', False) and c.active for c in cmd.contacts)
        
        if ew_active:
            sweep_speed = random.choice([-25, -10, 2.8, 15, 30, 60, -40]) # Glitch rotation
        else:
            sweep_speed = 2.8
            
        old_sweep_angle = sweep_angle
        sweep_angle = (sweep_angle + sweep_speed) % 360
        if old_sweep_angle > sweep_angle and not ew_active:
            sound_mgr.play_ping()

        # AESA Field of View (FOV) - e.g., +/- 60 degrees from mechanical boresight
        AESA_FOV = 60.0

        def angle_diff(a1, a2):
            diff = (a1 - a2 + 180) % 360 - 180
            return abs(diff)

        # --- Update brightness & detection for all contacts ---
        for c in cmd.contacts:
            if not c.active: continue
            bearing = getattr(c, 'bearing', getattr(c, 'heading', 0)) 
            
            # If target is within the AESA Field of View, it gets actively tracked
            if angle_diff(bearing, sweep_angle) <= AESA_FOV:
                c.visible_dist = c.distance_km
                c.brightness = 1.0 
                if not hasattr(c, 'trail'): c.trail = []
                
                # Record trail position occasionally
                if random.random() < 0.1:
                    c.trail.append((c.visible_dist, bearing))
                    if len(c.trail) > 8: c.trail.pop(0)
            else:
                if hasattr(c, 'brightness') and c.brightness > 0:
                    c.brightness = max(0.0, c.brightness - 0.005)  # Fade when out of FOV

        for eng in cmd.active_engagements:
            target = getattr(eng, 'target', None)
            if not target or not target.active: continue
            if not hasattr(eng, 'total_time'): eng.total_time = max(1, getattr(eng, 'time_to_impact', 1))
            
            # 60 FPS Visual Physics Interpolation for Missiles
            smooth_time = max(0, getattr(eng, 'time_to_impact', 0) - alpha)
            progress = 1.0 - (smooth_time / max(1, eng.total_time))
            bearing = getattr(target, 'bearing', getattr(target, 'heading', 0))
            
            if angle_diff(bearing, sweep_angle) <= AESA_FOV:
                ox = getattr(eng, 'origin_x_km', 0.0)
                oy = getattr(eng, 'origin_y_km', 0.0)
                
                target_x = getattr(target, 'prev_x_km', target.x_km) + (target.x_km - getattr(target, 'prev_x_km', target.x_km)) * alpha
                target_y = getattr(target, 'prev_y_km', target.y_km) + (target.y_km - getattr(target, 'prev_y_km', target.y_km)) * alpha
                
                eng.x_km = ox + (target_x - ox) * progress
                eng.y_km = oy + (target_y - oy) * progress
                eng.brightness = 1.0
                if not hasattr(eng, 'trail'): eng.trail = []
                if random.random() < 0.1:
                    eng.trail.append((eng.x_km, eng.y_km))
                    if len(eng.trail) > 8: eng.trail.pop(0)
            else:
                if hasattr(eng, 'brightness') and eng.brightness > 0:
                    eng.brightness = max(0.0, eng.brightness - 0.005)

        # --- AESA Random Search Beams (Electronic steering within FOV) ---
        for _ in range(12): 
            e_angle = random.uniform(-AESA_FOV, AESA_FOV)
            r_angle = (sweep_angle + e_angle) % 360
            r_len = km_to_px(RADAR_MAX_KM) * random.uniform(0.3, 0.95)
            bx = CX + r_len * math.sin(math.radians(r_angle))
            by = CY - r_len * math.cos(math.radians(r_angle))
            pygame.draw.line(screen, (0, 80, 40), (CX, CY), (bx, by), 1)

        # --- AESA Tracking Beams (Tracking targets within FOV) ---
        for c in cmd.contacts:
            if c.active and c.distance_km < RADAR_MAX_KM:
                target_bearing = getattr(c, 'bearing', 0)
                
                # Only track if the mechanical dish is pointing roughly towards it
                if angle_diff(target_bearing, sweep_angle) <= AESA_FOV:
                    dist_px = km_to_px(c.distance_km)
                    
                    b_color = (0, 180, 80) if c.status != "HOSTILE" else (200, 100, 0)
                    track_probability = 1.0 if selected_contact == c else 0.40
                    
                    track_count = 3 if selected_contact == c else 1
                    for _ in range(track_count):
                        if random.random() < track_probability:
                            jitter_angle = random.uniform(-1.5, 1.5)
                            jit_bearing = target_bearing + jitter_angle
                            tx_jit = CX + dist_px * math.sin(math.radians(jit_bearing))
                            ty_jit = CY - dist_px * math.cos(math.radians(jit_bearing))
                            pygame.draw.line(screen, b_color, (CX, CY), (tx_jit, ty_jit), 1)

        # Draw AESA FOV Boundaries Faintly
        fov_left = (sweep_angle - AESA_FOV) % 360
        fov_right = (sweep_angle + AESA_FOV) % 360
        r_max = km_to_px(RADAR_MAX_KM)
        lx = CX + r_max * math.sin(math.radians(fov_left))
        ly = CY - r_max * math.cos(math.radians(fov_left))
        rx = CX + r_max * math.sin(math.radians(fov_right))
        ry = CY - r_max * math.cos(math.radians(fov_right))
        pygame.draw.line(screen, (0, 60, 20), (CX, CY), (lx, ly), 1)
        pygame.draw.line(screen, (0, 60, 20), (CX, CY), (rx, ry), 1)

        # --- Main Sweep Line (Mechanical Boresight) ---
        alpha = min(1.0, (current_time - LAST_TICK_TIME) / 1000.0)
        # Retain main mechanical boresight visual
        end_x = CX + r_max * math.sin(math.radians(sweep_angle))
        end_y = CY - r_max * math.cos(math.radians(sweep_angle))
        pygame.draw.line(screen, (150, 255, 180), (CX, CY), (end_x, end_y), 3)

        # Draw fading sweep tail
        for i in range(1, 10):
            t_angle = (sweep_angle - (i * 3)) % 360
            t_alpha = 1.0 - (i / 10.0)
            t_color = (int(0 * t_alpha), int(200 * t_alpha), int(50 * t_alpha))
            tx = CX + r_max * math.sin(math.radians(t_angle))
            ty = CY - r_max * math.cos(math.radians(t_angle))
            pygame.draw.line(screen, t_color, (CX, CY), (tx, ty), 2)

        # --- 3. Contacts & EW Jamming ---
        ew_aircrafts = [c for c in cmd.contacts if c.active and getattr(c, 'status', '') == 'HOSTILE' and "EW" in getattr(c, 'type_name', '')]

        # full-screen green particle noise when any EW is active (like movie radar jamming)
        if ew_active:
            # scatter green dots everywhere across the entire radar area
            for _ in range(600):
                nx = random.randint(int(CX - r_max), int(CX + r_max))
                ny = random.randint(int(CY - r_max), int(CY + r_max))
                # only draw inside the radar circle
                if math.hypot(nx - CX, ny - CY) < r_max:
                    g = random.choice([(0, 255, 0), (0, 200, 0), (100, 255, 50),
                                       (0, 180, 0), (50, 255, 30), (200, 255, 0)])
                    sz = random.choice([1, 1, 1, 2])
                    pygame.draw.circle(screen, g, (nx, ny), sz)

            # bright horizontal scan lines for that CRT glitch look
            for _ in range(random.randint(3, 8)):
                sy = random.randint(int(CY - r_max), int(CY + r_max))
                line_alpha = random.randint(20, 80)
                pygame.draw.line(screen, (0, line_alpha, 0),
                                 (int(CX - r_max), sy), (int(CX + r_max), sy), 1)

        # per-jammer strobe cone (bright interference wedge from the EW source)
        for ew in ew_aircrafts:
            ew_bearing = getattr(ew, 'bearing', getattr(ew, 'heading', 0))
            jam_width = 20.0 if getattr(ew, 'is_heavy_ew', False) else 10.0

            # dense noise particles in the jammer's sector
            particle_count = 400 if getattr(ew, 'is_heavy_ew', False) else 120
            for _ in range(particle_count):
                r_dist = random.uniform(10, r_max * 1.3)
                j_angle = ew_bearing + random.uniform(-jam_width, jam_width)
                jx = CX + r_dist * math.sin(math.radians(j_angle))
                jy = CY - r_dist * math.cos(math.radians(j_angle))
                g = random.choice([(0, 255, 0), (150, 255, 0), (0, 200, 50), (80, 255, 80)])
                pygame.draw.circle(screen, g, (int(jx), int(jy)), random.choice([1, 1, 2, 2, 3]))

            # strobe boundary lines
            for offset in [-jam_width, jam_width]:
                sx = CX + r_max * math.sin(math.radians(ew_bearing + offset))
                sy = CY - r_max * math.cos(math.radians(ew_bearing + offset))
                pygame.draw.line(screen, (0, 120, 40), (CX, CY), (sx, sy), 1)

        for c in cmd.contacts:
            if not c.active or not hasattr(c, 'visible_dist'): continue
            if c.brightness <= 0: continue 
            
            # EW glitch jitter
            if ew_active:
                glitch_x = random.randint(-8, 8)
                glitch_y = random.randint(-8, 8)
            else:
                glitch_x, glitch_y = 0, 0

            bearing = getattr(c, 'bearing', getattr(c, 'heading', 0)) 
            
            # 60 FPS Visual Physics Interpolation
            prev_x = getattr(c, 'prev_x_km', c.x_km)
            prev_y = getattr(c, 'prev_y_km', c.y_km)
            interp_x_km = prev_x + (c.x_km - prev_x) * alpha
            interp_y_km = prev_y + (c.y_km - prev_y) * alpha
            
            x = CX + km_to_px(interp_x_km) + glitch_x
            y = CY - km_to_px(interp_y_km) + glitch_y

            base_color = (180, 180, 180) 
            render_status = c.status

            if render_status in ["HOSTILE", "ENGAGING"]: base_color = (255, 60, 60)
            elif render_status in ["SUSPECT"]: base_color = (255, 220, 0)
            elif render_status in ["FRIENDLY"]: base_color = (60, 180, 255)
            elif render_status in ["INTERCEPTING"]: base_color = (200, 50, 200)

            color = lerp_color(BG_COLOR, base_color, c.brightness)

            if hasattr(c, 'trail'):
                for i, (tr_dist, tr_bear) in enumerate(c.trail):
                    tr_px = km_to_px(tr_dist)
                    tx = CX + tr_px * math.sin(math.radians(tr_bear))
                    ty = CY - tr_px * math.cos(math.radians(tr_bear))
                    alpha = (i + 1) / len(c.trail) * c.brightness
                    pygame.draw.circle(screen, lerp_color(BG_COLOR, base_color, alpha * 0.5), (int(tx), int(ty)), 1)

            if render_status in ["HOSTILE", "ENGAGING"]:
                pygame.draw.polygon(screen, color, [(x, y-8), (x+8, y), (x, y+8), (x-8, y)], 2)
            elif render_status == "FRIENDLY":
                pygame.draw.circle(screen, color, (int(x), int(y)), 6, 2)
            else:
                pygame.draw.rect(screen, color, (x-6, y-6, 12, 12), 2)
            
            target_heading = getattr(c, 'heading', (bearing + 180) % 360)
            vec_length = max(10, c.speed_mach * 10) 
            vec_end_x = x + vec_length * math.sin(math.radians(target_heading))
            vec_end_y = y - vec_length * math.cos(math.radians(target_heading))
            pygame.draw.line(screen, color, (x, y), (vec_end_x, vec_end_y), 1)

            # Draw info precisely next to the dot instead of the heading vector
            text_color = base_color if c.brightness > 0.3 else (80, 80, 80)
            screen.blit(font_sm.render(c.id_code, True, text_color), (x + 10, y - 10))
            alt_k = c.altitude_ft // 1000
            screen.blit(font_xs.render(f"{c.speed_mach:.1f}M FL{alt_k:02d}", True, text_color), (x + 10, y + 2))

            if selected_contact == c:
                heading = getattr(c, 'heading', (bearing + 180) % 360)
                lead_dist = c.speed_mach * 0.3403 * 3.0
                lead_x_km = c.x_km + lead_dist * math.sin(math.radians(heading))
                lead_y_km = c.y_km + lead_dist * math.cos(math.radians(heading))
                lead_px = (CX + km_to_px(lead_x_km), CY - km_to_px(lead_y_km))
                vfx_mgr.draw_lead_reticle(screen, (x, y), lead_px, c.id_code)

        for eng in cmd.active_engagements:
            target = getattr(eng, 'target', None)
            if not target or not target.active or not hasattr(eng, 'x_km'): continue
            
            wpn_name = "FIGHTER" if eng.weapon_name == "Interceptors" else eng.weapon_name
            
            mx = CX + km_to_px(eng.x_km)
            my = CY - km_to_px(eng.y_km)
            
            if hasattr(eng, 'trail'):
                for i, (tx_km, ty_km) in enumerate(eng.trail):
                    tx = CX + km_to_px(tx_km)
                    ty = CY - km_to_px(ty_km)
                    pygame.draw.circle(screen, lerp_color(BG_COLOR, MISSILE_COLOR, ((i + 1) / len(eng.trail)) * 0.8), (int(tx), int(ty)), 2)

            pygame.draw.line(screen, MISSILE_COLOR, (mx-4, my-4), (mx+4, my+4), 2)
            pygame.draw.line(screen, MISSILE_COLOR, (mx-4, my+4), (mx+4, my-4), 2)
            screen.blit(font_sm.render(wpn_name, True, MISSILE_COLOR), (mx + 8, my - 5))

        # --- Active RF Decoys ---
        for decoy in getattr(cmd, 'active_decoys', []):
            if decoy.get('active', False):
                dx_px = CX + km_to_px(decoy['x'])
                dy_px = CY - km_to_px(decoy['y'])
                pygame.draw.circle(screen, (255, 220, 0), (int(dx_px), int(dy_px)), 8, 2)
                pygame.draw.circle(screen, (255, 255, 100), (int(dx_px), int(dy_px)), 3)
                screen.blit(font_xs.render(f"RF-DECOY ({decoy['timer']}s)", True, (255, 220, 50)), (dx_px + 10, dy_px - 8))

        # --- Visual FX Layers (Shockwaves, Flak, Contrails, Embers) ---
        vfx_mgr.draw(screen, CX, CY)

        # --- Emergency Red Edge Vignette on Base Damage ---
        vfx_mgr.draw_damage_vignette(screen, cmd.base_hp)



        # --- Flight Info Panel ---
        if selected_contact:
            c = selected_contact
            panel_x, panel_y = 20, 120
            panel_w, panel_h = 240, 200
            
            # Draw Panel Background
            pygame.draw.rect(screen, (8, 12, 8), (panel_x, panel_y, panel_w, panel_h))
            pygame.draw.rect(screen, GRID_COLOR, (panel_x, panel_y, panel_w, panel_h), 1)
            
            # Header
            pygame.draw.rect(screen, (20, 40, 20), (panel_x, panel_y, panel_w, 20))
            screen.blit(font_sm.render("Flight Info | Aircraft Data", True, (200, 255, 200)), (panel_x + 5, panel_y + 3))
            
            texts = [
                f"DEPARTURE: {getattr(c, 'departure', 'UNKNOWN')}",
                f"DEST     : {getattr(c, 'destination', 'UNKNOWN')}",
                f"CALLSIGN : {getattr(c, 'callsign', 'UNKNOWN')}",
                f"ALT      : {c.altitude_ft} ft",
                f"SPD      : {int(c.speed_mach * 666)} kt",
                f"TYPE     : {c.type_name[:15]}",
                f"MODE 3   : {getattr(c, 'squawk_code', 'NONE')}"
            ]
            for i, txt in enumerate(texts):
                screen.blit(font_xs.render(txt, True, (180, 220, 180)), (panel_x + 10, panel_y + 30 + (i * 18)))
            
            # Set ID Buttons
            btn_y = panel_y + 165
            screen.blit(font_xs.render("Set ID:", True, (150, 150, 150)), (panel_x + 10, btn_y + 4))
            labels = ["H", "S", "F", "U"]
            for i, lbl in enumerate(labels):
                bx = panel_x + 70 + (i * 30)
                pygame.draw.rect(screen, (40, 40, 40), (bx, btn_y, 25, 20))
                pygame.draw.rect(screen, GRID_COLOR, (bx, btn_y, 25, 20), 1)
                screen.blit(font_sm.render(lbl, True, (255, 255, 255)), (bx + 8, btn_y + 3))


        # --- 4. HUD Overlays ---
        
        # 4.1 Top Center Status Bar
        top_bar_w = 780
        top_bar_x = (WIDTH - top_bar_w) // 2
        top_bar_y = 10
        
        def draw_status_box(x, y, w, h, text, color, val_text="", val_color=(255,255,255)):
            pygame.draw.rect(screen, (10, 15, 10), (x, y, w, h))
            pygame.draw.rect(screen, GRID_COLOR, (x, y, w, h), 1)
            screen.blit(font_sm.render(text, True, color), (x + 5, y + 4))
            if val_text:
                screen.blit(font_sm.render(val_text, True, val_color), (x + w - max(30, len(val_text)*8), y + 4))
                
        # Top Row: DEFCON, HP, PHASE, RANK/XP
        hp_color = RADAR_COLOR if cmd.base_hp > 50 else (255, 50, 50)
        draw_status_box(top_bar_x, top_bar_y, 160, 22, "DEFCON", (255,255,255), str(cmd.calculate_defcon()), (255,200,0))
        draw_status_box(top_bar_x + 165, top_bar_y, 190, 22, "BASE INTEGRITY", (255,255,255), f"{cmd.base_hp}%", hp_color)
        
        t = cmd.tick_count
        if t < 120:
            phase_str, phase_color = "PEACETIME", (100, 200, 100)
        elif t < 360:
            phase_str, phase_color = "TENSIONS", (255, 200, 50)
        else:
            phase_str, phase_color = "WARTIME", (255, 60, 60)
        draw_status_box(top_bar_x + 360, top_bar_y, 170, 22, phase_str, phase_color, f"T+{t}s", (150,150,150))
        draw_status_box(top_bar_x + 535, top_bar_y, 245, 22, f"RTAF {cmd.rank.upper()}", (100,220,255), f"{cmd.xp} XP", (255,220,0))
        
        # Second Row: Armory + Tactical Controls (EMCON, SALVO, DECOYS)
        armory_x = top_bar_x
        for i, (wpn, amount) in enumerate(cmd.ammo.items()):
            draw_status_box(armory_x + (i*85), top_bar_y + 25, 80, 20, wpn[:4], (150,150,150), str(amount), RADAR_COLOR)

        emcon_color = (80, 255, 80) if cmd.emcon_mode == "ACTIVE" else ((255, 200, 50) if cmd.emcon_mode == "SECTOR" else (255, 60, 60))
        draw_status_box(armory_x + 345, top_bar_y + 25, 140, 20, "[E] EMCON", (150,150,150), cmd.emcon_mode, emcon_color)
        
        salvo_color = (100, 200, 255) if cmd.salvo_mode == "SINGLE" else ((255, 200, 50) if cmd.salvo_mode == "RIPPLE" else (255, 60, 60))
        draw_status_box(armory_x + 490, top_bar_y + 25, 140, 20, "[S] SALVO", (150,150,150), cmd.salvo_mode, salvo_color)
        
        decoy_color = (255, 220, 50) if cmd.decoys_remaining > 0 else (120, 120, 120)
        draw_status_box(armory_x + 635, top_bar_y + 25, 145, 20, "[D] DECOY", (150,150,150), f"{cmd.decoys_remaining}/3", decoy_color)

        # Third Row: Active Mission Campaign
        draw_status_box(top_bar_x, top_bar_y + 48, 780, 20, f"[F1] MISSION: {cmd.mission_mgr.current.name.upper()}", (255, 220, 100), f"STATUS: {cmd.mission_mgr.current.state}", (100, 255, 100) if cmd.mission_mgr.current.state == 'IN_PROGRESS' else (255, 80, 80))

        # Spawn controls instruction
        map_tag = ["FULL", "SOVEREIGN", "MINIMAL", "OFF"][map_mgr.map_mode]
        ovr_text = f"LOCKED: {selected_contact.id_code} (PRESS 1:THAAD 2:SAM 3:CIWS 4:SCRAMBLE)" if selected_contact else f"TACTICAL: [E] EMCON | [S] Salvo | [D] Decoy | [TAB] Upgrades | [F1] Mission | [F2] Map:{map_tag} | [P] Phase 3"
        screen.blit(font_xs.render(ovr_text, True, (150, 150, 150)), (top_bar_x, top_bar_y + 72))

        # Tactical Upgrades Overlay (Toggle with TAB)
        if show_upgrades:
            up_w, up_h = 580, 280
            up_x, up_y = CX - (up_w // 2), CY - (up_h // 2)
            pygame.draw.rect(screen, (5, 12, 10), (up_x, up_y, up_w, up_h))
            pygame.draw.rect(screen, (80, 220, 120), (up_x, up_y, up_w, up_h), 2)
            screen.blit(font_lg.render("TACTICAL ARMORY & TECH UPGRADES", True, (100, 255, 150)), (up_x + 20, up_y + 15))
            screen.blit(font_sm.render(f"COMMAND BALANCE: {cmd.xp:,} XP AVAILABLE  |  PRESS [TAB] TO CLOSE", True, (255, 220, 50)), (up_x + 20, up_y + 45))
            
            for idx, (uid, uinfo) in enumerate(cmd.UPGRADE_CATALOG.items()):
                row_y = up_y + 75 + idx * 36
                is_unlocked = uid in cmd.unlocked_upgrades
                status_txt = "[UNLOCKED]" if is_unlocked else f"[{uinfo['key']}] BUY: {uinfo['cost']:,} XP"
                status_color = (100, 255, 100) if is_unlocked else ((255, 220, 0) if cmd.xp >= uinfo['cost'] else (140, 140, 140))
                
                screen.blit(font_md.render(f"{uinfo['name']}", True, (220, 220, 220)), (up_x + 20, row_y))
                screen.blit(font_xs.render(f"{uinfo['desc']}", True, (150, 180, 150)), (up_x + 20, row_y + 16))
                screen.blit(font_md.render(status_txt, True, status_color), (up_x + up_w - 200, row_y + 4))
            
        # 4.2 Left Side: Active Operations (Track List)
        list_w, list_h = 360, 480
        list_x, list_y = 20, HEIGHT - list_h - 20
        pygame.draw.rect(screen, (5, 8, 5), (list_x, list_y, list_w, list_h))
        pygame.draw.rect(screen, GRID_COLOR, (list_x, list_y, list_w, list_h), 1)
        screen.blit(font_sm.render("ACTIVE OPERATIONS", True, (150, 255, 150)), (list_x + 10, list_y + 5))
        pygame.draw.line(screen, GRID_COLOR, (list_x, list_y + 25), (list_x + list_w, list_y + 25), 1)
        
        sorted_contacts = sorted(cmd.contacts, key=lambda c: c.calculate_threat_score(), reverse=True)
        for i, c in enumerate(sorted_contacts[:20]):
            row_y = list_y + 30 + (i * 18)
            r_color = (150, 150, 150)
            if c.status in ["HOSTILE", "ENGAGING"]: r_color = (255, 80, 80)
            elif c.status == "SUSPECT": r_color = (255, 220, 50)
            elif c.status == "FRIENDLY": r_color = (100, 180, 255)
            
            prefix = "[*]" if selected_contact == c else " - "
            row_str = f"{prefix} {c.id_code:<9} {c.status[:3]:<3} {c.distance_km:>4.0f}km {c.speed_mach:>3.1f}M"
            screen.blit(font_xs.render(row_str, True, r_color), (list_x + 10, row_y))

        # 4.3 Right Side: Minimalist Tactical Log
        log_w = 400
        log_x = WIDTH - log_w - 20
        log_y = HEIGHT // 2 - 150
        recent_logs = cmd.tactical_log[-20:]
        for i, log in enumerate(recent_logs):
            clean_str = clean_ansi(log)[:70]
            screen.blit(font_xs.render(clean_str, True, get_log_color(log)), (log_x, log_y + (i * 16)))

        if cmd.base_hp <= 0:
            aar = cmd.get_after_action_report()
            aar_w, aar_h = 620, 260
            aar_x, aar_y = CX - (aar_w // 2), CY - (aar_h // 2)
            pygame.draw.rect(screen, (15, 8, 8), (aar_x, aar_y, aar_w, aar_h))
            pygame.draw.rect(screen, (220, 40, 40), (aar_x, aar_y, aar_w, aar_h), 2)
            
            status_title = "COURT-MARTIAL: CIVILIAN CASUALTIES" if getattr(cmd, 'is_court_martialed', False) else "BASE COMPROMISED: ALL SYSTEMS OFFLINE"
            screen.blit(font_lg.render(status_title, True, (255, 80, 80)), (aar_x + 20, aar_y + 15))
            
            medals_str = ", ".join(aar.get("medals", [])) if aar.get("medals") else "None Awarded"
            lines_data = [
                f"RTAF Rank: {aar.get('rank', 'Airman').upper()}  |  Final XP: {aar.get('xp', 0):,}  |  Kills: {aar.get('kills', 0)}",
                f"Sortie Duration: {aar.get('survival_time_sec', 0)}s  |  Airliners Safe: {aar.get('airliners_safe', 0)}",
                f"Medals: {medals_str}",
                f"Performance Grade: {aar.get('grade', 'D')}"
            ]
            for idx, txt in enumerate(lines_data):
                color = (255, 220, 50) if idx == 0 else ((100, 255, 100) if idx == 2 else (220, 220, 220))
                screen.blit(font_md.render(txt, True, color), (aar_x + 20, aar_y + 60 + idx * 32))
                
            restart_hint = font_md.render("Press [R] to Re-Scramble Sortie  |  [ESC] to Stand Down", True, (120, 200, 255))
            screen.blit(restart_hint, (aar_x + 20, aar_y + 215))

        screen.blit(font_sm.render("Press [ESC] Quit | [CLICK] Select | [1-4] Fire | [E] EMCON | [S] Salvo | [D] Decoy | [P] Phase 3 Wartime | [U] Mute | [R] Restart", True, (120, 150, 120)), (10, HEIGHT - 25))

        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    start_radar()
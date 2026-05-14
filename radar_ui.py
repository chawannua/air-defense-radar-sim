import pygame
import math
import sys
import random
import json
import os
import re
from command_center import CommandCenter
from targets import AWACS

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

def generate_map_shapes():
    shapes = []
    # Thai Border Approximation (very rough polygon)
    thai_border = [
        (-200, 400), (-100, 500), (100, 450), (200, 200),
        (300, 100), (350, -100), (200, -200), (100, -400),
        (-50, -600), (-150, -300), (-250, 100)
    ]
    shapes.append(thai_border)
    return shapes

def generate_topo_contours(peaks_km):
    contours = []
    for px, py, name in peaks_km:
        height_str = ''.join(filter(str.isdigit, name))
        height = int(height_str) if height_str else 3000
        num_rings = max(2, height // 1200)
        
        for ring_idx in range(1, num_rings + 1):
            base_radius = ring_idx * 15 # km
            ring_points = []
            num_points = 60
            seed1 = random.uniform(0, 100)
            seed2 = random.uniform(0, 100)
            
            for i in range(num_points):
                angle = math.radians(i * (360/num_points))
                # more organic noise
                n1 = math.sin(angle * 3 + seed1) * (base_radius * 0.15)
                n2 = math.cos(angle * 5 + seed2) * (base_radius * 0.05)
                r = base_radius + n1 + n2
                
                cx = px + r * math.cos(angle)
                cy = py + r * math.sin(angle)
                ring_points.append((cx, cy))
            
            contours.append(ring_points)
    return contours

def load_real_map():
    shapes_km = []
    RADAR_LAT = 13.7563  # Bangkok, Thailand
    RADAR_LON = 100.5018
    
    def latlon_to_km(lon, lat):
        dx = (lon - RADAR_LON) * 111.32 * math.cos(math.radians(RADAR_LAT))
        dy = (lat - RADAR_LAT) * 110.574
        return (dx, dy) 
    
    map_files = ["tha.json", "mmr.json", "lao.json", "khm.json", "mys.json", "vnm.json", "chn.json", "idn.json", "phl.json", "twn.json"]
    for filename in map_files:
        filepath = filename
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            filepath = os.path.join(sys._MEIPASS, filename)
            
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    poly_list = json.load(f)
                for ring in poly_list:
                    ring_km = []
                    for lon, lat in ring:
                        x_km, y_km = latlon_to_km(lon, lat)
                        ring_km.append((x_km, y_km))
                    shapes_km.append(ring_km)
            except Exception as e:
                print("Map load error:", e)
    
    if not shapes_km:
        shapes_km = generate_map_shapes()
        
    peaks_data = [
        (18.588, 98.487, "DOI INTHANON 8415FT"),
        (8.544, 99.736, "KHAO LUANG 6024FT"),
        (16.883, 101.783, "PHU KRADUENG 4301FT"),
        (13.5, 99.3, "TENASSERIM 3500FT"),
        (14.3, 102.0, "KHAO YAI 4400FT"),
        (19.9, 99.0, "DOI PHA HOM POK 7500FT")
    ]
    peaks_km = []
    for lat, lon, name in peaks_data:
        x_km, y_km = latlon_to_km(lon, lat)
        peaks_km.append((x_km, y_km, name))
        
    airbases_data = [
        (14.933, 102.083, "WING 1 (KORAT)"),
        (15.266, 100.333, "WING 4 (TAKHLI)"),
        (9.133, 99.133, "WING 7 (SURAT THANI)"),
        (15.250, 104.866, "WING 21 (UBON)"),
        (17.383, 102.783, "WING 23 (UDON)")
    ]
    airbases_km = []
    for lat, lon, name in airbases_data:
        x_km, y_km = latlon_to_km(lon, lat)
        airbases_km.append((x_km, y_km, name))
        
    return shapes_km, peaks_km, airbases_km

MAP_SHAPES_KM, MAP_PEAKS_KM, MAP_AIRBASES_KM = load_real_map()
MAP_CONTOURS_KM = generate_topo_contours(MAP_PEAKS_KM)

def start_radar():
    pygame.init()
    
    info = pygame.display.Info()
    MONITOR_W, MONITOR_H = info.current_w, info.current_h
    
    # start windowed at 90% of screen
    WIDTH, HEIGHT = int(MONITOR_W * 0.9), int(MONITOR_H * 0.9)
    is_fullscreen = False
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE) 
    pygame.display.set_caption("AEGIS Tactical Air Defense Radar")

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
    sweep_angle = 0.0
    sweep_speed = 2.8
    clock = pygame.time.Clock()
    LAST_TICK_TIME = pygame.time.get_ticks()

    selected_contact = None  

    running = True
    while running:
        current_time = pygame.time.get_ticks()

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

                # dev: manual threat spawn
                if not selected_contact:
                    if event.key == pygame.K_5: cmd.manual_spawn("ICBM")
                    elif event.key == pygame.K_6: cmd.manual_spawn("FIGHTER")
                    elif event.key == pygame.K_7: cmd.manual_spawn("DRONE")
                    elif event.key == pygame.K_8: cmd.manual_spawn("AIRLINER")
                    elif event.key == pygame.K_9: cmd.manual_spawn("EW")
                    elif event.key == pygame.K_0: cmd.manual_spawn("AWACS")
                    elif event.key == pygame.K_w: cmd.manual_spawn("WAVE")
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

        CX = (WIDTH // 2) + int(camera_x)
        CY = (HEIGHT // 2) + int(camera_y)

        screen.fill(BG_COLOR)

        # --- 1. Weapon Engagement Zones (WEZ) ---
        # Only display the Weapon Engagement Zones (WEZ)
        pygame.draw.circle(screen, (0, 30, 80), (CX, CY), int(km_to_px(400)), 1) # THAAD Optimal Range
        pygame.draw.circle(screen, (80, 80, 0), (CX, CY), int(km_to_px(200)), 1) # SAM Anti-Ballistic Range
        pygame.draw.circle(screen, (80, 50, 0), (CX, CY), int(km_to_px(80)), 1)  # SAM Anti-Aircraft Range
        pygame.draw.circle(screen, (80, 0, 0), (CX, CY), int(km_to_px(20)), 1)   # CIWS Range

        # Draw map shapes
        for shape_km in MAP_SHAPES_KM:
            pixel_points = []
            for (x_km, y_km) in shape_km:
                px_x = CX + km_to_px(x_km)
                px_y = CY - km_to_px(y_km) # Minus because Pygame Y is flipped relative to North
                pixel_points.append((px_x, px_y))
            if len(pixel_points) > 2:
                # Beautiful Anti-Aliased Map Rendering
                pygame.draw.aalines(screen, (0, 140, 40), True, pixel_points) # Sharp inner anti-aliased line

        # Draw Topographical Contours
        for ring_points_km in MAP_CONTOURS_KM:
            points_px = []
            for rx_km, ry_km in ring_points_km:
                px = CX + km_to_px(rx_km)
                py = CY - km_to_px(ry_km)
                points_px.append((px, py))
            if len(points_px) >= 2:
                pygame.draw.aalines(screen, (30, 45, 20), True, points_px) # Faint green-brown for contours

        # Draw Mountain Peaks (Elevation)
        for x_km, y_km, p_name in MAP_PEAKS_KM:
            px = CX + km_to_px(x_km)
            py = CY - km_to_px(y_km)
            pygame.draw.polygon(screen, (80, 100, 40), [(px, py - 4), (px - 4, py + 4), (px + 4, py + 4)], 1)
            screen.blit(font_xs.render(p_name, True, (80, 100, 40)), (px + 6, py - 3))

        # Draw Military Airbases
        for x_km, y_km, b_name in MAP_AIRBASES_KM:
            px = CX + km_to_px(x_km)
            py = CY - km_to_px(y_km)
            pygame.draw.circle(screen, (0, 150, 255), (px, py), 3, 1)
            pygame.draw.rect(screen, (0, 150, 255), (px - 5, py - 5, 10, 10), 1)
            screen.blit(font_xs.render(b_name, True, (0, 150, 255)), (px + 8, py - 4))

        r_max = km_to_px(RADAR_MAX_KM)

        # --- 2. Rotary AESA Radar Sweep ---
        ew_active = any(getattr(c, 'is_heavy_ew', False) and c.active for c in cmd.contacts)
        
        if ew_active:
            sweep_speed = random.choice([-25, -10, 2.8, 15, 30, 60, -40]) # Glitch rotation
        else:
            sweep_speed = 2.8
            
        old_sweep_angle = sweep_angle
        sweep_angle = (sweep_angle + sweep_speed) % 360

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
                pygame.draw.rect(screen, (255, 255, 255), (x-12, y-12, 24, 24), 1)
                pygame.draw.circle(screen, (255, 255, 255), (int(x), int(y)), 20, 1)

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
        top_bar_w = 600
        top_bar_x = (WIDTH - top_bar_w) // 2
        top_bar_y = 10
        
        def draw_status_box(x, y, w, h, text, color, val_text="", val_color=(255,255,255)):
            pygame.draw.rect(screen, (10, 15, 10), (x, y, w, h))
            pygame.draw.rect(screen, GRID_COLOR, (x, y, w, h), 1)
            screen.blit(font_sm.render(text, True, color), (x + 5, y + 4))
            if val_text:
                screen.blit(font_sm.render(val_text, True, val_color), (x + w - max(30, len(val_text)*8), y + 4))
                
        # Top Row: DEFCON, HP, PHASE
        hp_color = RADAR_COLOR if cmd.base_hp > 50 else (255, 50, 50)
        draw_status_box(top_bar_x, top_bar_y, 180, 22, "DEFCON STATUS", (255,255,255), str(cmd.calculate_defcon()), (255,200,0))
        draw_status_box(top_bar_x + 190, top_bar_y, 220, 22, "BASE INTEGRITY", (255,255,255), f"{cmd.base_hp}%", hp_color)
        
        # show escalation phase
        t = cmd.tick_count
        if t < 120:
            phase_str, phase_color = "PEACETIME", (100, 200, 100)
        elif t < 360:
            phase_str, phase_color = "TENSIONS", (255, 200, 50)
        else:
            phase_str, phase_color = "WARTIME", (255, 60, 60)
        draw_status_box(top_bar_x + 420, top_bar_y, 180, 22, phase_str, phase_color, f"T+{t}s", (150,150,150))
        
        # Second Row: Armory (Small buttons)
        armory_x = top_bar_x
        for i, (wpn, amount) in enumerate(cmd.ammo.items()):
            draw_status_box(armory_x + (i*100), top_bar_y + 25, 95, 20, wpn[:4], (150,150,150), str(amount), RADAR_COLOR)
            
        # Spawn controls instruction
        ovr_text = f"LOCKED: {selected_contact.id_code} (PRESS 1:THAAD 2:SAM 3:CIWS 4:SCRAMBLE)" if selected_contact else "SPAWN: 5:ICBM 6:Jet 7:Drone 8:CIV 9:EW 0:AWACS W:Wave"
        screen.blit(font_xs.render(ovr_text, True, (150, 150, 150)), (top_bar_x, top_bar_y + 50))
            
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
            pygame.draw.rect(screen, (100, 0, 0), (CX - 220, CY - 40, 440, 80))
            pygame.draw.rect(screen, (255, 0, 0), (CX - 220, CY - 40, 440, 80), 3)
            screen.blit(font_lg.render("BASE DESTROYED! ALL SYSTEMS OFFLINE", True, (255, 255, 255)), (CX - 200, CY - 20))
            
            # Text to indicate restart option
            restart_text = font_md.render("Press [R] to Restart Simulation", True, (255, 200, 200))
            screen.blit(restart_text, (CX - (restart_text.get_width() // 2), CY + 10))

        screen.blit(font_sm.render("Press [ESC] to Quit | [CLICK] Select | [1-4] Fire | [BACKSPACE] Abort | [F11] Fullscreen | [R] Restart (On Death)", True, (80, 80, 80)), (10, HEIGHT - 25))

        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    start_radar()
import pygame
import math
import sys
import re
import random
from command_center import CommandCenter
from targets import AWACS

# 🟢 [FIX] แก้ปัญหา Windows แอบซูมหน้าจอ และทำให้ Resolution พัง
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
    island1 = []
    for angle in range(0, 360, 15):
        r = 120 + random.uniform(-20, 20)
        island1.append((-150 + r * math.cos(math.radians(angle)), -200 + r * math.sin(math.radians(angle))))
    shapes.append(island1)
    
    coast = []
    for y in range(-800, 800, 30):
        x = 350 + math.sin(y/120.0)*80 + random.uniform(-15, 15)
        coast.append((x, y))
    coast.append((1000, 800))
    coast.append((1000, -800))
    shapes.append(coast)
    return shapes

MAP_SHAPES_KM = generate_map_shapes()

def start_radar():
    pygame.init()
    
    info = pygame.display.Info()
    MONITOR_W, MONITOR_H = info.current_w, info.current_h
    
    # เปิดมาตอนแรกให้เป็นโหมด Window 90% และดึงขอบหน้าต่างได้ (RESIZABLE)
    WIDTH, HEIGHT = int(MONITOR_W * 0.9), int(MONITOR_H * 0.9)
    is_fullscreen = False
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE) 
    pygame.display.set_caption("AEGIS Tactical Air Defense Radar")

    BG_COLOR = (4, 10, 4)
    GRID_COLOR = (0, 70, 0)
    RADAR_COLOR = (0, 255, 50)
    LOG_BG = (8, 12, 8)
    MISSILE_COLOR = (255, 120, 0)
    
    RADAR_AREA = HEIGHT 
    SIDEBAR_WIDTH = max(400, WIDTH - RADAR_AREA) # ล็อคไม่ให้ Sidebar เล็กกว่า 400px
    sidebar_x = RADAR_AREA
    
    CX, CY = RADAR_AREA // 2, HEIGHT // 2
    RADAR_RADIUS_PX = (HEIGHT // 2) - 60 
    RADAR_MAX_KM = 800.0 
    
    def km_to_px(km): return (km / RADAR_MAX_KM) * RADAR_RADIUS_PX

    font_xs = pygame.font.SysFont('consolas', 10)
    font_sm = pygame.font.SysFont('consolas', 12)
    font_md = pygame.font.SysFont('consolas', 16, bold=True)
    font_lg = pygame.font.SysFont('consolas', 22, bold=True)

    cmd = CommandCenter()
    sweep_angle = 0.0
    sweep_speed = 2.8  # เพิ่มความเร็วการกวาดเพื่อให้ตรวจสอบเป้าหมายบ่อยขึ้น
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

            # 🟢 [RESIZE] ระบบลากขอบหน้าต่างอิสระ (Smooth Resize แบบ Roblox)
            if event.type == pygame.VIDEORESIZE:
                if not is_fullscreen:
                    WIDTH, HEIGHT = event.w, event.h
                    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
                    
                    RADAR_AREA = HEIGHT 
                    SIDEBAR_WIDTH = max(400, WIDTH - RADAR_AREA) 
                    sidebar_x = RADAR_AREA
                    CX, CY = RADAR_AREA // 2, HEIGHT // 2
                    RADAR_RADIUS_PX = (HEIGHT // 2) - 60
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: running = False; sys.exit()
                
                # 🟢 [FIRE] กดยิงเป้าหมายที่เลือก
                if selected_contact:
                    wpn = None
                    if event.key == pygame.K_1: wpn = 'THAAD'
                    elif event.key == pygame.K_2: wpn = 'SAM'
                    elif event.key == pygame.K_3: wpn = 'CIWS'
                    elif event.key == pygame.K_4: wpn = 'F-16' 
                    
                    if wpn:
                        cmd.manual_override_fire(selected_contact, wpn)

                # 🔴 [ABORT] ระบบยกเลิกการยิงเป้าหมายที่เลือก
                if event.key == pygame.K_BACKSPACE and selected_contact:
                    cmd.manual_override_abort(selected_contact)

                # 🛠️ [DEV] Manual Spawn
                if not selected_contact:
                    if event.key == pygame.K_5: cmd.manual_spawn("ICBM")
                    elif event.key == pygame.K_6: cmd.manual_spawn("FIGHTER")
                    elif event.key == pygame.K_7: cmd.manual_spawn("DRONE")
                    elif event.key == pygame.K_8: cmd.manual_spawn("AIRLINER")
                    elif event.key == pygame.K_9: cmd.manual_spawn("EW")
                    elif event.key == pygame.K_0: cmd.manual_spawn("AWACS")
                    elif event.key == pygame.K_w: cmd.manual_spawn("WAVE")
                # 🟢 [FULLSCREEN] สลับโหมดแบบปลอดภัย ไม่ทำจอพัง
                if event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    if is_fullscreen:
                        # ใช้ (0, 0) เพื่อให้ Pygame วาดทับหน้าจอพอดี โดยไม่เปลี่ยนความละเอียด OS
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                        info_fs = pygame.display.Info()
                        WIDTH, HEIGHT = info_fs.current_w, info_fs.current_h 
                    else:
                        WIDTH, HEIGHT = int(MONITOR_W * 0.9), int(MONITOR_H * 0.9) 
                        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
                    
                    RADAR_AREA = HEIGHT 
                    SIDEBAR_WIDTH = max(400, WIDTH - RADAR_AREA)
                    sidebar_x = RADAR_AREA
                    CX, CY = RADAR_AREA // 2, HEIGHT // 2
                    RADAR_RADIUS_PX = (HEIGHT // 2) - 60

                # 🟢 [RESTART] เริ่มเกมใหม่เมื่อฐานถูกทำลาย
                if event.key == pygame.K_r and cmd.base_hp <= 0:
                    cmd = CommandCenter()
                    selected_contact = None
                    sweep_angle = 0.0
                    LAST_TICK_TIME = pygame.time.get_ticks()

            # 🟢 [CLICK] คลิกเมาส์เพื่อล็อคเป้าหมาย
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
                            
                if not panel_clicked and mx < RADAR_AREA:
                    closest_c = None
                    min_dist = 20 
                    for c in cmd.contacts:
                        if not c.active or not hasattr(c, 'visible_dist'): continue
                        bearing = getattr(c, 'bearing', getattr(c, 'heading', 0))
                        px_dist = km_to_px(min(c.visible_dist, RADAR_MAX_KM))
                        tx = CX + px_dist * math.sin(math.radians(bearing))
                        ty = CY - px_dist * math.cos(math.radians(bearing))
                        
                        dist_to_mouse = math.hypot(mx - tx, my - ty)
                        if dist_to_mouse < min_dist:
                            min_dist = dist_to_mouse
                            closest_c = c
                    selected_contact = closest_c

        screen.fill(BG_COLOR)

        # ===================================================
        # 1. วาดกริดและ Weapon Engagement Zones (WEZ)
        # ===================================================
        for ring_km in [200, 400, 600, 800]:
            r_px = km_to_px(ring_km)
            pygame.draw.circle(screen, GRID_COLOR, (CX, CY), int(r_px), 1)
            screen.blit(font_xs.render(f"{ring_km}", True, GRID_COLOR), (CX + 2, CY - r_px - 12))
            
        pygame.draw.circle(screen, (0, 30, 80), (CX, CY), int(km_to_px(400)), 1) # THAAD Optimal Range
        pygame.draw.circle(screen, (80, 80, 0), (CX, CY), int(km_to_px(200)), 1) # SAM Anti-Ballistic Range
        pygame.draw.circle(screen, (80, 50, 0), (CX, CY), int(km_to_px(80)), 1)  # SAM Anti-Aircraft Range
        pygame.draw.circle(screen, (80, 0, 0), (CX, CY), int(km_to_px(20)), 1)   # CIWS Range

        # Draw map shapes
        for shape_km in MAP_SHAPES_KM:
            pixel_points = []
            for (x_km, y_km) in shape_km:
                px_x = CX + km_to_px(x_km)
                px_y = CY + km_to_px(y_km)
                pixel_points.append((px_x, px_y))
            if len(pixel_points) > 2:
                pygame.draw.polygon(screen, (0, 30, 10), pixel_points, 1)

        pygame.draw.line(screen, GRID_COLOR, (CX, CY - RADAR_RADIUS_PX), (CX, CY + RADAR_RADIUS_PX), 1)
        pygame.draw.line(screen, GRID_COLOR, (CX - RADAR_RADIUS_PX, CY), (CX + RADAR_RADIUS_PX, CY), 1)

        for angle in range(0, 360, 10):
            rad = math.radians(angle)
            outer_x = CX + (RADAR_RADIUS_PX + 5) * math.sin(rad)
            outer_y = CY - (RADAR_RADIUS_PX + 5) * math.cos(rad)
            inner_x = CX + RADAR_RADIUS_PX * math.sin(rad)
            inner_y = CY - RADAR_RADIUS_PX * math.cos(rad)
            
            if angle % 30 == 0:
                pygame.draw.line(screen, (0, 120, 0), (inner_x, inner_y), (outer_x, outer_y), 2)
                text = font_xs.render(f"{angle:03d}", True, (0, 150, 0))
                tx = CX + (RADAR_RADIUS_PX + 15) * math.sin(rad) - text.get_width()//2
                ty = CY - (RADAR_RADIUS_PX + 15) * math.cos(rad) - text.get_height()//2
                screen.blit(text, (tx, ty))
            else:
                pygame.draw.line(screen, GRID_COLOR, (inner_x, inner_y), (outer_x, outer_y), 1)

        # ===================================================
        # 2. จำลองการกวาดแบบ Rotary AESA (Mechanical + Electronic Steering)
        # ===================================================
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
            progress = 1.0 - (max(0, getattr(eng, 'time_to_impact', 0)) / max(1, eng.total_time))
            bearing = getattr(target, 'bearing', getattr(target, 'heading', 0))
            
            if angle_diff(bearing, sweep_angle) <= AESA_FOV:
                # Calculate expected impact distance to ensure linear missile trajectory
                impact_dist = max(0, target.distance_km - (target.speed_mach * getattr(eng, 'time_to_impact', 0)))
                eng.visible_dist = impact_dist * progress
                eng.brightness = 1.0
                if not hasattr(eng, 'trail'): eng.trail = []
                if random.random() < 0.1:
                    eng.trail.append((eng.visible_dist, bearing))
                    if len(eng.trail) > 8: eng.trail.pop(0)
            else:
                if hasattr(eng, 'brightness') and eng.brightness > 0:
                    eng.brightness = max(0.0, eng.brightness - 0.005)

        # --- AESA Random Search Beams (Electronic steering within FOV) ---
        for _ in range(12): 
            e_angle = random.uniform(-AESA_FOV, AESA_FOV)
            r_angle = (sweep_angle + e_angle) % 360
            r_len = RADAR_RADIUS_PX * random.uniform(0.3, 0.95)
            bx = CX + r_len * math.sin(math.radians(r_angle))
            by = CY - r_len * math.cos(math.radians(r_angle))
            pygame.draw.line(screen, (0, 80, 40), (CX, CY), (bx, by), 1)

        # --- AESA Tracking Beams (Tracking targets within FOV) ---
        for c in cmd.contacts:
            if c.active and c.distance_km < RADAR_MAX_KM:
                target_bearing = getattr(c, 'bearing', 0)
                
                # Only track if the mechanical dish is pointing roughly towards it
                if angle_diff(target_bearing, sweep_angle) <= AESA_FOV:
                    dist_px = (c.distance_km / RADAR_MAX_KM) * RADAR_RADIUS_PX
                    
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
        lx = CX + RADAR_RADIUS_PX * math.sin(math.radians(fov_left))
        ly = CY - RADAR_RADIUS_PX * math.cos(math.radians(fov_left))
        rx = CX + RADAR_RADIUS_PX * math.sin(math.radians(fov_right))
        ry = CY - RADAR_RADIUS_PX * math.cos(math.radians(fov_right))
        pygame.draw.line(screen, (0, 60, 20), (CX, CY), (lx, ly), 1)
        pygame.draw.line(screen, (0, 60, 20), (CX, CY), (rx, ry), 1)

        # --- Main Sweep Line (Mechanical Boresight) ---
        # ยังคงเส้นหลักไว้เพื่อให้เห็นทิศทางการหมุนของจานเรดาร์
        end_x = CX + RADAR_RADIUS_PX * math.sin(math.radians(sweep_angle))
        end_y = CY - RADAR_RADIUS_PX * math.cos(math.radians(sweep_angle))
        pygame.draw.line(screen, (150, 255, 180), (CX, CY), (end_x, end_y), 3)

        # วาด Tail (เงาของเส้นกวาด) ให้ดูนวลขึ้น
        for i in range(1, 10):
            t_angle = (sweep_angle - (i * 3)) % 360
            t_alpha = 1.0 - (i / 10.0)
            t_color = (int(0 * t_alpha), int(200 * t_alpha), int(50 * t_alpha))
            tx = CX + RADAR_RADIUS_PX * math.sin(math.radians(t_angle))
            ty = CY - RADAR_RADIUS_PX * math.cos(math.radians(t_angle))
            pygame.draw.line(screen, t_color, (CX, CY), (tx, ty), 2)

        # ===================================================
        # 3. วาดเป้าหมาย & Electronic Warfare (Jamming)
        # ===================================================
        ew_aircrafts = [c for c in cmd.contacts if c.active and "EW" in getattr(c, 'type_name', '')]

        # --- Draw Realistic Jamming Strobes (Sector Jamming) ---
        for ew in ew_aircrafts:
            ew_bearing = getattr(ew, 'bearing', getattr(ew, 'heading', 0))
            jam_width = 8.0 # +/- 8 degree cone of noise
            
            # Draw noise particles representing RF interference in this sector
            for _ in range(80):
                r_dist = random.uniform(20, RADAR_RADIUS_PX)
                j_angle = ew_bearing + random.uniform(-jam_width, jam_width)
                jx = CX + r_dist * math.sin(math.radians(j_angle))
                jy = CY - r_dist * math.cos(math.radians(j_angle))
                noise_color = (random.randint(50, 150), random.randint(150, 255), random.randint(50, 150))
                pygame.draw.circle(screen, noise_color, (int(jx), int(jy)), random.randint(1, 2))
                
            # Draw faint boundaries of the strobe
            for angle_offset in [-jam_width, jam_width]:
                sx = CX + RADAR_RADIUS_PX * math.sin(math.radians(ew_bearing + angle_offset))
                sy = CY - RADAR_RADIUS_PX * math.cos(math.radians(ew_bearing + angle_offset))
                pygame.draw.line(screen, (0, 80, 40), (CX, CY), (sx, sy), 1)

        for c in cmd.contacts:
            if not c.active or not hasattr(c, 'visible_dist'): continue
            if c.brightness <= 0: continue 
            
            bearing = getattr(c, 'bearing', getattr(c, 'heading', 0)) 
            px_dist = km_to_px(min(c.visible_dist, RADAR_MAX_KM))
            x = CX + px_dist * math.sin(math.radians(bearing))
            y = CY - px_dist * math.cos(math.radians(bearing))

            base_color = (180, 180, 180) 
            render_status = c.status

            if render_status in ["HOSTILE", "ENGAGING"]: base_color = (255, 60, 60)
            elif render_status in ["SUSPECT"]: base_color = (255, 220, 0)
            elif render_status in ["FRIENDLY"]: base_color = (60, 180, 255)
            elif render_status in ["INTERCEPTING"]: base_color = (200, 50, 200)

            color = lerp_color(BG_COLOR, base_color, c.brightness)

            if hasattr(c, 'trail'):
                for i, (tr_dist, tr_bear) in enumerate(c.trail):
                    tr_px = km_to_px(min(tr_dist, RADAR_MAX_KM))
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

            screen.blit(font_sm.render(c.id_code, True, color), (vec_end_x + 5, vec_end_y - 10))
            alt_k = c.altitude_ft // 1000
            screen.blit(font_xs.render(f"{c.speed_mach:.1f}M FL{alt_k:02d}", True, color), (vec_end_x + 5, vec_end_y + 2))

            if selected_contact == c:
                pygame.draw.rect(screen, (255, 255, 255), (x-12, y-12, 24, 24), 1)
                pygame.draw.circle(screen, (255, 255, 255), (int(x), int(y)), 20, 1)
                
            # AWACS Radar Ring Effect
            if isinstance(c, AWACS):
                awacs_range_px = km_to_px(300)
                pygame.draw.circle(screen, (0, 80, 0), (int(x), int(y)), int(awacs_range_px), 1)
                pygame.draw.circle(screen, (0, 40, 0), (int(x), int(y)), int(awacs_range_px * 0.5), 1)

        for eng in cmd.active_engagements:
            target = getattr(eng, 'target', None)
            if not target or not target.active or not hasattr(eng, 'visible_dist'): continue
            
            wpn_name = "F-16" if eng.weapon_name == "Interceptors" else eng.weapon_name
            bearing = getattr(target, 'bearing', getattr(target, 'heading', 0))
            m_px = km_to_px(min(eng.visible_dist, RADAR_MAX_KM))
            mx = CX + m_px * math.sin(math.radians(bearing))
            my = CY - m_px * math.cos(math.radians(bearing))
            
            if hasattr(eng, 'trail'):
                for i, (tr_dist, tr_bear) in enumerate(eng.trail):
                    tr_px = km_to_px(min(tr_dist, RADAR_MAX_KM))
                    tx = CX + tr_px * math.sin(math.radians(tr_bear))
                    ty = CY - tr_px * math.cos(math.radians(tr_bear))
                    pygame.draw.circle(screen, lerp_color(BG_COLOR, MISSILE_COLOR, ((i + 1) / len(eng.trail)) * 0.8), (int(tx), int(ty)), 2)

            pygame.draw.line(screen, MISSILE_COLOR, (mx-4, my-4), (mx+4, my+4), 2)
            pygame.draw.line(screen, MISSILE_COLOR, (mx-4, my+4), (mx+4, my-4), 2)
            screen.blit(font_sm.render(wpn_name, True, MISSILE_COLOR), (mx + 8, my - 5))

        # ===================================================
        # 3.5 Dynamic Electronic Warfare Effect (Growler)
        # ===================================================
        growler_count = sum(1 for c in cmd.contacts if getattr(c, 'is_heavy_ew', False) and c.status != "UNIDENTIFIED" and c.active)

        if growler_count > 0:
            noise_areas = []
            if growler_count >= 1: noise_areas.append(pygame.Rect(CX, 0, CX, CY))       
            if growler_count >= 2: noise_areas.append(pygame.Rect(CX, CY, CX, CY))      
            if growler_count >= 3: noise_areas.append(pygame.Rect(0, 0, CX, CY))        
            if growler_count >= 4: noise_areas.append(pygame.Rect(0, CY, CX, CY))       

            for area in noise_areas:
                for _ in range(300):
                    rx = random.randint(area.left, area.right - 1)
                    ry = random.randint(area.top, area.bottom - 1)
                    n_color = random.choice([(0, 255, 0), (200, 255, 0), (50, 150, 50)])
                    pygame.draw.circle(screen, n_color, (rx, ry), random.randint(1, 2))

        # ===================================================
        # 3.8 Flight Info Panel (On Radar Display)
        # ===================================================
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


        # ===================================================
        # 4. วาดฝั่งขวา (DASHBOARD & TABLES)
        # ===================================================
        pygame.draw.rect(screen, LOG_BG, (sidebar_x, 0, SIDEBAR_WIDTH, HEIGHT))
        pygame.draw.line(screen, GRID_COLOR, (sidebar_x, 0), (sidebar_x, HEIGHT), 2)
        
        pad_x = sidebar_x + 20
        
        hp_color = RADAR_COLOR if cmd.base_hp > 50 else (255, 50, 50)
        screen.blit(font_lg.render(f"DEFCON {cmd.calculate_defcon()} | BASE HP: {cmd.base_hp}% | TICK: {cmd.tick_count}", True, hp_color), (pad_x, 15))
        
        armory_str = ""
        for wpn, amount in cmd.ammo.items():
            armory_str += f"[{wpn}: {amount:02d}/{cmd.max_ammo[wpn]:02d}]   "
        screen.blit(font_md.render(f"ARMORY: {armory_str}", True, RADAR_COLOR), (pad_x, 45))

        override_color = (255, 255, 255) if selected_contact else (80, 80, 80)
        ovr_text = f"LOCKED: {selected_contact.id_code} (PRESS 1:THAAD 2:SAM 3:CIWS)" if selected_contact else "SPAWN: 5:ICBM 6:Jet 7:Drone 8:CIV 9:EW 0:AWACS W:Wave"
        screen.blit(font_sm.render(ovr_text, True, override_color), (pad_x, 65))

        pygame.draw.line(screen, GRID_COLOR, (sidebar_x, 85), (WIDTH, 85), 1)

        y_table = 95
        screen.blit(font_md.render("ACTIVE TARGETS (Sorted by Threat)", True, (255, 200, 0)), (pad_x, y_table))
        
        # คอลัมน์ครบ 10 ช่องตามต้นฉบับ
        table_header = f"{'TRACK ID':<9} | {'STATUS':<9} | {'TYPE':<11} | {'ALT':<4} | {'DIST':<4} | {'AZI':<3} | {'SPD':<3} | {'ETA':<3} | {'SENSOR':<6} | {'INT'}"
        screen.blit(font_sm.render(table_header, True, (150, 150, 150)), (pad_x, y_table + 25))
        pygame.draw.line(screen, (50, 50, 50), (sidebar_x, y_table + 45), (WIDTH, y_table + 45), 1)

        sorted_contacts = sorted(cmd.contacts, key=lambda c: c.calculate_threat_score(), reverse=True)
        max_rows = 15
        
        for i, c in enumerate(sorted_contacts[:max_rows]):
            row_y = y_table + 50 + (i * 20)
            
            if c.status in ["HOSTILE", "ENGAGING"]: r_color = (255, 80, 80)
            elif c.status == "SUSPECT": r_color = (255, 220, 50)
            elif c.status == "FRIENDLY": r_color = (100, 180, 255)
            elif c.status == "INTERCEPTING": r_color = (220, 100, 220)
            else: r_color = (150, 150, 150)

            if selected_contact == c:
                pygame.draw.rect(screen, (50, 50, 80), (sidebar_x + 5, row_y - 2, SIDEBAR_WIDTH - 10, 18))
                r_color = (255, 255, 255)

            t_type = c.type_name if c.type_name != "UNKNOWN" else "???"
            if len(t_type) > 11: t_type = t_type[:9] + ".."
            eta_str = f"{c.get_eta():.0f}s" if c.get_eta() < 999 else "N/A"
            alt_str = f"FL{c.altitude_ft//1000:02d}" 
            
            intercept_str = "---"
            engs = [e for e in cmd.active_engagements if getattr(e, 'target', None) == c]
            if engs:
                soonest = min(engs, key=lambda x: getattr(x, 'time_to_impact', 99))
                wp_n = "F-16" if soonest.weapon_name == "Interceptors" else soonest.weapon_name
                intercept_str = f"{wp_n}({getattr(soonest, 'time_to_impact', 0)}s)"

            bearing = int(getattr(c, 'bearing', getattr(c, 'heading', 0)))
            sensor = getattr(c, 'detected_by', 'RADAR')[:6] 
            
            row_str = f"{c.id_code:<9} | {c.status:<9} | {t_type:<11} | {alt_str:<4} | {c.distance_km:>4.0f} | {bearing:>3}° | {c.speed_mach:>3.1f} | {eta_str:<3} | {sensor:<6} | {intercept_str}"
            screen.blit(font_sm.render(row_str, True, r_color), (pad_x, row_y))

        y_log = y_table + 50 + (max_rows * 20) + 15
        pygame.draw.line(screen, GRID_COLOR, (sidebar_x, y_log - 10), (WIDTH, y_log - 10), 1)
        screen.blit(font_md.render("TACTICAL LOG:", True, RADAR_COLOR), (pad_x, y_log))
        
        max_log_lines = (HEIGHT - y_log - 40) // 18
        recent_logs = cmd.tactical_log[-max_log_lines:] 
        
        for i, log in enumerate(recent_logs):
            screen.blit(font_sm.render(clean_ansi(log)[:85], True, get_log_color(log)), (pad_x, y_log + 25 + (i * 18)))

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
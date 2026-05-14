from datetime import datetime
import time
import random
import os
from config import GameConfig
from targets import ICBM, TacticalBM, Drone, Helicopter, Aircraft, GhostTrack, Airliner, AWACS
from personnel import ThreatQueue, RadarOperator, WeaponOfficer, Engagement

class CommandCenter:
    def __init__(self):
        self.contacts = []
        self.unseen_contacts = []
        self.active_engagements = []
        self.returning_fighters = [] 
        self.base_hp = 100
        self.tick_count = 0
        self.track_counter = 100
        self.threat_queue = ThreatQueue()
        self.wave_cooldown = GameConfig.WAVE_COOLDOWN_INITIAL
        
        self.max_ammo = GameConfig.MAX_AMMO.copy()
        self.ammo = self.max_ammo.copy()
        self.reload_timers = {"THAAD": 0, "SAM": 0, "CIWS": 0} 
        self.awacs_pool = 2
        
        # --- Logistics 60s System ---
        self.idle_timers = {wpn: 0 for wpn in self.max_ammo}
        self.prev_ammo = self.max_ammo.copy()
        
        self.radar_op = RadarOperator("Alpha")
        self.weapon_op = WeaponOfficer("Bravo")
        self.tactical_log = []

    def add_log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.tactical_log.append(f"[{ts}] {msg}")
        if len(self.tactical_log) > 24: self.tactical_log.pop(0)

    def calculate_defcon(self):
        current_defcon = 5 
        for c in self.contacts:
            if not c.active: continue
            if isinstance(c, ICBM) and c.status in ["HOSTILE", "ENGAGING"]: return 1 
            if c.status in ["HOSTILE", "ENGAGING", "SUSPECT", "INTERCEPTING"]:
                if c.distance_km < 80: current_defcon = min(current_defcon, 2) 
                else: current_defcon = min(current_defcon, 3) 
            elif c.status in ["UNIDENTIFIED", "IDENTIFYING"]: current_defcon = min(current_defcon, 4) 
        return current_defcon

    def detect_airspace(self):
        if self.wave_cooldown > 0: self.wave_cooldown -= 1
        
        # Difficulty scales up linearly over time, capping at 3x difficulty
        difficulty_multiplier = min(3.0, 1.0 + (self.tick_count / 1500.0))
        
        # Massive wave system (base 10% chance)
        if self.wave_cooldown <= 0 and random.random() < (0.10 * difficulty_multiplier): 
            self.wave_cooldown = max(80, int(200 / difficulty_multiplier))
            wave_size = int(random.randint(8, 15) * difficulty_multiplier)
            
            wave_theme = random.choices(
                ["MIXED", "BALLISTIC_RAIN", "DRONE_SWARM", "FIGHTER_STRIKE"], 
                weights=[40, 20, 20, 20], k=1)[0]
                
            # ประกาศแบบทางการทหาร
            if wave_theme == "MIXED":
                self.add_log("\033[41;97m[TACTICAL WARNING] 🚨 MULTIPLE HOSTILE CONTACTS INBOUND. BATTLE STATIONS. 🚨\033[0m")
            elif wave_theme == "BALLISTIC_RAIN":
                self.add_log("\033[41;97m[DEFCON 1] 🚨 BALLISTIC MISSILE LAUNCH DETECTED. THAAD BATTERIES TO STANDBY. 🚨\033[0m")
            elif wave_theme == "DRONE_SWARM":
                self.add_log("\033[41;97m[WARNING] 🚨 UNMANNED AERIAL SWARM DETECTED. ACTIVATE CIWS PROTOCOL. 🚨\033[0m")
            elif wave_theme == "FIGHTER_STRIKE":
                self.add_log("\033[41;97m[TACTICAL WARNING] 🚨 HEAVY FIGHTER FORMATION INBOUND. SCRAMBLE ALL INTERCEPTORS. 🚨\033[0m")
            
            for _ in range(wave_size):
                self.track_counter += 1
                
                # ตัด Decoy ออกทั้งหมด
                if wave_theme == "BALLISTIC_RAIN":
                    threat_type = random.choices(["ICBM", "TBM"], weights=[10, 90], k=1)[0]
                elif wave_theme == "DRONE_SWARM":
                    threat_type = "DRONE"
                elif wave_theme == "FIGHTER_STRIKE":
                    threat_type = "FIGHTER" # เครื่องบินรบล้วน
                else: 
                    threat_type = random.choices(
                        ["ICBM", "TBM", "DRONE", "FIGHTER", "HELI"], 
                        weights=[5, 20, 30, 30, 15], k=1)[0] # ปรับน้ำหนักใหม่
                
                if threat_type == "ICBM": 
                    new_contact = ICBM(self.track_counter); new_contact.detected_by = "SPACE-COM"
                elif threat_type == "TBM": 
                    new_contact = TacticalBM(self.track_counter); new_contact.detected_by = "GND-EWR"
                elif threat_type == "DRONE": 
                    new_contact = Drone(self.track_counter); new_contact.detected_by = "AWACS"
                elif threat_type == "HELI": 
                    new_contact = Helicopter(self.track_counter); new_contact.scenario = "HOSTILE_HELI"; new_contact.detected_by = "GND-RADAR"
                else: 
                    new_contact = Aircraft(self.track_counter); new_contact.scenario = "HOSTILE_FIGHTER"; new_contact.detected_by = "GND-RADAR"
                
                self.unseen_contacts.append(new_contact)
                
        # Normal target detection system (base 25% chance)
        elif random.random() < (0.25 * difficulty_multiplier): 
            self.track_counter += 1
            prob = random.random()
            if prob < 0.05: new_contact = ICBM(self.track_counter); new_contact.detected_by = "SPACE-COM"  
            elif prob < 0.1: new_contact = TacticalBM(self.track_counter); new_contact.detected_by = "GND-EWR"  
            elif prob < 0.15: new_contact = Drone(self.track_counter); new_contact.detected_by = "AWACS"    
            elif prob < 0.18: new_contact = Helicopter(self.track_counter); new_contact.detected_by = random.choice(["GND-RADAR", "AWACS"]) 
            elif prob < 0.25: new_contact = Airliner(self.track_counter); new_contact.detected_by = "GND-RADAR" # 7% chance for airliner
            else: new_contact = Aircraft(self.track_counter); new_contact.detected_by = random.choice(["GND-RADAR", "AWACS"]) 
            self.unseen_contacts.append(new_contact)
            
        # False Alarm (Clutter/Ghosts) system (5% chance per tick)
        if random.random() < 0.05:
            self.track_counter += 1
            ghost = GhostTrack(self.track_counter)
            ghost.detected_by = "GND-RADAR"
            self.unseen_contacts.append(ghost)

    def process_reloads(self):
        # --- Base Defense Logistics ---
        for wpn, max_qty in self.max_ammo.items():
            if self.ammo[wpn] == self.prev_ammo[wpn] and self.ammo[wpn] < max_qty:
                self.idle_timers[wpn] += 1
                if self.idle_timers[wpn] >= 120:  
                    self.ammo[wpn] += 1
                    self.idle_timers[wpn] = 0
            else:
                self.idle_timers[wpn] = 0
            self.prev_ammo[wpn] = self.ammo[wpn]

        # Automated AWACS Patrol Swap System
        active_awacs = [c for c in self.contacts if isinstance(c, AWACS)]
        
        # Recover landed AWACS
        for a in active_awacs:
            if a.state == "RTB" and not a.active:
                self.awacs_pool += 1
                self.add_log(f"\033[94m[AIRBASE] {a.id_code} landed safely at Wing 7 and refueling.\033[0m")
                
        # Launch AWACS if none active and pool has aircraft
        flying_awacs = [a for a in active_awacs if a.active]
        if len(flying_awacs) == 0 and self.awacs_pool > 0:
            self.track_counter += 1
            awacs = AWACS(self.track_counter)
            self.contacts.append(awacs)
            self.awacs_pool -= 1
            self.add_log("\033[94m[AIRBASE] Wing 7 launching Saab 340 AEW&C for CAP orbit.\033[0m")
        elif len(flying_awacs) > 0:
            primary_awacs = flying_awacs[0]
            if primary_awacs.fuel < 20.0 and primary_awacs.state == "ON_STATION":
                if self.awacs_pool > 0:
                    self.track_counter += 1
                    relief = AWACS(self.track_counter)
                    self.contacts.append(relief)
                    self.awacs_pool -= 1
                    self.add_log("\033[94m[AIRBASE] Wing 7 launching relief AWACS. Primary AWACS returning to base.\033[0m")
                primary_awacs.state = "RTB"

        self.contacts = [c for c in self.contacts if c.active]
        
        # Standard reload system when ammo depleted
        for wpn in self.reload_timers:
            if self.ammo[wpn] == 0 and self.reload_timers[wpn] == 0:
                self.reload_timers[wpn] = GameConfig.RELOAD_TIMES[wpn]
                self.add_log(f"\033[93m[LOGISTICS]\033[0m {wpn} depleted! Reload sequence initiated.")
            
            if self.reload_timers[wpn] > 0:
                self.reload_timers[wpn] -= 1
                if self.reload_timers[wpn] <= 0:
                    self.ammo[wpn] = self.max_ammo[wpn]
                    self.add_log(f"\033[92m[LOGISTICS]\033[0m {wpn} fully reloaded and ready!")

        # FIGHTER return to base (RTB) system
        updated_rtb = []
        for rtb_time in self.returning_fighters:
            rtb_time -= 1
            if rtb_time <= 0:
                if self.ammo["FIGHTER"] < self.max_ammo["FIGHTER"]:
                    self.ammo["FIGHTER"] += 1
                    self.add_log(f"\033[94m[ATC] FIGHTER landed rearmed & refueled. Ready for tasking. (Standby: {self.ammo['FIGHTER']})\033[0m")
            else:
                updated_rtb.append(rtb_time)
        self.returning_fighters = updated_rtb

    def process_personnel(self):
        radar_result = self.radar_op.tick()
        if radar_result: self.add_log(radar_result)

        if not self.radar_op.is_busy:
            ifos = [c for c in self.contacts if c.status == "UNIDENTIFIED" and c.active]
            if ifos:
                # Automatic target prioritization by ETA
                ifos.sort(key=lambda x: x.distance_km / max(0.1, x.speed_mach))
                
                unidentified_count = len(ifos)
                self.add_log(self.radar_op.start_identifying(ifos[0], unidentified_count))

        wep_result = self.weapon_op.tick(self.ammo)
        if wep_result:
            if isinstance(wep_result, tuple):
                msg, engagement = wep_result; self.add_log(msg); self.active_engagements.append(engagement)
            else: self.add_log(wep_result)

        if not self.weapon_op.is_busy:
            self.threat_queue.build_queue(self.contacts)
            highest_threat = self.threat_queue.pop_highest_priority()
            if highest_threat: self.add_log(self.weapon_op.authorize_engagement(highest_threat))

    def manual_override_fire(self, target, wpn):
        # Altitude Ceilings Check
        alt = target.altitude_ft
        if wpn == "CIWS" and alt > 15000:
            self.add_log(f"\033[91;1m[ERROR] {wpn} CANNOT REACH {alt} FT!\033[0m")
            return
        if wpn == "SAM" and alt > 100000:
            self.add_log(f"\033[91;1m[ERROR] {wpn} CANNOT REACH {alt} FT!\033[0m")
            return
        if wpn == "FIGHTER" and alt > 60000:
            self.add_log(f"\033[91;1m[ERROR] FIGHTER CANNOT REACH {alt} FT!\033[0m")
            return
            
        if self.ammo.get(wpn, 0) > 0:
            self.ammo[wpn] -= 1
            
            display_wpn = wpn
            if wpn == "FIGHTER":
                display_wpn = random.choice(["F-16AM Fighting Falcon", "JAS-39 Gripen", "F-5TH Super Tigris", "T-50TH Golden Eagle", "Alpha Jet"])
                
            impact_time = max(1, int(target.distance_km / max(1, target.speed_mach * 2)))
            self.active_engagements.append(Engagement(target, display_wpn, impact_time))
            target.status = "ENGAGING"
            self.add_log(f"\033[95m[MANUAL OVERRIDE]\033[0m SCRAMBLED {display_wpn} intercepting {target.id_code}")
        else:
            self.add_log(f"\033[91m[WARNING]\033[0m {wpn} Out of Ammo!")

    def manual_spawn(self, target_type):
        self.track_counter += 1
        if target_type == "WAVE":
            for _ in range(5):
                self.manual_spawn("FIGHTER")
            return
            
        if target_type == "ICBM": c = ICBM(self.track_counter); c.detected_by = "SPACE-COM"
        elif target_type == "FIGHTER": c = Aircraft(self.track_counter); c.detected_by = "GND-RADAR"
        elif target_type == "DRONE": c = Drone(self.track_counter); c.detected_by = "GND-RADAR"
        elif target_type == "AIRLINER": c = Airliner(self.track_counter); c.detected_by = "GND-RADAR"
        elif target_type == "EW": c = Aircraft(self.track_counter); c.true_type = "EA-18G Growler (HEAVY EW)"; c.is_heavy_ew = True; c.detected_by = "GND-RADAR"
        elif target_type == "AWACS": c = AWACS(self.track_counter); c.detected_by = "GND-RADAR"
        else: return
        self.unseen_contacts.append(c)
        self.add_log(f"\033[95m[DEV] MANUAL SPAWN: {target_type} inbound.\033[0m")

    def manual_override_abort(self, target):
        aborted = False
        for eng in list(self.active_engagements):
            if getattr(eng, 'target', None) == target:
                self.active_engagements.remove(eng)
                aborted = True
        if aborted:
            target.status = "HOSTILE"
            self.add_log(f"\033[41m[ABORT]\033[0m Cancelled engagement on {target.id_code}")

    def process_engagements(self):
        surviving_engagements = []
        for eng in self.active_engagements:
            
            if eng is None or getattr(eng, 'target', None) is None:
                continue


            if not eng.target.active: 
                if eng.weapon_name not in ["THAAD", "SAM", "CIWS"]:
                    self.returning_fighters.append(GameConfig.F16_RTB_TIME_ASSIST)
                    self.add_log(f"\033[94m[ATC] Target eliminated by other unit. {eng.weapon_name} returning to base (RTB).\033[0m")
                continue 
            
            eng.time_to_impact -= 1
            if eng.time_to_impact <= 0:
                if eng.weapon_name == "THAAD":
                    if random.random() <= GameConfig.HIT_CHANCE_THAAD: 
                        eng.target.status = "CLEARED"; eng.target.active = False
                        self.add_log(f"\033[92m[KILL] DIRECT HIT! {eng.target.id_code} destroyed by THAAD!\033[0m")
                    else:
                        eng.target.status = "HOSTILE"
                        self.add_log(f"\033[91;1m[MISS] THAAD MISSED {eng.target.id_code}! TARGET STILL INCOMING!\033[0m")
                
                elif eng.weapon_name == "SAM":
                    # Chaff Evasion Mechanic
                    if isinstance(eng.target, Aircraft) and random.random() < 0.25:
                        eng.target.status = "HOSTILE"
                        self.add_log(f"\033[93m[EW] {eng.target.id_code} DEPLOYED CHAFF! SAM DECOYED!\033[0m")
                        continue
                        
                    base_hit = GameConfig.HIT_CHANCE_SAM_NUKE if isinstance(eng.target, ICBM) else \
                               (GameConfig.HIT_CHANCE_SAM_TBM if isinstance(eng.target, TacticalBM) else GameConfig.HIT_CHANCE_SAM_NORMAL)
                    
                    # Kinematic modifier: Harder to hit fast targets
                    speed_penalty = max(0.0, (eng.target.speed_mach - 1.0) * 0.10) # -10% per Mach above Mach 1
                    final_hit_chance = max(0.05, base_hit - speed_penalty)
                    
                    if random.random() <= final_hit_chance: 
                        eng.target.status = "CLEARED"; eng.target.active = False
                        if isinstance(eng.target, Airliner):
                            self.base_hp = 0
                            self.add_log(f"\033[41;97m[CRITICAL INCIDENT] YOU SHOT DOWN A COMMERCIAL AIRLINER! COURT-MARTIAL IMMINENT!\033[0m")
                        else:
                            self.add_log(f"\033[92m[KILL] SPLASH! {eng.target.id_code} destroyed by SAM!\033[0m")
                    else:
                        eng.target.status = "HOSTILE"
                        self.add_log(f"\033[91;1m[MISS] SAM MISSED {eng.target.id_code}!\033[0m")
                
                elif eng.weapon_name not in ["THAAD", "SAM", "CIWS"]: # Fighter Intercept
                    self.returning_fighters.append(GameConfig.F16_RTB_TIME_KILL) 
                    
                    scen = getattr(eng.target, 'scenario', None)
                    if scen in ["RADIO_FAIL", "STRAYED"]: 
                        eng.target.status = "CLEARED"; eng.target.active = False
                        self.add_log(f"\033[94m[INTERCEPT]\033[0m {eng.target.id_code} complied. {eng.weapon_name} is RTB.\033[0m")
                    else:
                        # Kinematics for FIGHTER AMRAAMs
                        speed_penalty = max(0.0, (eng.target.speed_mach - 1.5) * 0.15)
                        final_hit_chance = max(0.10, GameConfig.HIT_CHANCE_F16 - speed_penalty)
                        
                        if random.random() <= final_hit_chance: 
                            eng.target.status = "CLEARED"; eng.target.active = False
                            if isinstance(eng.target, Airliner):
                                self.base_hp = 0
                                self.add_log(f"\033[41;97m[CRITICAL INCIDENT] YOU SHOT DOWN A COMMERCIAL AIRLINER! COURT-MARTIAL IMMINENT!\033[0m")
                            else:
                                self.add_log(f"\033[92m[KILL]\033[0m FOX-3! {eng.target.id_code} splashed by {eng.weapon_name}! {eng.weapon_name} is RTB.\033[0m")
                        else:
                            eng.target.status = "HOSTILE"
                            self.add_log(f"\033[91;1m[MISS]\033[0m {eng.target.id_code} survived {eng.weapon_name} attack! {eng.weapon_name} is RTB.\033[0m")
            else:
                surviving_engagements.append(eng)

        self.active_engagements = surviving_engagements

    def process_auto_ciws(self):
        # Auto-CIWS with dynamic engagement range
        for c in self.contacts:
            engage_range = max(5.0, c.speed_mach * 1.5) 
            
            if c.active and c.distance_km <= engage_range and c.status not in ["FRIENDLY", "CLEARED"]:
                if self.ammo["CIWS"] > 0:
                    # Higher speed targets require more ammunition spread
                    curtain_spread = max(1, int(c.speed_mach)) 
                    ammo_used = min(curtain_spread, self.ammo["CIWS"])
                    self.ammo["CIWS"] -= ammo_used
                    
                    hit_multiplier = 1.0 + (ammo_used * 0.10) 
                    speed_penalty = max(0.0, (c.speed_mach - 0.5) * 0.15) # CIWS struggles with Mach 2+ targets
                    final_hit_chance = max(0.05, min(0.95, GameConfig.HIT_CHANCE_CIWS * hit_multiplier - speed_penalty))
                    
                    if random.random() <= final_hit_chance:
                        self.add_log(f"\033[91;1m[AUTO-CIWS] BRRRRRRT! (Spread x{ammo_used}) {c.id_code} SHREDDED! (Ammo: {self.ammo['CIWS']})\033[0m")
                        c.status = "CLEARED"; c.active = False
                    else:
                        if self.tick_count % 2 == 0: 
                            self.add_log(f"\033[93;1m[AUTO-CIWS] BRRRRRRT! MISSED {c.id_code} DESPITE SPREAD! TARGET EVADED!\033[0m")
                else:
                    if self.tick_count % 3 == 0: self.add_log(f"\033[41;97m[AUTO-CIWS] CLICK! CIWS RELOADING! BRACE FOR IMPACT: {c.id_code}!\033[0m")

    def update_world(self):
        # Identify active Jammers (must be HOSTILE) and AWACS
        ew_aircrafts = [c for c in self.contacts if c.active and getattr(c, 'status', '') == 'HOSTILE' and "EW" in getattr(c, 'type_name', '')]
        has_awacs = any(isinstance(c, AWACS) for c in self.contacts if c.active)
        effective_radar_alt = 35000 if has_awacs else 150 # AWACS looks down from 35,000 ft, massively extending radar horizon!
        
        # Process unseen contacts (move them, check if they cross the detection threshold)
        surviving_unseen = []
        for c in self.unseen_contacts:
            if c.active:
                c.move()
                
                # Check if target is inside any EW jammer's directional strobe (+/- 10 degrees)
                is_jammed = False
                for ew in ew_aircrafts:
                    if ew != c:
                        # Shortest angle difference between the target and the jammer
                        angle_diff = abs((c.bearing - ew.bearing + 180) % 360 - 180)
                        if angle_diff <= 10.0:
                            is_jammed = True
                            break
                            
                jamming_factor = 0.3 if is_jammed else 1.0 # 30% range if in the jammer's sector
                
                if c.is_detectable_by_radar(radar_alt_ft=effective_radar_alt, jamming_factor=jamming_factor):
                    self.contacts.append(c)
                    self.add_log(f"\033[90m[SYS] NEW TRACK: {c.id_code} appeared on radar.\033[0m")
                elif c.distance_km <= 0:
                    c.active = False
                    self.base_hp -= GameConfig.DAMAGE_AIRCRAFT
                    self.add_log(f"\033[41;97m[DEFENSE] AMBUSH! {c.id_code} hit base below radar horizon!\033[0m")
                else:
                    surviving_unseen.append(c)
        self.unseen_contacts = surviving_unseen

        # Process visible contacts
        for c in self.contacts:
            if c.active:
                c.move()
                
                if c.status == "FRIENDLY" and random.random() < 0.03:
                    c.active = False; self.add_log(f"\033[94m[TRAFFIC] {c.id_code} has left the monitored sector.\033[0m")
                    continue

                if c.distance_km <= 0:
                    c.active = False
                    if c.status == "FRIENDLY": 
                        self.add_log(f"\033[94m[TRAFFIC] {c.id_code} safely passed through airspace.\033[0m")
                    elif c.status in ["HOSTILE", "ENGAGING", "UNIDENTIFIED", "IDENTIFYING", "SUSPECT", "INTERCEPTING"]:
                        damage = GameConfig.DAMAGE_ICBM if isinstance(c, ICBM) else \
                                 (GameConfig.DAMAGE_TBM if isinstance(c, TacticalBM) else GameConfig.DAMAGE_AIRCRAFT)
                        self.base_hp -= damage
                        self.add_log(f"\033[41;97m[DEFENSE] CRITICAL! {c.id_code} hit the base! HP -{damage}\033[0m")
                        
                        if self.base_hp > 0:
                            lost_ammo_msgs = []
                            for wpn in self.ammo:
                                if self.ammo[wpn] > 0:
                                    loss = int(self.ammo[wpn] * random.uniform(0.15, 0.40))
                                    if loss == 0 and random.random() > 0.5: loss = 1
                                    if loss > 0:
                                        self.ammo[wpn] -= loss; lost_ammo_msgs.append(f"{wpn} -{loss}")
                            if lost_ammo_msgs: self.add_log(f"\033[43;30m[DAMAGE] Ammo cache hit by explosion! Lost: {', '.join(lost_ammo_msgs)}\033[0m")

        self.contacts = [c for c in self.contacts if c.active]
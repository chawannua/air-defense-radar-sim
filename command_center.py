# command_center.py
import time
import random
import os
from datetime import datetime
from config import GameConfig
from targets import ICBM, TacticalBM, Drone, Helicopter, Aircraft
from personnel import ThreatQueue, RadarOperator, WeaponOfficer, Engagement

class CommandCenter:
    def __init__(self):
        self.contacts = []
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
        
        # Massive wave system (10% chance)
        if self.wave_cooldown <= 0 and random.random() < 0.10: 
            self.wave_cooldown = 200
            wave_size = random.randint(8, 15)
            
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
                
                self.contacts.append(new_contact)
                
        # Normal target detection system
        elif random.random() < 0.25: 
            self.track_counter += 1
            prob = random.random()
            if prob < 0.05: new_contact = ICBM(self.track_counter); new_contact.detected_by = "SPACE-COM"  
            elif prob < 0.1: new_contact = TacticalBM(self.track_counter); new_contact.detected_by = "GND-EWR"  
            elif prob < 0.15: new_contact = Drone(self.track_counter); new_contact.detected_by = "AWACS"    
            elif prob < 0.18: new_contact = Helicopter(self.track_counter); new_contact.detected_by = random.choice(["GND-RADAR", "AWACS"]) 
            else: new_contact = Aircraft(self.track_counter); new_contact.detected_by = random.choice(["GND-RADAR", "AWACS"]) 
            self.contacts.append(new_contact)
            self.add_log(f"\033[90m[SYS] RAW CONTACT: {new_contact.id_code} detected by {new_contact.detected_by}.\033[0m")

    def process_reloads(self):
        # Ammo tracking and supply system
        for wpn in self.ammo:
            if self.ammo[wpn] < self.prev_ammo[wpn]:
                self.idle_timers[wpn] = 0  
            else:
                self.idle_timers[wpn] += 1 
            
            self.prev_ammo[wpn] = self.ammo[wpn]

            if self.idle_timers[wpn] >= 60 and self.ammo[wpn] < self.max_ammo[wpn]:
                self.ammo[wpn] = self.max_ammo[wpn]
                self.idle_timers[wpn] = 0
                if wpn in self.reload_timers: self.reload_timers[wpn] = 0
                if wpn == "F-16": self.returning_fighters.clear() 
                self.add_log(f"\033[96m[SUPPLY]\033[0m {wpn} unused for 60s. Auto-restocked to full capacity!")

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

        # F-16 return to base (RTB) system
        updated_rtb = []
        for rtb_time in self.returning_fighters:
            rtb_time -= 1
            if rtb_time <= 0:
                if self.ammo["F-16"] < self.max_ammo["F-16"]:
                    self.ammo["F-16"] += 1
                    self.add_log(f"\033[94m[ATC] F-16 landed rearmed & refueled. Ready for tasking. (Standby: {self.ammo['F-16']})\033[0m")
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

    def process_engagements(self):
        surviving_engagements = []
        for eng in self.active_engagements:
            
            if eng is None or getattr(eng, 'target', None) is None:
                continue


            if not eng.target.active: 
                if eng.weapon_name == "Interceptors":
                    self.returning_fighters.append(GameConfig.F16_RTB_TIME_ASSIST)
                    self.add_log(f"\033[94m[ATC] Target eliminated by other unit. F-16 returning to base (RTB).\033[0m")
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
                    hit_chance = GameConfig.HIT_CHANCE_SAM_NUKE if isinstance(eng.target, ICBM) else \
                                 (GameConfig.HIT_CHANCE_SAM_TBM if isinstance(eng.target, TacticalBM) else GameConfig.HIT_CHANCE_SAM_NORMAL)
                    
                    if random.random() <= hit_chance: 
                        eng.target.status = "CLEARED"; eng.target.active = False
                        self.add_log(f"\033[92m[KILL] SPLASH! {eng.target.id_code} destroyed by SAM!\033[0m")
                    else:
                        eng.target.status = "HOSTILE"
                        self.add_log(f"\033[91;1m[MISS] SAM MISSED {eng.target.id_code}!\033[0m")
                
                elif eng.weapon_name == "Interceptors":
                    self.returning_fighters.append(GameConfig.F16_RTB_TIME_KILL) 
                    
                    scen = getattr(eng.target, 'scenario', None)
                    if scen in ["RADIO_FAIL", "STRAYED"]: 
                        eng.target.status = "CLEARED"; eng.target.active = False
                        self.add_log(f"\033[94m[INTERCEPT]\033[0m {eng.target.id_code} complied. F-16 is RTB.\033[0m")
                    else:
                        if random.random() <= GameConfig.HIT_CHANCE_F16: 
                            eng.target.status = "CLEARED"; eng.target.active = False
                            self.add_log(f"\033[92m[KILL]\033[0m FOX-3! {eng.target.id_code} splashed by F-16! F-16 is RTB.\033[0m")
                        else:
                            eng.target.status = "HOSTILE"
                            self.add_log(f"\033[91;1m[MISS]\033[0m {eng.target.id_code} survived F-16 attack! F-16 is RTB.\033[0m")
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
                    final_hit_chance = min(0.95, GameConfig.HIT_CHANCE_CIWS * hit_multiplier)
                    
                    if random.random() <= final_hit_chance:
                        self.add_log(f"\033[91;1m[AUTO-CIWS] BRRRRRRT! (Spread x{ammo_used}) {c.id_code} SHREDDED! (Ammo: {self.ammo['CIWS']})\033[0m")
                        c.status = "CLEARED"; c.active = False
                    else:
                        if self.tick_count % 2 == 0: 
                            self.add_log(f"\033[93;1m[AUTO-CIWS] BRRRRRRT! MISSED {c.id_code} DESPITE SPREAD! TARGET EVADED!\033[0m")
                else:
                    if self.tick_count % 3 == 0: self.add_log(f"\033[41;97m[AUTO-CIWS] CLICK! CIWS RELOADING! BRACE FOR IMPACT: {c.id_code}!\033[0m")

    def update_world(self):
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
                        damage = GameConfig.DAMAGE_NUKE if isinstance(c, ICBM) else \
                                 (GameConfig.DAMAGE_TBM if isinstance(c, TacticalBM) else GameConfig.DAMAGE_NORMAL)
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

    def format_ammo_display(self, wpn):
        if wpn != "F-16" and self.reload_timers[wpn] > 0:
            return f"\033[33mRLD {self.reload_timers[wpn]:02d}s\033[0m"
        return f"{self.ammo[wpn]:02d}/{self.max_ammo[wpn]:02d}"

    def get_intercept_info(self, contact):
        engs = [e for e in self.active_engagements if e.target == contact]
        if engs:
            soonest = min(engs, key=lambda x: x.time_to_impact)
            wpn_name = "F-16" if soonest.weapon_name == "Interceptors" else soonest.weapon_name
            return f"{wpn_name}:{soonest.time_to_impact}s"
        return "---"

    def display_dashboard(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        width = 162 
        defcon_level = self.calculate_defcon()
        if defcon_level == 1: defcon_color = "\033[41;97m" 
        elif defcon_level == 2: defcon_color = "\033[41;33m" 
        elif defcon_level == 3: defcon_color = "\033[43;30m" 
        elif defcon_level == 4: defcon_color = "\033[44;97m" 
        else: defcon_color = "\033[42;97m" 

        print(f" {defcon_color} [ DEFCON {defcon_level} ] \033[0m  🛡️  CEI TACTICAL AIRSPACE  |  TICK: {self.tick_count:04d}  |  BASE HP: {self.base_hp}%")
        
        airborne_f16 = len(self.returning_fighters)
        f16_status = f"{self.format_ammo_display('F-16')} \033[94m(RTB: {airborne_f16})\033[0m" if airborne_f16 > 0 else self.format_ammo_display('F-16')
        
        armory_str = f" 💣 ARMORY: [THAAD: {self.format_ammo_display('THAAD')}] | [F-16s: {f16_status}] | [SAMs: {self.format_ammo_display('SAM')}] | [CIWS: {self.format_ammo_display('CIWS')}]"
        print(armory_str)
        
        print("="*width)
        print(f" {'TRACK/CALLSIGN':<16} | {'THREAT':<7} | {'STATUS':<12} | {'AIRCRAFT TYPE':<24} | {'DIST (km)':<9} | {'ALT (ft)':<8} | {'SPD (M)':<7} | {'ETA (s)':<7} | {'WPN/INTCPT':<12} | {'SENSOR'}")
        print("-" * width)

        sorted_contacts = sorted(self.contacts, key=lambda c: c.calculate_threat_score(), reverse=True)
        if not sorted_contacts: 
            print(f" {'--':<16} | {'--':<7} | {'CLEAR':<12} | {'--':<24} | {'--':<9} | {'--':<8} | {'--':<7} | {'--':<7} | {'--':<12} | {'--'}")
        else:
            for c in sorted_contacts:
                reset = "\033[0m"
                if isinstance(c, ICBM) and c.status in ["HOSTILE", "ENGAGING"]: color = "\033[41;97m" 
                elif isinstance(c, TacticalBM) and c.status in ["HOSTILE", "ENGAGING"]: color = "\033[43;30m" 
                else:
                    if c.status == "UNIDENTIFIED": color = "\033[90m" 
                    elif c.status == "IDENTIFYING": color = "\033[37m" 
                    elif c.status == "FRIENDLY": color = "\033[94m" 
                    elif c.status == "SUSPECT": color = "\033[33m" 
                    elif c.status == "INTERCEPTING": color = "\033[95m" 
                    elif c.status == "HOSTILE": color = "\033[91m" 
                    elif c.status == "ENGAGING": color = "\033[91;1m" 
                    else: color = reset
                t_type = c.type_name if c.type_name != "UNKNOWN" else "???"
                eta_str = f"{c.get_eta():.0f}" if c.get_eta() < 999 else "N/A"
                score = c.calculate_threat_score() if c.status not in ["FRIENDLY", "UNIDENTIFIED", "IDENTIFYING"] else "---"
                intercept_str = self.get_intercept_info(c)
                
                print(f" {color}{c.id_code:<16} | {score:<7} | {c.status:<12} | {t_type:<24} | {c.distance_km:>7.1f}   | {c.altitude_ft:>8} | {c.speed_mach:>7.1f} | {eta_str:>7} | {intercept_str:<12} | {c.detected_by}{reset}")

        print("\n" + "="*width)
        print(" 📻 TACTICAL LOG:")
        for log in self.tactical_log: print(f"  > {log}")
        print("="*width)

    def run(self):
        for _ in range(5): self.detect_airspace() 
        while self.base_hp > 0:
            self.tick_count += 1
            self.detect_airspace()
            self.process_reloads()
            self.process_personnel()
            self.process_engagements()
            self.process_auto_ciws()
            self.update_world()
            self.display_dashboard()
            time.sleep(1.0)
            
        print("\n\033[41;97m 💀 BASE DESTROYED! ALL SYSTEMS OFFLINE! 💀 \033[0m\n")
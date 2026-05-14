# personnel.py
import random
import heapq
import math
from config import GameConfig
from targets import ICBM, TacticalBM, Drone, Helicopter, Aircraft

class ThreatQueue:
    def __init__(self):
        self.heap = []
        self.counter = 0

    def build_queue(self, contacts):
        self.heap = []
        for contact in contacts:
            if contact.active and contact.status in ["HOSTILE", "SUSPECT"]:
                score = contact.calculate_threat_score()
                heapq.heappush(self.heap, (-score, self.counter, contact))
                self.counter += 1

    def pop_highest_priority(self):
        if self.heap: return heapq.heappop(self.heap)[2]
        return None

def get_closest_airbase(target):
    closest_base = (0, 0, "HQ", "F-16AM Fighting Falcon")
    min_dist = float('inf')
    for bx, by, bname, baircraft in getattr(GameConfig, 'AIRBASES', []):
        d = math.hypot(target.x_km - bx, target.y_km - by)
        if d < min_dist:
            min_dist = d
            closest_base = (bx, by, bname, baircraft)
    return closest_base

class Engagement:
    def __init__(self, target, weapon_name, time_to_impact, origin_x=0.0, origin_y=0.0):
        self.target = target
        self.weapon_name = weapon_name
        self.time_to_impact = time_to_impact
        self.origin_x_km = origin_x
        self.origin_y_km = origin_y

class RadarOperator:
    def __init__(self, name):
        self.name = name; self.is_busy = False; self.timer = 0; self.current_task = None

    def start_identifying(self, contact, unidentified_count=0):
        self.is_busy = True
        self.current_task = contact
        contact.status = "IDENTIFYING"
        
        # Check for overload (>8 unidentified contacts)
        is_overload = unidentified_count > 8
        speed_boost = 2 if is_overload else 1
        
        # Update prefix message if busy
        prefix = "\033[41;97m[BATTLE STATIONS] OVERLOAD IDENTIFY!\033[0m \033[96m[RADAR]\033[0m" if is_overload else "\033[96m[RADAR]\033[0m"
        
        if contact.has_transponder:
            self.timer = 1 
            return f"{prefix} IFF Active. Auto-resolving {contact.id_code}..."
        else:
            base_time = random.randint(3, 6) + (8 if contact.rcs < 0.1 else 0)
            self.timer = max(1, base_time // speed_boost)
            
            return f"{prefix} Interrogating {contact.id_code} (Military/No IFF). Takes ~{self.timer}s..."

    def tick(self):
        if self.is_busy:
            self.timer -= 1
            if self.timer <= 0:
                self.is_busy = False; contact = self.current_task; self.current_task = None
                if contact.active:
                    old_id = contact.id_code; contact.identify_target()
                    if isinstance(contact, ICBM): return f"\033[41;97m[RADAR] 🚨 NUCLEAR LAUNCH DETECTED BY SPACE-COM! 🚨\033[0m"
                    elif isinstance(contact, TacticalBM): return f"\033[41;93m[RADAR] TACTICAL BALLISTIC MISSILE DETECTED!\033[0m"
                    elif contact.status == "SUSPECT": return f"\033[93m[IFF]\033[0m CAUTION! {contact.id_code} is UNRESPONSIVE."
                    elif contact.status == "FRIENDLY": return f"\033[94m[IFF]\033[0m {old_id} Confirmed FRIENDLY. Callsign: {contact.id_code}.\033[0m"
                    else: return f"\033[91m[IFF]\033[0m WARNING! {contact.id_code} is HOSTILE ({contact.type_name})."
        return None

class WeaponOfficer:
    def __init__(self, name):
        self.name = name; self.is_busy = False; self.timer = 0; self.current_task = None

    def authorize_engagement(self, target):
        self.is_busy = True; self.timer = random.randint(3, 5); self.current_task = target
        if target.status == "SUSPECT": target.status = "INTERCEPTING"; return f"\033[95m[WEAPON]\033[0m Scramble ordered for: {target.id_code}..."
        else: target.status = "ENGAGING"; return f"\033[93m[WEAPON]\033[0m Target Locked: {target.id_code}. Authorizing launch sequence..."

    def tick(self, ammo):
        if self.is_busy:
            self.timer -= 1
            if self.timer <= 0:
                self.is_busy = False; target = self.current_task; self.current_task = None
                if not target.active: return None
                
                if isinstance(target, (ICBM, TacticalBM)):
                    if ammo["THAAD"] > 0:
                        weapon, prep_time = "THAAD", GameConfig.PREP_TIME_THAAD
                        ammo["THAAD"] -= 1
                        # Head-on intercept physics
                        closure_rate = target.speed_mach + GameConfig.WEAPON_SPEED_THAAD
                        impact_time = int(target.distance_km / closure_rate) + prep_time
                        return f"\033[41;97m[LAUNCH]\033[0m FIRING THAAD AT {target.id_code}! ({ammo['THAAD']} left)", Engagement(target, weapon, impact_time)
                    elif ammo["SAM"] > 0 and target.distance_km <= 200:
                        weapon, prep_time = "SAM", GameConfig.PREP_TIME_SAM
                        ammo["SAM"] -= 1
                        closure_rate = target.speed_mach + GameConfig.WEAPON_SPEED_SAM
                        impact_time = int(target.distance_km / closure_rate) + prep_time
                        return f"\033[43;30m[LAUNCH]\033[0m DESPERATE MEASURE! FIRING SAM AT BALLISTIC TARGET {target.id_code}! ({ammo['SAM']} left)", Engagement(target, weapon, impact_time)
                    else:
                        target.status = "HOSTILE"; return f"\033[41;93m[WEAPON] OUT OF OPTIONS FOR {target.id_code}!\033[0m", None
                        
                elif isinstance(target, (Drone, Helicopter)):
                    if target.distance_km > 50 and ammo["FIGHTER"] > 0:
                        bx, by, bname, baircraft = get_closest_airbase(target)
                        fighter_type = baircraft
                        weapon, prep_time = fighter_type, GameConfig.PREP_TIME_F16
                        ammo["FIGHTER"] -= 1 
                        # Time to impact based on distance from base instead of center
                        dist_from_base = math.hypot(target.x_km - bx, target.y_km - by)
                        closure_rate = target.speed_mach + GameConfig.WEAPON_SPEED_F16
                        impact_time = int(dist_from_base / closure_rate) + prep_time
                        return f"\033[95m[LAUNCH]\033[0m SCRAMBLE! {fighter_type} launched from {bname} intercepting {target.id_code}.", Engagement(target, weapon, impact_time, bx, by)
                    elif ammo["SAM"] > 0:
                        weapon, prep_time = "SAM", GameConfig.PREP_TIME_SAM
                        ammo["SAM"] -= 1
                        closure_rate = target.speed_mach + GameConfig.WEAPON_SPEED_SAM
                        impact_time = int(target.distance_km / closure_rate) + prep_time
                        return f"\033[95m[LAUNCH]\033[0m Firing SAM at {target.id_code}. ({ammo['SAM']} left)", Engagement(target, weapon, impact_time, 0, 0)
                    else:
                        target.status = "HOSTILE"; return f"\033[91m[WEAPON] SAM RELOADING! {target.id_code} slipping through!\033[0m", None
                
                elif isinstance(target, Aircraft):
                    if target.distance_km > 80:
                        if ammo["FIGHTER"] > 0:
                            bx, by, bname, baircraft = get_closest_airbase(target)
                            fighter_type = baircraft
                            weapon, prep_time = fighter_type, GameConfig.PREP_TIME_F16
                            ammo["FIGHTER"] -= 1 
                            dist_from_base = math.hypot(target.x_km - bx, target.y_km - by)
                            closure_rate = target.speed_mach + GameConfig.WEAPON_SPEED_F16
                            impact_time = int(dist_from_base / closure_rate) + prep_time
                            return f"\033[95m[LAUNCH]\033[0m SCRAMBLE! {fighter_type} launched from {bname}. ({ammo['FIGHTER']} jets left)", Engagement(target, weapon, impact_time, bx, by)
                        else:
                            target.status = "HOSTILE"; return f"\033[93m[WEAPON] ALL FIGHTERs ARE BUSY! Waiting for SAM range.\033[0m", None
                    else:
                        if ammo["SAM"] > 0:
                            weapon, prep_time = "SAM", GameConfig.PREP_TIME_SAM
                            ammo["SAM"] -= 1
                            closure_rate = target.speed_mach + GameConfig.WEAPON_SPEED_SAM
                            impact_time = int(target.distance_km / closure_rate) + prep_time
                            return f"\033[93m[LAUNCH]\033[0m LETHAL RANGE! Firing SAM at {target.id_code} ({ammo['SAM']} left)", Engagement(target, weapon, impact_time)
                        else:
                            target.status = "HOSTILE"; return f"\033[91m[WEAPON] SAM RELOADING! Brace for impact!\033[0m", None
        return None
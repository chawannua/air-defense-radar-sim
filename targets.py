# targets.py
import random
import math
from abc import ABC, abstractmethod

class AirContact(ABC):
    def __init__(self, track_number, distance_km):
        self.track_number = track_number
        self.id_code = f"IFO-{track_number}"
        self.callsign = "UNKNOWN"
        self.distance_km = distance_km
        self.active = True
        self.status = "UNIDENTIFIED" 
        
        self.bearing = random.randint(0, 359)
        self.speed_mach = 0.0
        self.altitude_ft = 0
        # Target flies directly towards the radar (the base)
        self.heading = (self.bearing + 180) % 360
        self.rcs = 0.0
        self.size = "UNKNOWN"
        self.type_name = "UNKNOWN"
        self.is_friendly = False
        
        self.has_transponder = False
        self.squawk_code = f"{random.randint(1000, 7700)}"
        self.departure = "UNKNOWN"
        self.destination = "UNKNOWN"
        self.detected_by = "UNKNOWN"
        
        # 🟢 เพิ่มคุณสมบัติจอมกวนสัญญาณระดับหนัก
        self.is_heavy_ew = False

    @abstractmethod
    def identify_target(self): pass

    def is_detectable_by_radar(self, radar_alt_ft=150, jamming_factor=1.0):
        # Space-Command and Strategic Early Warning Radars bypass local horizon
        if self.detected_by in ["SPACE-COM", "GND-EWR"]:
            return True
            
        # 1. Radar Horizon Check (Earth's curvature)
        # Formula: Distance to horizon (nm) = 1.23 * (sqrt(radar_alt) + sqrt(target_alt))
        # 1 nm = 1.852 km
        radar_horizon_km = 1.852 * 1.23 * (math.sqrt(max(0, radar_alt_ft)) + math.sqrt(max(0, self.altitude_ft)))
        if self.distance_km > radar_horizon_km:
            return False
            
        # 2. RCS Detection Check with Jamming (Simplified Radar Range Equation & Burn-through)
        # Baseline: Can detect 1.0 m^2 target at 400 km
        # Max Range = Baseline_Range * (RCS / Baseline_RCS)^(1/4) * Jamming_Factor
        max_detection_range = 400.0 * (max(0.001, self.rcs) ** 0.25) * jamming_factor
        if self.distance_km > max_detection_range:
            return False
            
        return True

    def get_eta(self):
        speed_per_tick = self.speed_mach * 1.0 
        return self.distance_km / speed_per_tick if speed_per_tick > 0 else 999

    def calculate_threat_score(self):
        if self.status == "FRIENDLY": return 0
        if self.status in ["UNIDENTIFIED", "IDENTIFYING"]: return 50
        
        score = 0
        if self.speed_mach > 3.0: score += 1000 
        elif self.speed_mach > 1.0: score += 500
        distance_factor = max(1, self.distance_km)
        score += int(10000 / distance_factor)
        if self.altitude_ft < 5000: score += 300 
        if self.rcs < 1.0: score += 200 
        return score

    def move(self):
        speed_per_tick = self.speed_mach * 1.0
        self.distance_km -= speed_per_tick
        if self.distance_km < 0:
            self.distance_km = 0

class Aircraft(AirContact):
    def __init__(self, track_number):
        super().__init__(track_number, random.randint(300, 800))
        self.speed_mach = random.uniform(0.7, 2.5)
        self.altitude_ft = random.randint(15000, 45000)
        self.rcs = random.uniform(0.1, 10.0)
        
        # 🟢 ปรับเรทเกิดใหม่: พลเรือน (Commercial) 70%, ข้าศึก 30%
        self.is_friendly = random.choices([True, False], weights=[80, 20], k=1)[0]
        self.has_transponder = self.is_friendly

        if self.is_friendly:
            self.true_type = random.choice([
                "Thai Airways B777", "AirAsia A320", "Nok Air B737", "Bangkok Airways A319", "Cessna 172", 
                "JAS-39 VIP Escort", "C-130H Hercules (RTAF)"
            ])
            self.scenario = "COMMERCIAL"
        else:
            combat_aircraft = [
                "Su-30MKM Flanker", "MiG-29 Fulcrum", "J-10C Vigorous Dragon", "FC-1 Xiaolong",
                "Su-27SK Flanker", "Su-35S Flanker-E", "F-16A/B Block 15", "Yak-130", 
                "H-6K Badger", "Su-22M4 Fitter"
            ]
            
            ew_aircraft = [
                "EC-130H Compass Call EW", "RC-135 Rivet Joint EW", 
                "Su-34 Fullback EW", "Il-22PP Porubschik EW", "Tu-214R EW",
                "J-16D Roaring Dragon EW", "Y-8 High New EW", "Y-9G EW",
                "Saab 340 AEW&C", "A-50 Mainstay AWACS", "KJ-500 AWACS"
            ]
            
            # โอกาส 35% เป็น EW (จาก 30% ของข้าศึกทั้งหมด)
            if random.randint(1, 100) <= 30:
                # โอกาส 10% ของกลุ่ม EW ที่จะเป็นบอสใหญ่ EA-18G
                if random.randint(1, 100) <= 20:
                    self.true_type = "EA-18G Growler (HEAVY EW)"
                    self.is_heavy_ew = True 
                else:
                    self.true_type = random.choice(ew_aircraft)
            else:
                self.true_type = random.choice(combat_aircraft)
                
            self.scenario = "STRIKE"

    def identify_target(self):
        self.type_name = self.true_type
        self.status = "FRIENDLY" if self.is_friendly else "HOSTILE"
        prefix = "CIV" if self.is_friendly else "BOGEY"
        self.id_code = f"{prefix}-{self.track_number}"
        self.callsign = f"{prefix}{random.randint(100, 999)}"
        if self.is_friendly:
            self.departure = random.choice(["VTBS", "VTBD", "VTSP", "VTCC", "VTSG"]) # BKK, DMK, HKT, CNX, KBV
            self.destination = random.choice(["WMKK", "VYYY", "VLVT", "VVDN", "WSSS"]) # KUL, RGN, VTE, DAD, SIN

class Helicopter(AirContact):
    def __init__(self, track_number):
        super().__init__(track_number, random.randint(50, 150))
        self.speed_mach = random.uniform(0.1, 0.3); self.altitude_ft = random.randint(500, 5000)
        self.rcs = random.uniform(2.0, 5.0); self.is_friendly = False; self.has_transponder = False
        
        self.true_type = random.choice([
            "AH-64 Apache", "Mi-28 Havoc", "UH-60 Blackhawk", "Ka-52 Alligator", 
            "Mi-24 Hind", "CH-47 Chinook", "AH-1Z Viper", "Z-10 Fierce Thunderbolt",
            "Eurocopter Tiger", "AW159 Wildcat", "Mi-8 Hip"
        ])
        self.scenario = "CAS"

    def identify_target(self):
        self.type_name = self.true_type; self.status = "HOSTILE"; self.id_code = f"HELO-{self.track_number}"

class Drone(AirContact):
    def __init__(self, track_number):
        super().__init__(track_number, random.randint(100, 300))
        self.speed_mach = random.uniform(0.1, 0.6); self.altitude_ft = random.randint(2000, 20000)
        self.rcs = random.uniform(0.01, 0.5); self.is_friendly = False; self.has_transponder = False
        
        self.true_type = random.choice([
            "MQ-9 Reaper", "RQ-4 Global Hawk", "RQ-170 Sentinel", "MQ-1 Predator",
            "Bayraktar TB2", "Bayraktar Akinci", 
            "Shahed-136", "Mohajer-6",
            "Orlan-10", "Kronshtadt Orion",
            "Wing Loong II", "CH-4 Rainbow", "WZ-7 Soaring Dragon",
            "Switchblade 600"
        ])
        self.scenario = "RECON"

    def identify_target(self):
        self.type_name = self.true_type; self.status = "HOSTILE"; self.id_code = f"UAV-{self.track_number}"

class TacticalBM(AirContact):
    def __init__(self, track_number):
        super().__init__(track_number, random.randint(800, 1500)) 
        self.speed_mach = random.uniform(6.0, 10.0); self.altitude_ft = random.randint(80000, 150000)
        self.rcs = random.uniform(0.5, 1.0); self.is_friendly = False; self.has_transponder = False
        
        self.true_type = random.choice([
            "Iskander-M", "Kinzhal Aero-Ballistic", "Zircon Hypersonic", "Tochka-U",
            "ATACMS", "PrSM",
            "DF-15", "DF-21D Carrier Killer", "DF-17 Hypersonic",
            "SCUD-B", "Fateh-110", "Zolfaghar",
            "Hyunmoo-2"
        ])
        self.scenario = "BALLISTIC"

    def identify_target(self):
        self.type_name = self.true_type; self.status = "HOSTILE"; self.id_code = f"TBM-{self.track_number}" 

    def calculate_threat_score(self):
        return 500000 + int(1000 / max(1, self.distance_km)) 

class ICBM(AirContact):
    def __init__(self, track_number):
        super().__init__(track_number, random.randint(3000, 5000))
        self.speed_mach = random.uniform(15.0, 25.0); self.altitude_ft = random.randint(300000, 1000000)
        self.rcs = random.uniform(0.1, 0.5); self.is_friendly = False; self.has_transponder = False
        
        self.true_type = random.choice([
            "RS-28 Sarmat", "Topol-M", "RS-24 Yars", "Bulava SLBM",
            "Minuteman III", "Trident II D5", "LGM-35 Sentinel",
            "DF-41", "DF-31AG", 
            "Hwasong-17", "Hwasong-18",
            "Agni-V"
        ])
        self.scenario = "NUCLEAR_STRIKE"

    def identify_target(self):
        self.type_name = self.true_type; self.status = "HOSTILE"; self.id_code = f"ICBM-{self.track_number}"

    def calculate_threat_score(self):
        return 1000000 + int(1000 / max(1, self.distance_km))

class Airliner(AirContact):
    def __init__(self, track_number):
        super().__init__(track_number, random.randint(300, 800))
        self.speed_mach = random.uniform(0.7, 0.85)
        self.altitude_ft = random.randint(30000, 42000)
        self.rcs = random.uniform(50.0, 200.0)
        self.is_friendly = True
        self.has_transponder = True if random.random() < 0.90 else False
        
        self.true_type = "COMMERCIAL_FLIGHT"
        self.scenario = "AIRLINER"
        
        # Airliners fly across the screen, not directly at the base
        self.heading = (self.bearing + random.choice([70, 90, 110, 250, 270, 290])) % 360
        
    def identify_target(self):
        self.type_name = "THAI B777" if self.rcs > 100 else "AIRASIA A320"
        self.status = "FRIENDLY"
        self.id_code = f"FLIGHT-{self.track_number}"
        self.callsign = f"TG{random.randint(100, 999)}" if self.rcs > 100 else f"FD{random.randint(100, 999)}"
        self.departure = random.choice(["VTBS", "VTBD", "VTSP", "VTCC", "VTSG"])
        self.destination = random.choice(["WMKK", "VYYY", "VLVT", "VVDN", "WSSS"])

    def move(self):
        # Cartesian movement so it flies across instead of towards center
        speed_per_tick = self.speed_mach * 1.0
        x = self.distance_km * math.sin(math.radians(self.bearing))
        y = -self.distance_km * math.cos(math.radians(self.bearing))
        
        x += speed_per_tick * math.sin(math.radians(self.heading))
        y -= speed_per_tick * math.cos(math.radians(self.heading))
        
        self.distance_km = math.sqrt(x*x + y*y)
        self.bearing = (math.degrees(math.atan2(x, -y)) + 360) % 360
        
        if self.distance_km > 1000:
            self.active = False
            
    def calculate_threat_score(self):
        return 0

class AWACS(AirContact):
    def __init__(self, track_number):
        super().__init__(track_number, 0) # Start at base (distance 0)
        self.speed_mach = 0.6
        self.altitude_ft = 35000
        self.rcs = 60.0
        self.is_friendly = True
        self.has_transponder = True
        self.true_type = "Saab 340 AEW&C"
        self.scenario = "AWACS"
        self.active = True
        
        self.fuel = 100.0
        self.state = "TRANSIT_TO_STATION"
        
        # Surat Thani Wing 7 roughly
        self.home_x = -50
        self.home_y = -400
        
        # Patrol over Gulf of Thailand
        self.orbit_center_x = 100
        self.orbit_center_y = -150
        self.orbit_angle = 0
        
        # Start AWACS at Home Base
        self.x_km = self.home_x
        self.y_km = self.home_y
        self.distance_km = math.hypot(self.x_km, self.y_km)
        self.bearing = (math.degrees(math.atan2(self.x_km, -self.y_km)) + 360) % 360
        
    def identify_target(self):
        self.type_name = self.true_type
        self.status = "FRIENDLY"
        self.id_code = f"ERIE-{self.track_number}"
        
    def calculate_threat_score(self):
        return 0
        
    def set_xy(self, x, y):
        self.x_km = x
        self.y_km = y
        self.distance_km = math.hypot(x, y)
        self.bearing = (math.degrees(math.atan2(x, -y)) + 360) % 360

    def move(self):
        speed_per_tick = self.speed_mach * 1.0
        x, y = self.x_km, self.y_km
        
        if self.state == "TRANSIT_TO_STATION":
            dist = math.hypot(self.orbit_center_x - x, self.orbit_center_y - y)
            if dist < speed_per_tick:
                self.state = "ON_STATION"
            else:
                angle = math.atan2(self.orbit_center_y - y, self.orbit_center_x - x)
                x += speed_per_tick * math.cos(angle)
                y += speed_per_tick * math.sin(angle)
                # Compute heading from movement vector
                self.heading = (math.degrees(math.atan2(speed_per_tick * math.cos(angle), -(speed_per_tick * math.sin(angle)))) + 360) % 360

        elif self.state == "ON_STATION":
            self.orbit_angle = (self.orbit_angle + 1) % 360
            orbit_radius_km = 50
            x = self.orbit_center_x + orbit_radius_km * math.cos(math.radians(self.orbit_angle))
            y = self.orbit_center_y + orbit_radius_km * math.sin(math.radians(self.orbit_angle))
            self.fuel -= 0.005 # Deplete fuel slowly (approx 5.5 mins patrol time)
            self.heading = (math.degrees(math.atan2(x - self.x_km, -(y - self.y_km))) + 360) % 360

        elif self.state == "RTB":
            dist = math.hypot(self.home_x - x, self.home_y - y)
            if dist < speed_per_tick:
                self.active = False # Landed
            else:
                angle = math.atan2(self.home_y - y, self.home_x - x)
                x += speed_per_tick * math.cos(angle)
                y += speed_per_tick * math.sin(angle)
                self.heading = (math.degrees(math.atan2(speed_per_tick * math.cos(angle), -(speed_per_tick * math.sin(angle)))) + 360) % 360
                
        self.set_xy(x, y)

class GhostTrack(AirContact):
    def __init__(self, track_number):
        super().__init__(track_number, random.randint(30, 150))
        self.speed_mach = random.uniform(0.02, 0.15) # Birds or slow moving clutter
        self.altitude_ft = random.randint(100, 5000)
        self.rcs = random.uniform(0.001, 0.1) # Very small cross section
        self.is_friendly = False
        self.has_transponder = False
        
        self.true_type = "BIRD_FLOCK/WEATHER"
        self.scenario = "CLUTTER"
        self.lifespan = random.randint(6, 18) # Will naturally vanish after a few seconds
        
    def identify_target(self):
        self.type_name = "CLUTTER"
        self.status = "CLEARED" # Radar operator realizes it's a ghost and clears it
        self.active = False
        self.id_code = f"GHOST-{self.track_number}"

    def move(self):
        super().move()
        self.lifespan -= 1
        if self.lifespan <= 0:
            self.active = False # Ghost vanishes from scope
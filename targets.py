# targets.py
import random
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
        self.heading = random.randint(0, 359)
        self.rcs = 0.0
        self.size = "UNKNOWN"
        self.type_name = "UNKNOWN"
        self.is_friendly = False
        
        self.has_transponder = False
        self.detected_by = "UNKNOWN"
        
        # 🟢 เพิ่มคุณสมบัติจอมกวนสัญญาณระดับหนัก
        self.is_heavy_ew = False

    @abstractmethod
    def identify_target(self): pass

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
                "Boeing 737", "Boeing 777", "Airbus A320", "Airbus A380", "Cessna 172", 
                "F-16 VIP Escort", "C-130 Hercules"
            ])
            self.scenario = "COMMERCIAL"
        else:
            combat_aircraft = [
                "F-22 Raptor", "F-35 Lightning II", "Su-57 Felon", "J-20 Mighty Dragon", "FC-31 Gyrfalcon",
                "Su-35 Flanker-E", "Su-27 Flanker", "MiG-31 Foxhound", "MiG-35 Fulcrum", 
                "F-15E Strike Eagle", "Eurofighter Typhoon", "Dassault Rafale", "J-10 Vigorous Dragon",
                "B-2 Spirit", "B-1B Lancer", "B-52 Stratofortress", "Tu-160 Blackjack", "Tu-95 Bear", "H-6K Badger"
            ]
            
            ew_aircraft = [
                "EC-130H Compass Call EW", "RC-135 Rivet Joint EW", 
                "Su-34 Fullback EW", "Il-22PP Porubschik EW", "Tu-214R EW",
                "J-16D Roaring Dragon EW", "Y-8 High New EW", "Y-9G EW",
                "E-3 Sentry AWACS", "A-50 Mainstay AWACS", "KJ-500 AWACS"
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
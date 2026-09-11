from datetime import datetime
import time
import random
import os
from config import GameConfig
from targets import (ICBM, TacticalBM, Drone, Helicopter, Aircraft,
                     GhostTrack, EWGhostTrack, Airliner, AWACS, CAPFighter,
                     AntiRadiationMissile, CruiseMissile, VIPTransport)
from personnel import ThreatQueue, RadarOperator, WeaponOfficer, Engagement, get_closest_airbase, get_wing_aircraft
from missions import MissionManager
from profiles import DEFAULT_PROFILE
import math

class CommandCenter:
    RTAF_RANKS = [
        "Airman",
        "Leading Airman",
        "Corporal",
        "Sergeant",
        "Flight Lieutenant",
        "Squadron Leader",
        "Wing Commander",
        "Group Captain",
        "Air Commodore",
        "Air Marshal",
        "Air Chief Marshal"
    ]
    XP_THRESHOLDS = [0, 500, 1200, 2200, 3500, 5200, 7500, 10500, 14500, 20000, 28000]

    def __init__(self, profile=None):
        # SimulationProfile: read-only spawn/behavior knobs (Spectator vs Player).
        # NEVER mutate GameConfig from this -- it is only ever resolved/read.
        self.profile = profile if profile is not None else DEFAULT_PROFILE
        profile_cfg = self.profile.resolve_config()

        # Scale factors derived from the profile relative to GameConfig defaults,
        # applied to the (mostly hardcoded) wave/spawn formulas below so a
        # Spectator profile visibly spawns more contacts than a Player profile,
        # without ever writing back into GameConfig itself.
        self._wave_chance_scale = profile_cfg["WAVE_CHANCE"] / GameConfig.WAVE_CHANCE
        self._wave_size_scale = profile_cfg["WAVE_SIZE_MAX"] / GameConfig.WAVE_SIZE_MAX
        self._wave_size_min = profile_cfg["WAVE_SIZE_MIN"]
        self._wave_cooldown_after_scale = profile_cfg["WAVE_COOLDOWN_AFTER"] / GameConfig.WAVE_COOLDOWN_AFTER

        self.contacts = []
        self.unseen_contacts = []
        self.active_engagements = []
        self.returning_fighters = []
        self.base_hp = 100
        self.tick_count = 0
        self.track_counter = 100
        self.threat_queue = ThreatQueue()
        self.wave_cooldown = profile_cfg["WAVE_COOLDOWN_INITIAL"]
        
        self.max_ammo = GameConfig.MAX_AMMO.copy()
        self.ammo = self.max_ammo.copy()
        self.reload_timers = {"THAAD": 0, "SAM": 0, "CIWS": 0} 
        self.awacs_pool = 2
        self.cap_pool = 6
        # tick stamps per threat type, for the rolling per-hour ceiling
        self._threat_log = {}
        self._cap_station_idx = 0
        
        # --- Logistics 60s System ---
        self.idle_timers = {wpn: 0 for wpn in self.max_ammo}
        self.prev_ammo = self.max_ammo.copy()
        
        self.radar_op = RadarOperator("Alpha")
        self.weapon_op = WeaponOfficer("Bravo")
        self.tactical_log = []

        # --- EMCON (Emission Control) System ---
        self.emcon_mode = "ACTIVE" # Options: "ACTIVE", "SECTOR", "SILENT"

        # --- Salvo Firing Doctrine ---
        self.salvo_mode = "SINGLE" # Options: "SINGLE", "RIPPLE", "SALVO"

        # --- Active RF Decoys ---
        self.decoys_remaining = 3
        self.active_decoys = []

        # --- Electronic Counter-Countermeasures (ECCM) ---
        self.burn_through_active = False
        self.burn_through_timer = 0
        self.hoj_mode = False

        # --- Event Bus ---
        self.event_bus = []
        self.historical_events = []

        # --- RTAF Career Rank & XP Progression ---
        self.xp = 0
        self.kills = 0
        self.airliners_safe = 0
        self.rank_index = 0
        self.is_court_martialed = False
        self.kills_by_type = {}
        self.kills_by_weapon = {}
        self.prev_defcon = 5
        self.mission_mgr = MissionManager()
        self.radar_max_km = 800.0
        self.max_base_hp = 100
        self.ciws_engage_range = 5.0
        self.unlocked_upgrades = set()
        self.UPGRADE_TIER_1_KEYS = ["AESA_RANGE", "DOPPLER_FILTER", "DECOY_PACK", "RAPID_CIWS", "AESA_SEEKERS"]
        self.UPGRADE_CATALOG = {
            "AESA_RANGE": {
                "name": "AESA Radar Overclock",
                "cost": 1200,
                "desc": "+25% Max Radar Range (800km -> 1000km)",
                "key": "1",
                "tier": 1
            },
            "DOPPLER_FILTER": {
                "name": "Doppler Clutter Filter",
                "cost": 800,
                "desc": "Auto-clears weather & bird clutter",
                "key": "2",
                "tier": 1
            },
            "DECOY_PACK": {
                "name": "RF Decoy Resupply Pack",
                "cost": 1000,
                "desc": "+3 Active RF Decoys",
                "key": "3",
                "tier": 1
            },
            "RAPID_CIWS": {
                "name": "Phalanx Rapid Feed System",
                "cost": 1500,
                "desc": "+100 CIWS 20mm Ammo & Instant Reload",
                "key": "4",
                "tier": 1
            },
            "AESA_SEEKERS": {
                "name": "AESA Active Missile Seekers",
                "cost": 2500,
                "desc": "+15% Base P_k for SAMs & THAAD",
                "key": "5",
                "tier": 1
            }
        }
        self.UPGRADE_TIER_2 = {
            "QUANTUM_SPACE_RADAR": {
                "name": "Space-Based Quantum Radar",
                "cost": 3500,
                "desc": "Orbital recon: paints all stealth & bypasses terrain masking",
                "key": "6",
                "tier": 2
            },
            "METEOR_HYPERSONIC": {
                "name": "Meteor Ramjet BVR Scramble",
                "cost": 4000,
                "desc": "+10 Max Fighter Ammo, Instant Restock & Mach 4.5 Intercept",
                "key": "7",
                "tier": 2
            },
            "IRON_BEAM_DIRECTED_ENERGY": {
                "name": "Helios 100kW Directed Energy Laser",
                "cost": 5000,
                "desc": "CIWS laser point-defense: 30km range & lightspeed intercept",
                "key": "8",
                "tier": 2
            },
            "TACTICAL_EMP_BURST": {
                "name": "High-Power EMP Shockwave Generator",
                "cost": 4500,
                "desc": "Emergency EMP: Wipes EW ghost tracks & fries ARM missile seekers",
                "key": "9",
                "tier": 2
            },
            "NANOTECH_AEGIS_SHIELD": {
                "name": "Nanotech Force Field & Hull Regeneration",
                "cost": 6000,
                "desc": "Fortifies Base HP to 150 Max & 50% damage reduction",
                "key": "0",
                "tier": 2
            }
        }
        self.UPGRADE_CATALOG.update(self.UPGRADE_TIER_2)

    @property
    def is_tier_1_complete(self):
        return all(k in self.unlocked_upgrades for k in self.UPGRADE_TIER_1_KEYS)

    @property
    def rank(self):
        if self.is_court_martialed:
            return "COURT-MARTIALED"
        return self.RTAF_RANKS[self.rank_index]

    def emit_event(self, event_type, **kwargs):
        evt = {
            "type": event_type,
            "tick": self.tick_count,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            **kwargs
        }
        self.event_bus.append(evt)
        self.historical_events.append(evt)
        if len(self.historical_events) > 3000:
            self.historical_events = self.historical_events[-1500:]
        return evt

    def award_xp(self, amount, reason=""):
        if self.is_court_martialed:
            return
        self.xp += amount
        current_idx = self.rank_index
        while current_idx + 1 < len(self.RTAF_RANKS) and self.xp >= self.XP_THRESHOLDS[current_idx + 1]:
            current_idx += 1
        if current_idx > self.rank_index:
            old_rank = self.RTAF_RANKS[self.rank_index]
            self.rank_index = current_idx
            new_rank = self.RTAF_RANKS[self.rank_index]
            self.add_log(f"\033[42;97m[PROMOTION] CONGRATULATIONS! Promoted to {new_rank.upper()}! (XP: {self.xp})\033[0m")
            self.emit_event("PROMOTION", old_rank=old_rank, new_rank=new_rank, xp=self.xp)

    def record_kill(self, contact, weapon):
        if getattr(contact, 'is_friendly', False) or isinstance(contact, Airliner):
            self.is_court_martialed = True
            self.base_hp = 0
            self.add_log(f"\033[41;97m[CRITICAL INCIDENT] YOU SHOT DOWN A FRIENDLY / CIVILIAN CRAFT! COURT-MARTIAL IMMINENT!\033[0m")
            self.emit_event("COURT_MARTIAL", target_id=contact.id_code, target_type=getattr(contact, 'type_name', 'Civilian'), weapon=weapon)
            return
        
        self.kills += 1
        t_name = type(contact).__name__
        self.kills_by_type[t_name] = self.kills_by_type.get(t_name, 0) + 1
        self.kills_by_weapon[weapon] = self.kills_by_weapon.get(weapon, 0) + 1
        
        # Intercept awards XP (higher for long-range >400 km kills and ICBMs)
        xp = 150
        if isinstance(contact, ICBM):
            xp = 1000
        elif isinstance(contact, TacticalBM):
            xp = 400
        elif isinstance(contact, AntiRadiationMissile):
            xp = 250
        elif isinstance(contact, CruiseMissile):
            xp = 200
        elif isinstance(contact, (Drone, Helicopter)):
            xp = 100

        dist = getattr(contact, 'distance_km', 0)
        if dist > 400:
            xp += 300
            self.add_log(f"\033[96m[AWARD] LONG-RANGE INTERCEPT (>400km): +300 XP BONUS!\033[0m")
            
        self.award_xp(xp, f"Splashed {contact.id_code}")

    def toggle_emcon(self):
        modes = ["ACTIVE", "SECTOR", "SILENT"]
        idx = modes.index(self.emcon_mode) if self.emcon_mode in modes else 0
        self.emcon_mode = modes[(idx + 1) % len(modes)]
        if self.emcon_mode == "ACTIVE":
            msg = "\033[92;1m[EMCON] RADAR TRANSMISSION: ACTIVE. Full 360° emitter active.\033[0m"
        elif self.emcon_mode == "SECTOR":
            msg = "\033[93;1m[EMCON] RADAR TRANSMISSION: SECTOR. Directional emission restricted to 120° forward arc.\033[0m"
        else:
            msg = "\033[41;97m[EMCON] RADAR TRANSMISSION: SILENT. Ground radar dark! Relying on AWACS/CAP sensors.\033[0m"
        self.add_log(msg)
        self.emit_event("EMCON_CHANGE", mode=self.emcon_mode)
        return self.emcon_mode

    def toggle_salvo(self):
        modes = ["SINGLE", "RIPPLE", "SALVO"]
        idx = modes.index(self.salvo_mode) if self.salvo_mode in modes else 0
        self.salvo_mode = modes[(idx + 1) % len(modes)]
        if self.salvo_mode == "SINGLE":
            msg = "\033[96m[DOCTRINE] Salvo doctrine set to SINGLE (1 missile per engagement).\033[0m"
        elif self.salvo_mode == "RIPPLE":
            msg = "\033[93m[DOCTRINE] Salvo doctrine set to RIPPLE (2 missiles, higher P_k).\033[0m"
        else:
            msg = "\033[91;1m[DOCTRINE] Salvo doctrine set to SALVO (3 missiles, maximum P_k against hypersonics).\033[0m"
        self.add_log(msg)
        self.emit_event("SALVO_CHANGE", mode=self.salvo_mode)
        return self.salvo_mode

    def deploy_decoy(self):
        if self.decoys_remaining <= 0:
            self.add_log("\033[91m[COUNTERMEASURES] NO ACTIVE RF DECOYS REMAINING!\033[0m")
            return False
        
        self.decoys_remaining -= 1
        arms = [c for c in self.contacts if c.active and isinstance(c, AntiRadiationMissile)]
        if arms:
            closest_arm = min(arms, key=lambda a: a.distance_km)
            bearing_rad = math.radians(closest_arm.bearing)
            dx = 15.0 * math.sin(bearing_rad)
            dy = 15.0 * math.cos(bearing_rad)
        else:
            angle = random.uniform(0, 2 * math.pi)
            dx = 15.0 * math.cos(angle)
            dy = 15.0 * math.sin(angle)
            
        decoy = {
            "id": f"RF-DECOY-{3 - self.decoys_remaining}",
            "x": dx,
            "y": dy,
            "timer": 20,
            "duration": 20,
            "active": True
        }
        self.active_decoys.append(decoy)
        self.add_log(f"\033[93;1m[COUNTERMEASURES] ACTIVE RF DECOY DEPLOYED! Blooming at 15km ({dx:.1f}, {dy:.1f}). ARM missiles drawn for 20s. ({self.decoys_remaining} remaining)\033[0m")
        self.emit_event("DECOY_DEPLOYED", decoy_id=decoy["id"], x=dx, y=dy, remaining=self.decoys_remaining)
        return True

    def is_in_sensor_coverage(self, target):
        """Checks if a contact is within airborne sensor coverage (AWACS or CAP)."""
        for aw in self.contacts:
            if isinstance(aw, AWACS) and aw.active:
                if math.hypot(target.x_km - aw.x_km, target.y_km - aw.y_km) <= 400.0:
                    return True
        for cap in self.contacts:
            if isinstance(cap, CAPFighter) and cap.active:
                if math.hypot(target.x_km - cap.x_km, target.y_km - cap.y_km) <= 100.0:
                    return True
        return False

    def retask_awacs(self, target_x: float, target_y: float) -> bool:
        for c in self.contacts:
            if isinstance(c, AWACS) and c.active:
                ok = c.retask_station(target_x, target_y)
                if ok:
                    self.add_log(f"\033[96;1m[AWACS-C2] {c.id_code} RETASKED TO PATROL STATION ({target_x:.1f}, {target_y:.1f}) km\033[0m")
                    return True
        return False

    def order_awacs_rtb(self) -> bool:
        for c in self.contacts:
            if isinstance(c, AWACS) and c.active:
                ok = c.order_rtb()
                if ok:
                    self.add_log(f"\033[93m[AWACS-C2] {c.id_code} ORDERED IMMEDIATE RTB TO WING 7\033[0m")
                    return True
        return False

    def is_contact_visible(self, c):
        """Returns True if contact is detectable/visible under current EMCON mode."""
        if not c.active:
            return False
        if "QUANTUM_SPACE_RADAR" in self.unlocked_upgrades:
            return True
        if isinstance(c, (AWACS, CAPFighter)):
            return True
        if getattr(c, 'detected_by', '') == 'SPACE-COM':
            return True
        if self.is_in_sensor_coverage(c):
            return True
        if self.emcon_mode == "SILENT":
            return False
        if self.emcon_mode == "SECTOR":
            # 120-degree forward sector (North/East threat axis, bearing 300 to 60)
            return (c.bearing <= 60 or c.bearing >= 300)
        return True

    def unlock_upgrade(self, upgrade_id):
        if upgrade_id in self.unlocked_upgrades:
            return False, "Already Unlocked"
        if upgrade_id in self.UPGRADE_TIER_2 and not self.is_tier_1_complete:
            return False, "Locked: Complete Tier 1 First"
        if upgrade_id not in self.UPGRADE_CATALOG:
            return False, "Unknown Upgrade"
        info = self.UPGRADE_CATALOG[upgrade_id]
        if self.xp < info["cost"]:
            return False, f"Insufficient XP (Need {info['cost']} XP)"
        
        self.xp -= info["cost"]
        self.unlocked_upgrades.add(upgrade_id)
        
        # Apply upgrade effect
        if upgrade_id == "AESA_RANGE":
            self.radar_max_km = 1000.0
        elif upgrade_id == "DECOY_PACK":
            self.decoys_remaining += 3
        elif upgrade_id == "RAPID_CIWS":
            self.max_ammo["CIWS"] += 100
            self.ammo["CIWS"] += 100
            self.reload_timers["CIWS"] = 0
        elif upgrade_id == "QUANTUM_SPACE_RADAR":
            self.add_log("\033[96;1m[SPACE-COM] QUANTUM SATELLITE CONSTELLATION ONLINE. TERRAIN MASKING BYPASSED.\033[0m")
        elif upgrade_id == "METEOR_HYPERSONIC":
            self.max_ammo["FIGHTER"] += 10
            self.ammo["FIGHTER"] = self.max_ammo["FIGHTER"]
            self.reload_timers["FIGHTER"] = 0
            self.add_log("\033[92;1m[RTAF] SQUADRONS EQUIPPED WITH METEOR BVR RAMJET MISSILES!\033[0m")
        elif upgrade_id == "IRON_BEAM_DIRECTED_ENERGY":
            self.ciws_engage_range = 30.0
            self.add_log("\033[93;1m[HELIOS] 100kW DIRECTED ENERGY LASER POINT DEFENSE ARMED (30km RANGE)!\033[0m")
        elif upgrade_id == "TACTICAL_EMP_BURST":
            self.add_log("\033[95;1m[SYS] HIGH-POWER MICROWAVE / EMP SHOCKWAVE GENERATOR READY! PRESS [B] TO DISCHARGE.\033[0m")
        elif upgrade_id == "NANOTECH_AEGIS_SHIELD":
            self.max_base_hp = 150
            self.base_hp = 150
            self.add_log("\033[94;1m[AEGIS] NANOTECH DEFENSE MATRIX ONLINE. BASE HP FORTIFIED TO 150!\033[0m")
            
        self.add_log(f"\033[92m[TECH UPGRADE] UNLOCKED: {info['name']} (-{info['cost']} XP)\033[0m")
        self.emit_event("UPGRADE_UNLOCKED", upgrade_id=upgrade_id, name=info["name"], tier=info.get("tier", 1))
        
        if self.is_tier_1_complete and len(self.unlocked_upgrades & set(self.UPGRADE_TIER_1_KEYS)) == 5:
            self.emit_event("TIER_2_UNLOCKED")
            self.add_log("\033[95;1m[CLASSIFIED] ALL TIER 1 UPGRADES MASTERED! TIER 2 BLACK OPS LAB UNLOCKED!\033[0m")
            
        return True, "Success"

    def trigger_emp_burst(self):
        if "TACTICAL_EMP_BURST" not in self.unlocked_upgrades:
            return False, "EMP Generator Not Unlocked"
            
        # 1. Disable ARM seeker locks
        for c in self.contacts:
            if isinstance(c, AntiRadiationMissile) or getattr(c, 'scenario', '') == 'SEAD' or hasattr(c, 'seeker_locked'):
                c.seeker_locked = False

        # 2. Clear all EW ghost tracks and clutter
        for c in list(self.contacts):
            if isinstance(c, (GhostTrack, EWGhostTrack)) or getattr(c, 'is_ghost', False) or getattr(c, 'true_type', '') in ['BIRD_FLOCK/WEATHER', 'ELECTRONIC_DECEPTION']:
                c.active = False
        self.contacts = [c for c in self.contacts if c.active]
                    
        self.emit_event("EMP_BURST_TRIGGERED")
        self.add_log("\033[95;1m[EMP] TACTICAL EMP SHOCKWAVE DISCHARGED! EW JAMMING & ARM SEEKERS NEUTRALIZED!\033[0m")
        return True, "EMP shockwave discharged."

    def toggle_burn_through(self):
        self.burn_through_active = not self.burn_through_active
        if self.burn_through_active:
            self.burn_through_timer = 20  # 20 seconds duration
            self.emit_event("ECCM_BURN_THROUGH", active=True)
            self.add_log("\033[96;1m[ECCM] TRANSMITTER OVERDRIVE ACTIVE: AESA burn-through penetrating jamming sectors!\033[0m")
            return True, "Burn-Through Overdrive Online"
        else:
            self.burn_through_timer = 0
            self.emit_event("ECCM_BURN_THROUGH", active=False)
            self.add_log("\033[90m[ECCM] Radar burn-through returned to normal scan power.\033[0m")
            return False, "Burn-Through Standby"

    def get_jamming_factor(self, target, ew_aircrafts):
        """Calculates radar detection range multiplier taking into account EW jamming and ECCM burn-through."""
        is_jammed = False
        for ew in ew_aircrafts:
            if ew != target:
                angle_diff = abs((target.bearing - ew.bearing + 180) % 360 - 180)
                if angle_diff <= 10.0:
                    is_jammed = True
                    break
        if not is_jammed:
            return 1.0
        if self.burn_through_active:
            return 1.5  # 150% burn-through range
        return 0.3  # Standard 30% range in jamming sector

    def toggle_hoj_mode(self):
        self.hoj_mode = not self.hoj_mode
        status_str = "ENABLED" if self.hoj_mode else "STANDBY"
        color_code = "\033[93;1m" if self.hoj_mode else "\033[90m"
        self.emit_event("HOJ_MODE_CHANGE", enabled=self.hoj_mode)
        self.add_log(f"{color_code}[HOJ DOCTRINE] HOME-ON-JAM PASSIVE SEEKER GUIDANCE {status_str}!\033[0m")
        return self.hoj_mode, f"HOJ Guidance {status_str}"

    def can_engage_with_sam(self, target):
        """Checks if SAM battery can engage target under current parameters, including HOJ mode."""
        if not target or not target.active:
            return False
        max_range = 200.0
        is_radiating_ew = getattr(target, 'is_heavy_ew', False) or "EW" in getattr(target, 'type_name', '') or getattr(target, 'scenario', '') == 'EW'
        if self.hoj_mode and is_radiating_ew:
            max_range = 350.0  # Extended HOJ range riding jamming emissions
        return target.distance_km <= max_range

    def process_esm_triangulation(self):
        """
        Passive ESM Cross-Bearing Triangulation:
        When Saab 340 AEW&C is airborne, cross-fixes bearing from Bangkok HQ with
        bearing from the AWACS, calculating exact (x, y) coordinates of standoff jammers.
        """
        active_awacs = [c for c in self.contacts if isinstance(c, AWACS) and c.active]
        if not active_awacs:
            for c in self.contacts:
                if hasattr(c, 'is_esm_triangulated'):
                    c.is_esm_triangulated = False
            return

        awacs = active_awacs[0]
        for c in self.contacts:
            if not c.active:
                continue
            is_ew = getattr(c, 'is_heavy_ew', False) or "EW" in getattr(c, 'type_name', '') or getattr(c, 'scenario', '') == 'EW'
            if is_ew and c.status != "FRIENDLY":
                c.is_esm_triangulated = True
                c.esm_fix_coord = (c.x_km, c.y_km)
                c.detected_by = "ESM-TRIANGULATED"

    def add_log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.tactical_log.append(f"[{ts}] {msg}")
        if len(self.tactical_log) > 24: self.tactical_log.pop(0)

    def calculate_defcon(self):
        current_defcon = 5 
        for c in self.contacts:
            if not c.active: continue
            if isinstance(c, ICBM) and c.status in ["HOSTILE", "ENGAGING"]:
                current_defcon = 1
                break
            if c.status in ["HOSTILE", "ENGAGING", "SUSPECT", "INTERCEPTING"]:
                if c.distance_km < 80: current_defcon = min(current_defcon, 2) 
                else: current_defcon = min(current_defcon, 3) 
            elif c.status in ["UNIDENTIFIED", "IDENTIFYING"]: current_defcon = min(current_defcon, 4) 
        
        if current_defcon != getattr(self, 'prev_defcon', 5):
            self.emit_event("DEFCON_CHANGE", from_defcon=self.prev_defcon, to_defcon=current_defcon, defcon=current_defcon)
            self.prev_defcon = current_defcon
        return current_defcon

    def detect_airspace(self):
        if self.wave_cooldown > 0: self.wave_cooldown -= 1
        
        # Advance mission scenario logic
        if hasattr(self, 'mission_mgr') and self.mission_mgr:
            self.mission_mgr.current.tick(self)
            
        # Doppler Clutter Filter upgrade: auto-clean ghost clutter
        if "DOPPLER_FILTER" in self.unlocked_upgrades:
            for c in self.contacts:
                if isinstance(c, (GhostTrack, EWGhostTrack)):
                    c.active = False
            self.contacts = [c for c in self.contacts if not isinstance(c, (GhostTrack, EWGhostTrack))]
        
        # Quantum Space Radar upgrade: bypass terrain masking & detect unseen contacts immediately
        if "QUANTUM_SPACE_RADAR" in self.unlocked_upgrades:
            for c in list(self.unseen_contacts):
                if c.active:
                    c.is_masked = False
                    c.detected_by = "QUANTUM-SPACE"
                    c.brightness = 1.0
                    self.contacts.append(c)
            self.unseen_contacts = [c for c in self.unseen_contacts if c not in self.contacts]
        
        # --- escalation phases ---
        tick = self.tick_count
        
        # Rates come from GameConfig.THREAT_PHASES so the threat model is
        # tunable in one place instead of buried in this function.
        if tick < 120:
            phase = "PEACETIME"
            cfg = GameConfig.THREAT_PHASES["PEACETIME"]
            hostile_chance = cfg["hostile_per_tick"]
            civilian_chance = cfg["civilian_per_tick"]
            civilian_ratio = cfg["civilian_ratio"]
            wave_enabled = False
        elif tick < 360:
            phase = "TENSIONS"
            cfg = GameConfig.THREAT_PHASES["TENSIONS"]
            progress = (tick - 120) / 240.0  # 0.0 to 1.0 across this phase
            hostile_chance = cfg["hostile_per_tick"] + (
                cfg["hostile_per_tick_end"] - cfg["hostile_per_tick"]) * progress
            civilian_chance = cfg["civilian_per_tick"] + (
                cfg["civilian_per_tick_end"] - cfg["civilian_per_tick"]) * progress
            civilian_ratio = cfg["civilian_ratio"] + (
                cfg["civilian_ratio_end"] - cfg["civilian_ratio"]) * progress
            wave_enabled = progress > 0.5  # waves start halfway through tensions
        else:
            phase = "WARTIME"
            cfg = GameConfig.THREAT_PHASES["WARTIME"]
            escalation = min(2.0, 1.0 + (tick - 360) / 1500.0)
            hostile_chance = cfg["hostile_per_tick"] * escalation
            civilian_chance = cfg["civilian_per_tick"]
            civilian_ratio = cfg["civilian_ratio"]
            wave_enabled = True
        
        # log phase transitions
        if tick == 120:
            self.add_log("\033[93m[INTEL] Unidentified aircraft detected near border. Increasing alert posture.\033[0m")
        elif tick == 360:
            self.add_log("\033[41;97m[COMMAND] AIRSPACE CLOSED TO CIVILIAN TRAFFIC. ALL UNKNOWN CONTACTS ARE HOSTILE.\033[0m")
        
        # massive wave attacks (wartime / late tensions only)
        # Base trigger chance / cooldown / size are scaled by the active
        # SimulationProfile (Spectator sees bigger, more frequent waves;
        # Player sees smaller, less frequent ones) without touching GameConfig.
        base_wave_trigger_chance = 0.08 if phase == "TENSIONS" else 0.12 * min(3.0, 1.0 + (tick - 360) / 1500.0)
        if wave_enabled and self.wave_cooldown <= 0 and random.random() < base_wave_trigger_chance * self._wave_chance_scale:
            base_cooldown = max(80, 200 if phase == "TENSIONS" else int(200 / min(3.0, 1.0 + (tick - 360) / 1500.0)))
            self.wave_cooldown = max(1, int(base_cooldown * self._wave_cooldown_after_scale))
            base_wave_size = random.randint(5, 10) if phase == "TENSIONS" else int(random.randint(8, 15) * min(3.0, 1.0 + (tick - 360) / 1500.0))
            wave_size = max(self._wave_size_min, int(base_wave_size * self._wave_size_scale))
            
            wave_theme = random.choices(
                ["MIXED", "BALLISTIC_RAIN", "DRONE_SWARM", "FIGHTER_STRIKE", "SEAD_STRIKE", "CRUISE_VOLLEY"], 
                weights=[30, 15, 15, 15, 15, 10], k=1)[0]
                
            if wave_theme == "MIXED":
                self.add_log("\033[41;97m[TACTICAL WARNING] MULTIPLE HOSTILE CONTACTS INBOUND. BATTLE STATIONS.\033[0m")
            elif wave_theme == "BALLISTIC_RAIN":
                self.add_log("\033[41;97m[DEFCON 1] BALLISTIC MISSILE LAUNCH DETECTED. THAAD BATTERIES TO STANDBY.\033[0m")
            elif wave_theme == "DRONE_SWARM":
                self.add_log("\033[41;97m[WARNING] UNMANNED AERIAL SWARM DETECTED. ACTIVATE CIWS PROTOCOL.\033[0m")
            elif wave_theme == "FIGHTER_STRIKE":
                self.add_log("\033[41;97m[TACTICAL WARNING] HEAVY FIGHTER FORMATION INBOUND. SCRAMBLE ALL INTERCEPTORS.\033[0m")
            elif wave_theme == "SEAD_STRIKE":
                if self.emcon_mode == "SILENT":
                    self.add_log("\033[93m[INTEL] Enemy SEAD strike detected but radar is dark (EMCON SILENT). ARMs unable to lock!\033[0m")
                else:
                    self.add_log("\033[41;97m[TACTICAL WARNING] SEAD STRIKE INBOUND! ANTI-RADIATION MISSILES HOMING ON BASE RADAR!\033[0m")
            elif wave_theme == "CRUISE_VOLLEY":
                self.add_log("\033[41;97m[TACTICAL WARNING] TERRAIN-MASKED CRUISE MISSILE VOLLEY DETECTED!\033[0m")
            
            THEME_POOLS = {
                "BALLISTIC_RAIN": {"ICBM": 10, "TBM": 90},
                "DRONE_SWARM":    {"DRONE": 100},
                "FIGHTER_STRIKE": {"FIGHTER": 100},
                "SEAD_STRIKE":    {"ARM": 100, "CRUISE": 1},
                "CRUISE_VOLLEY":  {"CRUISE": 100},
            }
            pool = THEME_POOLS.get(wave_theme, dict(GameConfig.THREAT_WEIGHTS))
            for _ in range(wave_size):
                # Every wave unit passes the same hourly ceiling as a lone
                # spawn, so a ballistic rain thins itself out instead of
                # dumping a dozen launches on the scope.
                threat_type = self.pick_threat(pool)
                if threat_type is None:
                    break
                self.unseen_contacts.append(self.spawn_threat(threat_type))
        
        # civilian traffic (airliners passing through)
        if random.random() < civilian_chance:
            self.track_counter += 1
            new_contact = Airliner(self.track_counter)
            new_contact.detected_by = "GND-RADAR"
            self.unseen_contacts.append(new_contact)
        
        # hostile / unknown contacts
        # EMCON adjusts spawn rate: if SILENT, enemy strike packages cannot find radiating emitters (-25% spawn chance)
        # Also scaled by the active SimulationProfile's wave_chance knob (Spectator: more pressure, Player: less).
        effective_hostile_chance = hostile_chance * (0.75 if self.emcon_mode == "SILENT" else 1.0) * self._wave_chance_scale
        if random.random() < effective_hostile_chance:
            threat_type = self.pick_threat()
            if threat_type == "FIGHTER":
                # A fighter-shaped contact may still resolve as a civilian
                # straggler in the earlier phases; civilian_ratio decides.
                self.track_counter += 1
                new_contact = Aircraft(self.track_counter,
                                       friendly_weight=int(civilian_ratio * 100))
                new_contact.detected_by = random.choice(["GND-RADAR", "AWACS"])
                self.unseen_contacts.append(new_contact)
            elif threat_type is not None:
                self.unseen_contacts.append(self.spawn_threat(threat_type))
            
        # False Alarm (Clutter/Ghosts) system: only detected by active ground radar
        if self.emcon_mode != "SILENT" and random.random() < 0.05 * self._wave_chance_scale:
            self.track_counter += 1
            ghost = GhostTrack(self.track_counter)
            ghost.detected_by = "GND-RADAR"
            self.unseen_contacts.append(ghost)

        # Update contact visibility according to EMCON posture:
        # If SILENT, ground radar is blind (contacts only visible if within AWACS or CAP visual/radar range)
        for c in self.contacts:
            if not self.is_contact_visible(c):
                c.brightness = 0.0

        # EW Glitch Mechanics (Floods radar with false targets)
        # Ghost tracks go directly into contacts — they're injected radar returns, not real aircraft
        flood_chance, jam_power = self.get_ew_flood_chance()
        if flood_chance > 0.0 and random.random() < flood_chance:
            # Ghost volume scales with the jamming power actually being applied.
            count_lo = max(1, int(round(2 * jam_power)))
            count_hi = max(count_lo + 1, int(round(6 * jam_power)))
            for _ in range(random.randint(count_lo, count_hi)):
                self.track_counter += 1
                ghost = EWGhostTrack(self.track_counter)
                ghost.detected_by = "EW-INJECT"
                ghost.brightness = 1.0
                ghost.visible_dist = ghost.distance_km
                self.contacts.append(ghost)

    # --- Electronic attack (ghost flood) doctrine ---------------------------
    # Range at which a jammer achieves full burn-in against our radar, the
    # floor its power decays to at extreme standoff, and the per-tick flood
    # rate at unit jamming power.
    EW_FLOOD_REFERENCE_KM = 300.0
    EW_FLOOD_MIN_PROXIMITY = 0.6
    EW_FLOOD_BASE_RATE = 0.60

    def get_jammer_strength(self, c):
        """Relative electronic-attack power of a contact (0.0 = not a jammer).
        Injected ghosts are explicitly excluded so the flood can never feed on
        the false targets it just created."""
        if not getattr(c, 'active', False):
            return 0.0
        if isinstance(c, (GhostTrack, EWGhostTrack)):
            return 0.0
        # Our own AEW&C / CAP are not jamming us (and "AEW&C" would otherwise
        # match the "EW" capability substring below).
        if getattr(c, 'is_friendly', False) or getattr(c, 'status', '') == "FRIENDLY":
            return 0.0
        if getattr(c, 'is_heavy_ew', False):
            return 1.0
        if ("EW" in getattr(c, 'type_name', '') or "EW" in getattr(c, 'true_type', '')
                or getattr(c, 'scenario', '') == 'EW'):
            return 0.35
        return 0.0

    def get_ew_flood_chance(self):
        """EW GHOST FLOOD RULE: a jammer injects false targets into a radar
        that is actually radiating. If the ground radar is dark (EMCON SILENT)
        there is no emission to exploit and the flood cannot happen at all;
        SECTOR emission offers a narrower window. Otherwise the rate is derived
        from the jammers really out there -- their electronic-attack strength
        and their range -- and is suppressed while ECCM burn-through overdrive
        is punching through the jamming.

        Returns (per-tick flood chance, applied jamming power)."""
        if self.emcon_mode == "SILENT":
            return 0.0, 0.0

        jam_power = 0.0
        for c in self.contacts:
            strength = self.get_jammer_strength(c)
            if strength <= 0.0:
                continue
            proximity = min(1.0, self.EW_FLOOD_REFERENCE_KM / max(1.0, c.distance_km))
            jam_power += strength * max(self.EW_FLOOD_MIN_PROXIMITY, proximity)

        if jam_power <= 0.0:
            return 0.0, 0.0
        jam_power = min(2.0, jam_power)

        factor = 0.5 if self.emcon_mode == "SECTOR" else 1.0
        if self.burn_through_active:
            factor *= 0.35

        return min(0.85, self.EW_FLOOD_BASE_RATE * jam_power * factor), jam_power

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

        # Automated Combat Air Patrol (CAP) Swap System
        active_caps = [c for c in self.contacts if isinstance(c, CAPFighter)]
        
        # Recover landed CAPs
        for c in active_caps:
            if c.state == "RTB" and not c.active:
                self.cap_pool += 1
                self.add_log(f"\033[94m[AIRBASE] {c.id_code} landed safely and refueling.\033[0m")
                
        flying_caps = [c for c in active_caps if c.active]
        # Rotate CAP across the stations in GameConfig.CAP_STATIONS so every
        # listed wing flies, each launching from its own field with its own
        # aircraft, instead of two hardcoded wings.
        stations = GameConfig.CAP_STATIONS
        if stations and len(flying_caps) < GameConfig.CAP_CONCURRENT and self.cap_pool > 0:
            if self.tick_count % 5 == 0:  # Stagger launches by 5 seconds
                manned = {getattr(c, "wing", None) for c in flying_caps}
                choices = [st for st in stations if st[0] not in manned] or list(stations)
                station = choices[self._cap_station_idx % len(choices)]
                self._cap_station_idx += 1
                wing, orbit_x, orbit_y, station_name = station
                fighter = GameConfig.wing_fighter(wing)
                field = next((n for _x, _y, n in GameConfig.AIRBASES
                              if n.startswith("Wing %d (" % wing)), "Wing %d" % wing)
                self.track_counter += 1
                cap = CAPFighter(self.track_counter, wing, orbit_x, orbit_y,
                                 "%s (CAP)" % fighter)
                self.add_log("\033[94m[AIRBASE] %s launching %s for %s.\033[0m"
                             % (field, fighter, station_name))
                self.contacts.append(cap)
                self.cap_pool -= 1
                
        # Handle RTB for low fuel CAPs
        for cap in flying_caps:
            if cap.fuel < 20.0 and cap.state == "ON_STATION":
                cap.state = "RTB"
                self.add_log(f"\033[94m[AIRBASE] {cap.id_code} bingo fuel, RTB.\033[0m")

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

    # Radius (km) inside which a threat is considered "imminent/leaking" and
    # the backup auto-fire may take over for the human in Player mode.
    BACKUP_ENGAGEMENT_RADIUS_KM = 40

    def _is_backup_engagement(self, threat):
        """BACKUP AUTO-FIRE RULE (Player mode only, profile.autonomous_weapons
        == False): the WeaponOfficer's auto-target-acquisition is reduced to a
        last-resort backstop instead of full autonomy. It only engages when a
        threat is either (a) imminent/leaking -- inside a close last-ditch
        radius the player clearly hasn't dealt with -- or (b) an unengaged
        ballistic missile (ICBM/TacticalBM), since manual THAAD/SAM timing
        against ballistic threats is unforgiving and letting one slip through
        unchallenged is effectively a lost game. Everything else is left for
        the human to fire on manually via manual_override_fire()."""
        if threat.distance_km <= self.BACKUP_ENGAGEMENT_RADIUS_KM:
            return True
        return isinstance(threat, (ICBM, TacticalBM))

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

        wep_result = self.weapon_op.tick(self.ammo, salvo_mode=self.salvo_mode)
        if wep_result:
            if isinstance(wep_result, tuple):
                msg, engagement = wep_result
                self.add_log(msg)
                if engagement is not None:
                    self.active_engagements.append(engagement)
                    if getattr(engagement, 'target', None):
                        self.emit_event(
                            "MISSILE_LAUNCH",
                            weapon=engagement.weapon_name,
                            target_id=engagement.target.id_code,
                            target_x=getattr(engagement.target, 'x_km', 0.0),
                            target_y=getattr(engagement.target, 'y_km', 0.0),
                            salvo_mode=getattr(engagement, 'salvo_mode', self.salvo_mode),
                            salvo_count=getattr(engagement, 'salvo_count', 1)
                        )
            else: self.add_log(wep_result)

        if not self.weapon_op.is_busy:
            self.threat_queue.build_queue(self.contacts)
            # Walk the queue rather than popping once: in Player mode the highest
            # scoring threat is often a distant contact the human is handling, and
            # discarding the tick on it starves a close leaker that backup fire
            # exists to catch. Spectator (autonomous_weapons=True) still engages
            # the first pop, so its behaviour is unchanged.
            while True:
                highest_threat = self.threat_queue.pop_highest_priority()
                if not highest_threat:
                    break
                if self.profile.autonomous_weapons or self._is_backup_engagement(highest_threat):
                    self.add_log(self.weapon_op.authorize_engagement(highest_threat))
                    break

        # Proactive AI fighter defense against standoff EW jammers
        self.process_ew_interceptor_defense()

    def process_ew_interceptor_defense(self):
        """
        AI Interceptor Prioritization:
        Scrambles available RTAF interceptors against unengaged standoff EW jammers
        to prevent persistent electronic warfare jamming and radar blinding.
        """
        if self.ammo.get("FIGHTER", 0) <= 0:
            return False

        # Find active hostile/unidentified EW platforms
        all_engaged_targets = [eng.target for eng in self.active_engagements if getattr(eng, 'target', None) and eng.target.active]

        unengaged_jammers = []
        for c in self.contacts:
            if not c.active:
                continue
            is_ew = getattr(c, 'is_heavy_ew', False) or "EW" in getattr(c, 'type_name', '') or getattr(c, 'scenario', '') == 'EW'
            if is_ew and c.status in ["HOSTILE", "SUSPECT", "UNIDENTIFIED"]:
                if c not in all_engaged_targets and c.status not in ["CLEARED", "FRIENDLY"]:
                    unengaged_jammers.append(c)

        if not unengaged_jammers:
            return False

        # Prioritize heavy EW first, then closest
        unengaged_jammers.sort(key=lambda j: (0 if getattr(j, 'is_heavy_ew', False) else 1, j.distance_km))
        target_jam = unengaged_jammers[0]

        bx, by, bname = get_closest_airbase(target_jam)
        fighter_type = get_wing_aircraft(bname)
        self.ammo["FIGHTER"] -= 1

        dist_from_base = math.hypot(target_jam.x_km - bx, target_jam.y_km - by)
        closure_rate = max(1.0, target_jam.speed_mach + GameConfig.WEAPON_SPEED_F16)
        prep_time = getattr(GameConfig, 'PREP_TIME_F16', 15)
        impact_time = max(1, int(dist_from_base / closure_rate) + prep_time)

        eng = Engagement(target_jam, fighter_type, impact_time, bx, by)
        self.active_engagements.append(eng)
        target_jam.status = "INTERCEPTING"

        self.emit_event(
            "MISSILE_LAUNCH",
            weapon=fighter_type,
            target_id=target_jam.id_code,
            target_x=target_jam.x_km,
            target_y=target_jam.y_km,
            salvo_mode="SINGLE",
            salvo_count=1
        )
        self.add_log(f"\033[95;1m[AI-C2] EW SUPPRESSION SORTIE: {fighter_type} scrambled from {bname} targeting jammer {target_jam.id_code}!\033[0m")
        return True

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

        # Range Check for Surface-to-Air Missiles
        if wpn == "SAM" and not self.can_engage_with_sam(target):
            self.add_log(f"\033[91;1m[ERROR] SAM OUT OF RANGE ({target.distance_km:.1f}km > 200km)! HOJ guidance required.\033[0m")
            return
            
        salvo_count = 1
        if wpn in ["THAAD", "SAM"]:
            if self.salvo_mode == "RIPPLE":
                salvo_count = 2
            elif self.salvo_mode == "SALVO":
                salvo_count = 3

        missiles_to_fire = min(salvo_count, self.ammo.get(wpn, 0))
        if missiles_to_fire > 0:
            self.ammo[wpn] -= missiles_to_fire
            
            display_wpn = wpn
            bx, by = 0.0, 0.0
            if wpn == "FIGHTER":
                bx, by, bname = get_closest_airbase(target)
                display_wpn = get_wing_aircraft(bname)
                
            dist_from_origin = math.hypot(target.x_km - bx, target.y_km - by)
            if wpn == "THAAD":
                weapon_speed = GameConfig.WEAPON_SPEED_THAAD
            elif wpn == "FIGHTER":
                weapon_speed = GameConfig.WEAPON_SPEED_F16
            elif wpn == "CIWS":
                weapon_speed = getattr(GameConfig, 'WEAPON_SPEED_CIWS', 25.0)
            else:
                weapon_speed = GameConfig.WEAPON_SPEED_SAM
            impact_time = max(1, int(dist_from_origin / max(1.0, weapon_speed)))
            
            eng = Engagement(target, display_wpn, impact_time, bx, by, salvo_count=missiles_to_fire, salvo_mode=self.salvo_mode)
            self.active_engagements.append(eng)
            target.status = "ENGAGING"
            
            if wpn == "CIWS":
                self.emit_event(
                    "CIWS_FIRE",
                    target_id=target.id_code,
                    ammo_used=missiles_to_fire,
                    hit=True
                )
            else:
                self.emit_event(
                    "MISSILE_LAUNCH",
                    weapon=wpn,
                    target_id=target.id_code,
                    target_x=target.x_km,
                    target_y=target.y_km,
                    salvo_mode=self.salvo_mode,
                    salvo_count=missiles_to_fire
                )
            
            salvo_suffix = f" ({self.salvo_mode} x{missiles_to_fire})" if wpn in ["THAAD", "SAM"] else ""
            origin_str = f" from {bname}" if wpn == "FIGHTER" else ""
            self.add_log(f"\033[95m[MANUAL OVERRIDE]\033[0m SCRAMBLED {display_wpn}{salvo_suffix}{origin_str} intercepting {target.id_code}")
        else:
            self.add_log(f"\033[91m[WARNING]\033[0m {wpn} Out of Ammo!")

    def threat_allowed(self, kind):
        """Rolling one-hour ceiling per threat type.

        Returns True and records the spawn, or False when the type has already
        used its GameConfig.THREAT_MAX_PER_HOUR budget for the last hour of
        scope time. Wave spawns go through here too, which is what stops a
        ballistic rain putting five TBM launches on the scope inside an hour.
        """
        cap = GameConfig.THREAT_MAX_PER_HOUR.get(kind)
        if cap is None:
            return True
        cutoff = self.tick_count - GameConfig.THREAT_WINDOW_TICKS
        stamps = [t for t in self._threat_log.get(kind, []) if t > cutoff]
        if len(stamps) >= cap:
            self._threat_log[kind] = stamps
            return False
        stamps.append(self.tick_count)
        self._threat_log[kind] = stamps
        return True

    def pick_threat(self, weights=None):
        """Choose a threat type by rarity weight, respecting the hourly cap.

        Returns None when every candidate is capped out. The caller treats that
        as a quiet sky rather than substituting a different threat.
        """
        pool = dict(weights or GameConfig.THREAT_WEIGHTS)
        if self.emcon_mode == "SILENT":
            pool.pop("ARM", None)  # an ARM cannot home on a dark radar
        while pool:
            kinds = list(pool.keys())
            kind = random.choices(kinds, weights=[pool[k] for k in kinds], k=1)[0]
            if self.threat_allowed(kind):
                return kind
            pool.pop(kind)
        return None

    def spawn_threat(self, kind):
        """Build one contact of the named type with its detection source."""
        self.track_counter += 1
        if kind == "ICBM":
            c = ICBM(self.track_counter); c.detected_by = "SPACE-COM"
        elif kind == "TBM":
            c = TacticalBM(self.track_counter); c.detected_by = "GND-EWR"
        elif kind == "DRONE":
            c = Drone(self.track_counter); c.detected_by = "AWACS"
        elif kind == "HELI":
            c = Helicopter(self.track_counter); c.scenario = "HOSTILE_HELI"
            c.detected_by = "GND-RADAR"
        elif kind == "ARM":
            c = AntiRadiationMissile(self.track_counter); c.detected_by = "GND-RADAR"
        elif kind == "CRUISE":
            c = CruiseMissile(self.track_counter); c.detected_by = "GND-RADAR"
        else:
            c = Aircraft(self.track_counter, friendly_weight=0)
            c.scenario = "HOSTILE_FIGHTER"; c.detected_by = "GND-RADAR"
        return c

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
        elif target_type == "EW": c = Aircraft(self.track_counter); c.true_type = "EA-18G Growler (HEAVY EW)"; c.is_heavy_ew = True; c.is_friendly = False; c.has_transponder = False; c.detected_by = "GND-RADAR"
        elif target_type == "AWACS": c = AWACS(self.track_counter); c.detected_by = "GND-RADAR"
        elif target_type in ["ARM", "SEAD"]:
            c = AntiRadiationMissile(self.track_counter)
            c.detected_by = "GND-RADAR"
        elif target_type in ["CRUISE", "CRUISE_MISSILE"]:
            c = CruiseMissile(self.track_counter)
            c.detected_by = "GND-RADAR"
        else: return
        self.unseen_contacts.append(c)
        self.add_log(f"\033[95m[DEV] MANUAL SPAWN: {target_type} inbound.\033[0m")

    def manual_override_abort(self, target):
        aborted = False
        for eng in list(self.active_engagements):
            if getattr(eng, 'target', None) == target:
                self.active_engagements.remove(eng)
                aborted = True
                wpn = getattr(eng, 'weapon_name', '')
                if wpn in ["F-16", "JAS-39", "FIGHTER"] or "F-16" in wpn or "Gripen" in wpn:
                    self.ammo["FIGHTER"] = min(self.max_ammo.get("FIGHTER", 15), self.ammo.get("FIGHTER", 0) + 1)
        if aborted:
            target.status = "FRIENDLY" if getattr(target, 'is_friendly', False) else "SUSPECT"
            self.add_log(f"\033[41m[ABORT]\033[0m Cancelled engagement on {target.id_code}")

    def _chaff_defeats_shot(self, target, salvo_count=1):
        """CHAFF / EVASION RULE: an aircraft only dispenses chaff because a
        radar-guided missile is actually arriving on it, and whether that chaff
        works is a function of the tactical picture -- how many cartridges the
        platform has left, how capable an EW platform it is, how much range and
        time of flight it has to break the lock, how many missiles are in the
        ripple, and whether our radar is burning through with ECCM. The dice
        roll survives (chaff is genuinely probabilistic) but the probability is
        DERIVED from that context instead of a flat 25%."""
        chance = target.chaff_evasion_chance(
            salvo_count=salvo_count,
            eccm_active=self.burn_through_active
        )
        if chance <= 0.0:
            return False
        return random.random() < chance

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
                salvo_count = getattr(eng, 'salvo_count', 1)
                salvo_mode = getattr(eng, 'salvo_mode', 'SINGLE')

                if eng.weapon_name == "THAAD":
                    base_hit = GameConfig.HIT_CHANCE_THAAD
                    if "AESA_SEEKERS" in self.unlocked_upgrades:
                        base_hit = min(0.95, base_hit + 0.15)
                    if salvo_count == 2:
                        hit_chance = 1.0 - (1.0 - base_hit) ** 2
                    elif salvo_count >= 3:
                        hit_chance = 1.0 - (1.0 - base_hit) ** 3
                        # Salvo fires 3 missiles with maximum P_k against hypersonic threats
                        if getattr(eng.target, 'speed_mach', 0) >= 5.0:
                            hit_chance = max(hit_chance, 0.90)
                    else:
                        hit_chance = base_hit

                    if random.random() <= hit_chance: 
                        eng.target.status = "CLEARED"
                        eng.target.active = False
                        self.record_kill(eng.target, "THAAD")
                        self.emit_event("INTERCEPT_KILL", target_id=eng.target.id_code, target_type=eng.target.type_name, weapon="THAAD", distance_km=eng.target.distance_km, x=eng.target.x_km, y=eng.target.y_km, threat_type=eng.target.type_name, salvo_mode=salvo_mode)
                        salvo_tag = f" ({salvo_mode} x{salvo_count})" if salvo_count > 1 else ""
                        self.add_log(f"\033[92m[KILL] DIRECT HIT! {eng.target.id_code} destroyed by THAAD{salvo_tag}!\033[0m")
                    else:
                        eng.target.status = "FRIENDLY" if getattr(eng.target, 'is_friendly', False) else "HOSTILE"
                        self.add_log(f"\033[91;1m[MISS] THAAD MISSED {eng.target.id_code}! TARGET STILL INCOMING!\033[0m")
                
                elif eng.weapon_name == "SAM":
                    is_radiating_ew = getattr(eng.target, 'is_heavy_ew', False) or "EW" in getattr(eng.target, 'type_name', '') or getattr(eng.target, 'scenario', '') == 'EW'

                    # Chaff Evasion Mechanic (bypassed if HOJ passive homing is active against radiating jammer)
                    if self.hoj_mode and is_radiating_ew:
                        self.add_log(f"\033[93;1m[HOJ] HOME-ON-JAM ACTIVE: Passive seeker riding {eng.target.id_code} RF strobe (chaff decoy bypassed)!\033[0m")
                    elif isinstance(eng.target, Aircraft) and self._chaff_defeats_shot(eng.target, salvo_count):
                        eng.target.chaff_remaining = max(0, getattr(eng.target, 'chaff_remaining', 0) - 1)
                        eng.target.status = "FRIENDLY" if getattr(eng.target, 'is_friendly', False) else "HOSTILE"
                        self.add_log(f"\033[93m[EW] {eng.target.id_code} DEPLOYED CHAFF! SAM DECOYED!\033[0m")
                        continue

                    base_hit = GameConfig.HIT_CHANCE_SAM_NUKE if isinstance(eng.target, ICBM) else \
                               (GameConfig.HIT_CHANCE_SAM_TBM if isinstance(eng.target, TacticalBM) else GameConfig.HIT_CHANCE_SAM_NORMAL)
                    if "AESA_SEEKERS" in self.unlocked_upgrades:
                        base_hit = min(0.95, base_hit + 0.15)
                    
                    # Kinematic modifier: Harder to hit fast targets
                    speed_penalty = max(0.0, (eng.target.speed_mach - 1.0) * 0.10) # -10% per Mach above Mach 1
                    single_hit_chance = max(0.05, base_hit - speed_penalty)
                    
                    if salvo_count == 2:
                        final_hit_chance = 1.0 - (1.0 - single_hit_chance) ** 2
                    elif salvo_count >= 3:
                        final_hit_chance = 1.0 - (1.0 - single_hit_chance) ** 3
                        # Salvo fires 3 missiles with maximum P_k against hypersonic threats
                        if getattr(eng.target, 'speed_mach', 0) >= 5.0:
                            final_hit_chance = max(final_hit_chance, 0.85)
                    else:
                        final_hit_chance = single_hit_chance
                    
                    # Home-On-Jam high lethality boost (>= 85% P_k against radiating jammers)
                    if self.hoj_mode and is_radiating_ew:
                        final_hit_chance = max(0.85, final_hit_chance)
                    
                    if random.random() <= final_hit_chance: 
                        eng.target.status = "CLEARED"
                        eng.target.active = False
                        self.record_kill(eng.target, "SAM")
                        self.emit_event("INTERCEPT_KILL", target_id=eng.target.id_code, target_type=eng.target.type_name, weapon="SAM", distance_km=eng.target.distance_km, x=eng.target.x_km, y=eng.target.y_km, threat_type=eng.target.type_name, salvo_mode=salvo_mode)
                        salvo_tag = f" ({salvo_mode} x{salvo_count})" if salvo_count > 1 else ""
                        if isinstance(eng.target, Airliner):
                            self.base_hp = 0
                            self.add_log(f"\033[41;97m[CRITICAL INCIDENT] YOU SHOT DOWN A COMMERCIAL AIRLINER! COURT-MARTIAL IMMINENT!\033[0m")
                        else:
                            self.add_log(f"\033[92m[KILL] SPLASH! {eng.target.id_code} destroyed by SAM{salvo_tag}!\033[0m")
                    else:
                        eng.target.status = "FRIENDLY" if getattr(eng.target, 'is_friendly', False) else "HOSTILE"
                        self.add_log(f"\033[91;1m[MISS] SAM MISSED {eng.target.id_code}!\033[0m")

                elif eng.weapon_name == "CIWS":
                    base_hit = GameConfig.HIT_CHANCE_CIWS
                    if "RAPID_CIWS" in self.unlocked_upgrades:
                        base_hit = min(0.98, base_hit + 0.10)
                    if random.random() <= base_hit:
                        eng.target.status = "CLEARED"
                        eng.target.active = False
                        self.record_kill(eng.target, "CIWS")
                        self.emit_event("INTERCEPT_KILL", target_id=eng.target.id_code, target_type=eng.target.type_name, weapon="CIWS", distance_km=eng.target.distance_km, x=eng.target.x_km, y=eng.target.y_km, threat_type=eng.target.type_name)
                        self.add_log(f"\033[92m[KILL] BRRRRRT! {eng.target.id_code} shredded by Phalanx CIWS!\033[0m")
                    else:
                        eng.target.status = "FRIENDLY" if getattr(eng.target, 'is_friendly', False) else "HOSTILE"
                        self.add_log(f"\033[91;1m[MISS] CIWS BURST MISSED {eng.target.id_code}!\033[0m")
                
                else: # Fighter Intercept
                    self.returning_fighters.append(GameConfig.F16_RTB_TIME_KILL) 
                    
                    scen = getattr(eng.target, 'scenario', None)
                    if scen in ["RADIO_FAIL", "STRAYED"]: 
                        eng.target.status = "CLEARED"
                        eng.target.active = False
                        self.add_log(f"\033[94m[INTERCEPT]\033[0m {eng.target.id_code} complied. {eng.weapon_name} is RTB.\033[0m")
                    else:
                        # Kinematics for FIGHTER AMRAAMs
                        base_hit_chance = GameConfig.HIT_CHANCE_F16
                        if isinstance(eng.target, (Drone, Helicopter)):
                            base_hit_chance = 0.95 # Fighters dominate slow/defenseless targets

                        speed_penalty = max(0.0, (eng.target.speed_mach - 1.5) * 0.15)
                        final_hit_chance = max(0.10, base_hit_chance - speed_penalty)
                        
                        if random.random() <= final_hit_chance: 
                            eng.target.status = "CLEARED"
                            eng.target.active = False
                            self.record_kill(eng.target, eng.weapon_name)
                            self.emit_event("INTERCEPT_KILL", target_id=eng.target.id_code, target_type=eng.target.type_name, weapon=eng.weapon_name, distance_km=eng.target.distance_km, x=eng.target.x_km, y=eng.target.y_km, threat_type=eng.target.type_name)
                            if isinstance(eng.target, Airliner):
                                self.base_hp = 0
                                self.add_log(f"\033[41;97m[CRITICAL INCIDENT] YOU SHOT DOWN A COMMERCIAL AIRLINER! COURT-MARTIAL IMMINENT!\033[0m")
                            else:
                                self.add_log(f"\033[92m[KILL]\033[0m FOX-3! {eng.target.id_code} splashed by {eng.weapon_name}! {eng.weapon_name} is RTB.\033[0m")
                        else:
                            eng.target.status = "FRIENDLY" if getattr(eng.target, 'is_friendly', False) else "HOSTILE"
                            self.add_log(f"\033[91;1m[MISS]\033[0m {eng.target.id_code} survived {eng.weapon_name} attack! {eng.weapon_name} is RTB.\033[0m")
            else:
                surviving_engagements.append(eng)

        self.active_engagements = surviving_engagements

    # --- Auto-CIWS last-ditch doctrine -------------------------------------
    # The Phalanx holds one 150-round magazine and needs 10 ticks to reload, so
    # it is the LAST layer, not an extra one. These knobs keep it spending that
    # magazine on genuine leakers instead of on whatever drifts through the
    # terminal bubble.
    CIWS_TERMINAL_ETA_TICKS = 3     # inside this ETA, override the "outer layer has it" hold
    CIWS_MAX_TARGETS_PER_TICK = 2   # mounts can only be slewed onto so many leakers per tick
    CIWS_RESERVE_FRACTION = 0.25    # below this magazine level, single highest-value target only

    def _ciws_engage_range(self, c):
        """Terminal bubble radius for this contact (faster leakers are taken
        under fire slightly further out so the burst has time to arrive)."""
        base_engage_range = getattr(self, 'ciws_engage_range', 30.0 if "IRON_BEAM_DIRECTED_ENERGY" in self.unlocked_upgrades else 5.0)
        return max(base_engage_range, c.speed_mach * 1.5)

    def _is_outer_layer_engaged(self, c):
        """True when THAAD/SAM/fighters already have a shot in the air at `c`."""
        for eng in self.active_engagements:
            if getattr(eng, 'target', None) is c and getattr(eng, 'weapon_name', '') != "CIWS":
                return True
        return False

    def _is_ciws_leaker(self, c):
        """LAST-DITCH RULE: CIWS only fires on a genuine leaker -- something
        that is closing on the base, can actually hurt it, and has defeated or
        bypassed the outer SAM/THAAD/fighter layers. Everything else (injected
        EW ghosts, bird/weather clutter, IFF squawkers, traffic that merely
        crossed the bubble, and targets another layer already has a missile on)
        is held, because a burst spent there is a burst the next real leaker
        will not get."""
        if not c.active:
            return False
        if c.status in ["FRIENDLY", "CLEARED"]:
            return False
        if c.distance_km > self._ciws_engage_range(c):
            return False
        # 1. Injected false targets and clutter cannot damage the base.
        if isinstance(c, (GhostTrack, EWGhostTrack)):
            return False
        # 2. A contact answering IFF is not a valid last-ditch target.
        if getattr(c, 'has_transponder', False):
            return False
        # 3. Must genuinely be running in on the base.
        if not c.is_closing_on_base():
            return False
        # 4. Already covered by an outer layer -- only take the shot once the
        #    leaker is terminal and that layer has demonstrably not stopped it.
        if self._is_outer_layer_engaged(c) and c.get_eta() > self.CIWS_TERMINAL_ETA_TICKS:
            return False
        return True

    def get_ciws_priority_targets(self):
        """Leakers inside the terminal bubble, ranked by calculate_threat_score()
        (ICBM > cruise/ARM > TBM > incidental traffic) and clipped to what the
        mounts -- and the remaining magazine -- can honestly service this tick."""
        leakers = [c for c in self.contacts if self._is_ciws_leaker(c)]
        leakers.sort(key=lambda c: (-c.calculate_threat_score(), c.distance_km))
        budget = self.CIWS_MAX_TARGETS_PER_TICK
        if self.ammo["CIWS"] <= self.max_ammo["CIWS"] * self.CIWS_RESERVE_FRACTION:
            budget = 1
        return leakers[:budget]

    def process_auto_ciws(self):
        # Auto-CIWS: prioritised last-ditch point defence (autonomous in BOTH
        # Spectator and Player modes -- it is self-defence, never a player toy).
        for c in self.get_ciws_priority_targets():
            if self.ammo["CIWS"] > 0:
                # Higher speed targets require more ammunition spread
                curtain_spread = max(1, int(c.speed_mach)) 
                ammo_used = min(curtain_spread, self.ammo["CIWS"])
                self.ammo["CIWS"] -= ammo_used
                
                hit_multiplier = 1.0 + (ammo_used * 0.10) 
                speed_penalty = max(0.0, (c.speed_mach - 0.5) * 0.15) # CIWS struggles with Mach 2+ targets
                final_hit_chance = max(0.05, min(0.95, GameConfig.HIT_CHANCE_CIWS * hit_multiplier - speed_penalty))
                if "IRON_BEAM_DIRECTED_ENERGY" in self.unlocked_upgrades:
                    final_hit_chance = max(0.95, final_hit_chance)
                
                hit = (random.random() <= final_hit_chance)
                self.emit_event("CIWS_FIRE", target_id=c.id_code, ammo_used=ammo_used, hit=hit)
                if hit:
                    weapon_label = "Helios Laser" if "IRON_BEAM_DIRECTED_ENERGY" in self.unlocked_upgrades else "Phalanx CIWS"
                    self.add_log(f"\033[91;1m[AUTO-CIWS] BRRRRRRT! (Spread x{ammo_used}) {c.id_code} SHREDDED by {weapon_label}! (Ammo: {self.ammo['CIWS']})\033[0m")
                    c.status = "CLEARED"
                    c.active = False
                    self.record_kill(c, "CIWS")
                    self.emit_event("INTERCEPT_KILL", target_id=c.id_code, target_type=c.type_name, weapon="CIWS", distance_km=c.distance_km)
                else:
                    if self.tick_count % 2 == 0: 
                        self.add_log(f"\033[93;1m[AUTO-CIWS] BRRRRRRT! MISSED {c.id_code} DESPITE SPREAD! TARGET EVADED!\033[0m")
            else:
                if self.tick_count % 3 == 0: self.add_log(f"\033[41;97m[AUTO-CIWS] CLICK! CIWS RELOADING! BRACE FOR IMPACT: {c.id_code}!\033[0m")

    def update_world(self):
        # Update active RF decoys
        updated_decoys = []
        for d in self.active_decoys:
            d["timer"] -= 1
            if d["timer"] <= 0:
                d["active"] = False
                self.add_log(f"\033[90m[COUNTERMEASURES] RF Decoy {d.get('id', '')} at ({d['x']:.1f}, {d['y']:.1f}) burned out.\033[0m")
            else:
                updated_decoys.append(d)
        self.active_decoys = updated_decoys

        # Update ECCM Burn-Through Timer
        if self.burn_through_active:
            self.burn_through_timer -= 1
            if self.burn_through_timer <= 0:
                self.burn_through_active = False
                self.emit_event("ECCM_BURN_THROUGH", active=False)
                self.add_log("\033[90m[ECCM] Radar burn-through overdrive expired. Returning to standard scan.\033[0m")

        # Process Passive ESM Cross-Bearing Triangulation (Ground C2 + AWACS)
        self.process_esm_triangulation()

        # Identify active Jammers (must be HOSTILE) and AWACS
        ew_aircrafts = [c for c in self.contacts if c.active and getattr(c, 'status', '') == 'HOSTILE' and "EW" in getattr(c, 'type_name', '')]
        has_awacs = any(isinstance(c, AWACS) for c in self.contacts if c.active)
        effective_radar_alt = 35000 if has_awacs else 150 # AWACS looks down from 35,000 ft, massively extending radar horizon!
        
        # Process unseen contacts (move them, check if they cross the detection threshold)
        surviving_unseen = []
        for c in self.unseen_contacts:
            if c.active:
                c.move(self)
                
                # Check jamming factor taking into account ECCM burn-through
                jamming_factor = self.get_jamming_factor(c, ew_aircrafts)

                # EMCON Detection Check:
                # If SILENT: ground radar is blind (contacts only visible if within AWACS or CAP visual/radar range)
                in_sensor = self.is_in_sensor_coverage(c)
                is_space = (getattr(c, 'detected_by', '') == 'SPACE-COM')
                is_quantum = ("QUANTUM_SPACE_RADAR" in self.unlocked_upgrades)

                can_detect = False
                if is_quantum:
                    can_detect = True
                    c.is_masked = False
                    c.detected_by = "QUANTUM-SPACE"
                elif is_space:
                    can_detect = True
                elif in_sensor:
                    can_detect = True
                    c.detected_by = "AWACS" if has_awacs else "CAP"
                elif self.emcon_mode == "SILENT":
                    can_detect = False # Ground radar is blind in SILENT!
                elif self.emcon_mode == "SECTOR":
                    in_sector = (c.bearing <= 60 or c.bearing >= 300)
                    if in_sector and c.is_detectable_by_radar(radar_alt_ft=effective_radar_alt, jamming_factor=jamming_factor):
                        can_detect = True
                else: # ACTIVE
                    if c.is_detectable_by_radar(radar_alt_ft=effective_radar_alt, jamming_factor=jamming_factor):
                        can_detect = True
                
                if can_detect:
                    self.contacts.append(c)
                    self.add_log(f"\033[90m[SYS] NEW TRACK: {c.id_code} appeared on radar.\033[0m")
                elif c.distance_km <= 0:
                    c.active = False
                    if isinstance(c, ICBM):
                        damage = GameConfig.DAMAGE_ICBM
                    elif isinstance(c, TacticalBM):
                        damage = GameConfig.DAMAGE_TBM
                    elif isinstance(c, AntiRadiationMissile):
                        damage = getattr(GameConfig, 'DAMAGE_ARM', 35)
                    elif isinstance(c, CruiseMissile):
                        damage = getattr(GameConfig, 'DAMAGE_CRUISE', 25)
                    else:
                        damage = GameConfig.DAMAGE_AIRCRAFT
                    self.base_hp -= damage
                    self.emit_event("BASE_DAMAGE", source_id=c.id_code, damage=damage, remaining_hp=self.base_hp)
                    self.add_log(f"\033[41;97m[DEFENSE] AMBUSH! {c.id_code} hit base below radar horizon!\033[0m")
                else:
                    surviving_unseen.append(c)
        self.unseen_contacts = surviving_unseen

        # Process visible contacts
        for c in self.contacts:
            if c.active:
                c.move(self)

                # Update visibility based on EMCON
                if not self.is_contact_visible(c):
                    c.brightness = 0.0
                
                if c.status == "FRIENDLY" and not isinstance(c, (AWACS, CAPFighter, VIPTransport)) and not getattr(c, 'is_vip', False) and random.random() < 0.03:
                    c.active = False
                    if isinstance(c, Airliner):
                        self.airliners_safe += 1
                        self.award_xp(50, "Airliner safely departed")
                    self.add_log(f"\033[94m[TRAFFIC] {c.id_code} has left the monitored sector.\033[0m")
                    continue

                if c.distance_km <= 0:
                    c.active = False
                    if isinstance(c, EWGhostTrack):
                        continue  # False target, no damage
                    if c.status == "FRIENDLY" or getattr(c, 'is_friendly', False) or isinstance(c, Airliner): 
                        if isinstance(c, Airliner):
                            self.airliners_safe += 1
                            self.award_xp(50, "Airliner safe passage")
                        self.add_log(f"\033[94m[TRAFFIC] {c.id_code} safely passed through airspace.\033[0m")
                    else:
                        if isinstance(c, ICBM):
                            damage = GameConfig.DAMAGE_ICBM
                        elif isinstance(c, TacticalBM):
                            damage = GameConfig.DAMAGE_TBM
                        elif isinstance(c, AntiRadiationMissile):
                            damage = getattr(GameConfig, 'DAMAGE_ARM', 35)
                        elif isinstance(c, CruiseMissile):
                            damage = getattr(GameConfig, 'DAMAGE_CRUISE', 25)
                        else:
                            damage = GameConfig.DAMAGE_AIRCRAFT
                            
                        self.base_hp -= damage
                        self.emit_event("BASE_DAMAGE", source_id=c.id_code, damage=damage, remaining_hp=self.base_hp)
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

        # Recover landed AWACS and CAP before purging inactive contacts
        for c in self.contacts:
            if not c.active and getattr(c, 'state', None) == "RTB":
                if isinstance(c, AWACS):
                    self.awacs_pool += 1
                    self.add_log(f"\033[94m[AIRBASE] {c.id_code} landed safely at Wing 7 and refueling.\033[0m")
                elif isinstance(c, CAPFighter):
                    self.cap_pool += 1
                    self.add_log(f"\033[94m[AIRBASE] {c.id_code} landed safely and refueling.\033[0m")

        self.contacts = [c for c in self.contacts if c.active]

    def get_after_action_report(self):
        outcome = "VICTORY" if self.base_hp > 0 else ("COURT-MARTIAL" if self.is_court_martialed else "DEFEAT (BASE DESTROYED)")
        lr_kills = sum(1 for e in self.historical_events if e.get("type") == "INTERCEPT_KILL" and e.get("distance_km", 0) > 400)
        
        medals = []
        if self.kills >= 20: medals.append("Air Defense Cross")
        elif self.kills >= 10: medals.append("Distinguished Service Ribbon")
        elif self.kills >= 5: medals.append("Combat Action Ribbon")
        if self.airliners_safe >= 8: medals.append("Civil Air Safety Citation")
        if not medals: medals = ["None Awarded"]

        if self.is_court_martialed: grade = "F (COURT-MARTIAL)"
        elif self.kills >= 20 and self.base_hp >= 80: grade = "A+"
        elif self.kills >= 15 and self.base_hp >= 50: grade = "A"
        elif self.kills >= 10: grade = "B"
        elif self.kills >= 5: grade = "C"
        else: grade = "D"

        report = {
            "duration_ticks": self.tick_count,
            "survival_time_sec": self.tick_count,
            "outcome": outcome,
            "rank": self.rank,
            "xp": self.xp,
            "kills": self.kills,
            "kills_by_type": dict(self.kills_by_type),
            "kills_by_weapon": dict(self.kills_by_weapon),
            "long_range_kills": lr_kills,
            "airliners_safe": self.airliners_safe,
            "is_court_martialed": self.is_court_martialed,
            "base_hp_remaining": max(0, self.base_hp),
            "emcon_mode": self.emcon_mode,
            "salvo_mode": self.salvo_mode,
            "decoys_remaining": self.decoys_remaining,
            "total_events": len(self.historical_events),
            "medals": medals,
            "grade": grade,
        }
        
        banner = "=" * 62
        lines = [
            banner,
            "        ROYAL THAI AIR FORCE - AFTER-ACTION REPORT (AAR)      ",
            banner,
            f" MISSION STATUS : {outcome:<20} DURATION: T+{self.tick_count}s",
            f" OFFICER RANK   : {self.rank.upper():<20} TOTAL XP: {self.xp}",
            f" BASE HEALTH    : {max(0, self.base_hp):<4}%",
            "-" * 62,
            f" CONFIRMED INTERCEPT KILLS : {self.kills}",
            f"   - Long-Range (>400km)   : {lr_kills}",
            f" CIVILIAN AIRLINERS SAFE   : {self.airliners_safe}",
            f" FINAL EMCON POSTURE       : {self.emcon_mode}",
            f" FINAL SALVO DOCTRINE      : {self.salvo_mode}",
            f" ACTIVE RF DECOYS REMAINING: {self.decoys_remaining}/3",
            f" RECORDED TACTICAL EVENTS  : {len(self.historical_events)}",
            "-" * 62,
            " KILLS BY THREAT TYPE:"
        ]
        if self.kills_by_type:
            for t, count in sorted(self.kills_by_type.items()):
                lines.append(f"   * {t:<22}: {count}")
        else:
            lines.append("   * None")
            
        lines.append("-" * 62)
        lines.append(" WEAPON SPLASH RECORD:")
        if self.kills_by_weapon:
            for w, count in sorted(self.kills_by_weapon.items()):
                lines.append(f"   * {w:<22}: {count}")
        else:
            lines.append("   * None")
            
        lines.append(banner)
        report["summary"] = "\n".join(lines)
        return report
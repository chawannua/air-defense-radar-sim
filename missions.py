import random
from abc import ABC, abstractmethod
from targets import VIPTransport, StealthBomber, CruiseMissile, AntiRadiationMissile, Drone, TacticalBM, ICBM

class Mission(ABC):
    def __init__(self, code, name, briefing, win_desc):
        self.code = code
        self.name = name
        self.briefing = briefing
        self.win_desc = win_desc
        self.state = 'IN_PROGRESS'
        self.mission_ticks = 0

    @abstractmethod
    def on_start(self, cmd):
        pass

    @abstractmethod
    def tick(self, cmd):
        pass

    def check_outcome(self, cmd):
        if cmd.base_hp <= 0:
            self.state = 'DEFEAT'
            return 'DEFEAT'
        return self.state


class StandardCampaign(Mission):
    def __init__(self):
        super().__init__(
            code='OP-DEFENSE',
            name='Endless Air Defense',
            briefing='Standard 3-Phase Defense posture across Bangkok FIR. Maintain airspace sovereignty from peacetime through DEFCON 1 wartime.',
            win_desc='Survive as long as possible with maximum score and airliners protected.'
        )

    def on_start(self, cmd):
        self.mission_ticks = 0
        cmd.add_log(f'[BRIEFING] {self.code}: {self.name} ACTIVE.')

    def tick(self, cmd):
        self.mission_ticks += 1
        return self.check_outcome(cmd)


class VIPEscortMission(Mission):
    def __init__(self):
        super().__init__(
            code='OP-GUARDIAN',
            name='Operation Guardian Angel (VIP Escort)',
            briefing='Royal Thai VIP Transport ROYAL-01 enroute from Chiang Mai to Don Mueang. Hostile air elements detected attempting intercept. Protect VIP at all costs!',
            win_desc='ROYAL-01 touches down safely at Don Mueang (VTBD).'
        )
        self.vip_contact = None
        self.ambush_spawned = False

    def on_start(self, cmd):
        self.mission_ticks = 0
        self.vip_contact = VIPTransport(track_number=999)
        cmd.contacts.append(self.vip_contact)
        cmd.add_log('[VIP OPERATION] ROYAL-01 AIRBORNE FROM CHIANG MAI. INGRESSING SOUTH TOWARD BANGKOK.')
        cmd.emit_event('VIP_DEPARTURE', callsign='ROYAL-01')

    def tick(self, cmd):
        self.mission_ticks += 1
        
        if self.vip_contact:
            if getattr(self.vip_contact, 'has_arrived', False):
                self.state = 'VICTORY'
                cmd.add_log('[OPERATION COMPLETE] VIP SAFELY ESCORTED! OUTSTANDING COMMAND PERFORMANCE.')
                return 'VICTORY'
            if not self.vip_contact.active and not getattr(self.vip_contact, 'has_arrived', False):
                self.state = 'DEFEAT'
                cmd.base_hp = 0
                cmd.is_court_martialed = True
                cmd.add_log('[MISSION FAILED] ROYAL-01 DESTROYED! COURT-MARTIAL CONVENED.')
                return 'DEFEAT'

        if self.mission_ticks == 15:
            cmd.add_log('[INTEL] Hostile MiG-29 flight attempting BVR intercept on ROYAL-01!')
            cmd.manual_spawn('FIGHTER')
            cmd.manual_spawn('FIGHTER')
        elif self.mission_ticks == 35:
            cmd.add_log('[INTEL] Second echelon interceptors and suicide drones inbound on VIP flight corridor!')
            cmd.manual_spawn('DRONE')
            cmd.manual_spawn('DRONE')
            cmd.manual_spawn('FIGHTER')

        return self.check_outcome(cmd)


class IronSwarmMission(Mission):
    def __init__(self):
        super().__init__(
            code='OP-IRONSWARM',
            name='Operation Iron Swarm (Saturation Defense)',
            briefing='Enemy has launched a mass saturation strike against Bangkok. 3 waves of drones, cruise missiles, and ballistic missiles. Ammo is strictly limited.',
            win_desc='Neutralize all 3 hostile waves while preserving base integrity.'
        )
        self.wave_count = 0

    def on_start(self, cmd):
        self.mission_ticks = 0
        self.wave_count = 0
        cmd.tick_count = 360
        cmd.add_log('[DEFCON 1] MASS ENEMY SATURATION STRIKE IMMINENT. 3 WAVES DETECTED.')

    def tick(self, cmd):
        self.mission_ticks += 1
        
        if self.mission_ticks == 5:
            cmd.add_log('[WAVE 1/3] Mass loitering munitions swarm crossing border!')
            for _ in range(8): cmd.manual_spawn('DRONE')
            self.wave_count = 1
            
        elif self.mission_ticks == 30:
            cmd.add_log('[WAVE 2/3] Supersonic Cruise Missiles and SEAD Anti-Radiation Missiles inbound!')
            cmd.manual_spawn('CRUISE')
            cmd.manual_spawn('CRUISE')
            cmd.manual_spawn('ARM')
            cmd.manual_spawn('ARM')
            self.wave_count = 2
            
        elif self.mission_ticks == 60:
            cmd.add_log('[WAVE 3/3] BALLISTIC MISSILE LAUNCH DETECTED. FINAL STRIKE WAVE!')
            cmd.manual_spawn('ICBM')
            cmd.manual_spawn('ARM')
            for _ in range(4): cmd.manual_spawn('CRUISE')
            self.wave_count = 3

        if self.mission_ticks > 80:
            hostile_count = sum(1 for c in cmd.contacts if c.active and getattr(c, 'status', '') in ['HOSTILE', 'ENGAGING'])
            if hostile_count == 0 and cmd.base_hp > 0:
                if self.state != 'VICTORY':
                    self.state = 'VICTORY'
                    cmd.add_log('[VICTORY] ALL 3 SATURATION WAVES DESTROYED. BANGKOK DEFENSES PRESERVED!')
                    cmd.award_xp(8000, 'Iron Swarm Cleared')
                return 'VICTORY'

        return self.check_outcome(cmd)


class GhostHunterMission(Mission):
    def __init__(self):
        super().__init__(
            code='OP-GHOST',
            name='Operation Ghost Hunter (Stealth Intercept)',
            briefing='2x Low-RCS Strategic Stealth Bombers ingressing at 50,000 ft. Ground radar cannot acquire beyond 35 km! Scramble forward Gripens and AWACS to triangulate!',
            win_desc='Destroy both Stealth Bombers before they reach standoff weapon launch points.'
        )
        self.bombers = []

    def on_start(self, cmd):
        self.mission_ticks = 0
        cmd.tick_count = 200
        cmd.add_log('[RADAR WARNING] Low-RCS stealth penetrators reported by forward SIGINT. Deploy AWACS!')
        b1 = StealthBomber(track_number=701, distance_km=600)
        b2 = StealthBomber(track_number=702, distance_km=680)
        cmd.contacts.extend([b1, b2])
        self.bombers = [b1, b2]

    def tick(self, cmd):
        self.mission_ticks += 1
        
        if self.bombers and all(not b.active for b in self.bombers):
            if self.state != 'VICTORY':
                self.state = 'VICTORY'
                cmd.add_log('[VICTORY] BOTH STEALTH BOMBERS SPLASHED BEFORE STANDOFF LAUNCH. AIRSPACE SECURE.')
                cmd.award_xp(10000, 'Ghost Hunter Cleared')
            return 'VICTORY'

        return self.check_outcome(cmd)


class MissionManager:
    def __init__(self):
        self.missions = [
            StandardCampaign(),
            VIPEscortMission(),
            IronSwarmMission(),
            GhostHunterMission()
        ]
        self.current_idx = 0

    @property
    def current(self):
        return self.missions[self.current_idx]

    def select_mission(self, idx, cmd):
        if 0 <= idx < len(self.missions):
            self.current_idx = idx
            cmd.contacts.clear()
            cmd.unseen_contacts.clear()
            cmd.active_engagements.clear()
            cmd.threat_queue = type(cmd.threat_queue)()
            self.current.state = 'IN_PROGRESS'
            self.current.on_start(cmd)
            return self.current
        return None

    def cycle_mission(self, cmd):
        next_idx = (self.current_idx + 1) % len(self.missions)
        return self.select_mission(next_idx, cmd)
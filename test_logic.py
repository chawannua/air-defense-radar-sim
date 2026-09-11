"""Headless integration test for the air defense simulator logic."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from targets import (AirContact, Aircraft, Helicopter, Drone, TacticalBM, ICBM,
                     Airliner, AWACS, CAPFighter, GhostTrack, EWGhostTrack,
                     AntiRadiationMissile, CruiseMissile, is_line_of_sight_masked)
from command_center import CommandCenter
from personnel import Engagement
from config import GameConfig
from sound_engine import SoundManager, synth_missile_launch
import random
import math
import inspect
import numpy as np

errors = []
def check(condition, msg):
    if not condition:
        errors.append(f"FAIL: {msg}")
        print(f"  FAIL: {msg}")
    else:
        print(f"  OK: {msg}")

print("=== 1. Coordinate System Tests ===")

# AirContact base: bearing 0 should be North (positive Y)
a = Aircraft(1)
a.bearing = 0
a.distance_km = 100
a.x_km = 100 * math.sin(math.radians(0))  # Should be 0
a.y_km = 100 * math.cos(math.radians(0))  # Should be 100
check(abs(a.x_km) < 0.01, f"Bearing 0: x_km should be ~0, got {a.x_km:.2f}")
check(abs(a.y_km - 100) < 0.01, f"Bearing 0: y_km should be ~100, got {a.y_km:.2f}")

# Bearing 90 should be East (positive X)
a.bearing = 90
a.x_km = 100 * math.sin(math.radians(90))  # Should be 100
a.y_km = 100 * math.cos(math.radians(90))  # Should be ~0
check(abs(a.x_km - 100) < 0.01, f"Bearing 90: x_km should be ~100, got {a.x_km:.2f}")
check(abs(a.y_km) < 0.01, f"Bearing 90: y_km should be ~0, got {a.y_km:.2f}")

print("\n=== 2. AWACS set_xy bearing consistency ===")
awacs = AWACS(10)
awacs.set_xy(100.0, 0.0)  # Due East
check(abs(awacs.bearing - 90) < 1.0, f"set_xy(100,0) bearing should be ~90, got {awacs.bearing:.1f}")
awacs.set_xy(0.0, 100.0)  # Due North
check(abs(awacs.bearing) < 1.0 or abs(awacs.bearing - 360) < 1.0, f"set_xy(0,100) bearing should be ~0, got {awacs.bearing:.1f}")
awacs.set_xy(-100.0, 0.0)  # Due West
check(abs(awacs.bearing - 270) < 1.0, f"set_xy(-100,0) bearing should be ~270, got {awacs.bearing:.1f}")

print("\n=== 3. CAPFighter set_xy bearing consistency ===")
cap = CAPFighter(20, 4, 150.0, 300.0, "F-16 (CAP)")
cap.set_xy(100.0, 0.0)
check(abs(cap.bearing - 90) < 1.0, f"CAPFighter set_xy(100,0) bearing should be ~90, got {cap.bearing:.1f}")

print("\n=== 4. AWACS move() heading matches direction ===")
awacs2 = AWACS(30)
awacs2.x_km = 0.0
awacs2.y_km = 0.0
awacs2.state = "TRANSIT_TO_STATION"
# Orbit center is at (20, -150), so heading should point roughly south-ish
awacs2.move()
dx = awacs2.x_km - 0.0
dy = awacs2.y_km - 0.0
actual_heading_from_movement = (math.degrees(math.atan2(dx, dy)) + 360) % 360
check(abs(actual_heading_from_movement - awacs2.heading) < 5.0,
      f"AWACS heading {awacs2.heading:.1f} should match movement direction {actual_heading_from_movement:.1f}")

print("\n=== 5. Airliner move() uses correct Y convention ===")
liner = Airliner(40)
liner.heading = 0  # Heading North
liner.x_km = 0
liner.y_km = 500
liner.distance_km = 500
liner.bearing = 0
old_y = liner.y_km
liner.move()
check(liner.y_km > old_y, f"Airliner heading 0 (North) should increase y_km: {old_y:.1f} -> {liner.y_km:.1f}")

print("\n=== 6. EWGhostTrack spawns correctly ===")
ghost = EWGhostTrack(50)
check(ghost.active, "EWGhostTrack should be active on creation")
check(ghost.lifespan >= 2 and ghost.lifespan <= 8, f"EWGhostTrack lifespan should be 2-8, got {ghost.lifespan}")
check(abs(ghost.x_km) > 0.01 or abs(ghost.y_km) > 0.01, "EWGhostTrack should have non-zero position")
check(ghost.distance_km >= 50 and ghost.distance_km <= 600, f"EWGhostTrack distance should be 50-600, got {ghost.distance_km}")

print("\n=== 7. CommandCenter EW ghost injection ===")
cmd = CommandCenter()
# Manually add a heavy EW aircraft to contacts (already identified)
ew_plane = Aircraft(999)
ew_plane.is_heavy_ew = True
ew_plane.is_friendly = False
ew_plane.status = "HOSTILE"
ew_plane.type_name = "EA-18G Growler (HEAVY EW)"
ew_plane.active = True
ew_plane.brightness = 1.0
ew_plane.visible_dist = 500
cmd.contacts.append(ew_plane)

# Run detect_airspace many times, ghosts should appear in contacts
import random
random.seed(42)  # Deterministic
contacts_before = len(cmd.contacts)
for _ in range(20):
    cmd.detect_airspace()
contacts_after = len(cmd.contacts)
ghost_count = sum(1 for c in cmd.contacts if isinstance(c, EWGhostTrack))
check(ghost_count > 0, f"EW ghost tracks should appear in contacts (found {ghost_count})")
check(contacts_after > contacts_before, f"Contacts should increase: {contacts_before} -> {contacts_after}")

# Verify ghosts have brightness and visible_dist
for c in cmd.contacts:
    if isinstance(c, EWGhostTrack):
        check(hasattr(c, 'brightness') and c.brightness == 1.0, f"Ghost {c.id_code} should have brightness=1.0")
        check(hasattr(c, 'visible_dist'), f"Ghost {c.id_code} should have visible_dist")
        break

print("\n=== 8. EWGhostTrack should not cause base damage ===")
cmd2 = CommandCenter()
ghost2 = EWGhostTrack(888)
ghost2.distance_km = 0.5
ghost2.speed_mach = 1.0
ghost2.active = True
ghost2.brightness = 1.0
ghost2.visible_dist = ghost2.distance_km
cmd2.contacts.append(ghost2)
hp_before = cmd2.base_hp
cmd2.update_world()
check(cmd2.base_hp == hp_before, f"EWGhostTrack reaching base should NOT cause damage: HP {hp_before} -> {cmd2.base_hp}")

print("\n=== 9. Base AirContact move() updates x_km/y_km ===")
drone = Drone(60)
drone.bearing = 180  # South
drone.distance_km = 100
drone.speed_mach = 1.0
drone.x_km = 100 * math.sin(math.radians(180))
drone.y_km = 100 * math.cos(math.radians(180))
old_x, old_y = drone.x_km, drone.y_km
drone.move()
check(drone.x_km != 0 or drone.y_km != 0, f"Drone x_km/y_km should be set after move: ({drone.x_km:.1f}, {drone.y_km:.1f})")
check(drone.distance_km < 100, f"Drone moving towards center should decrease distance: {drone.distance_km:.1f}")

print("\n=== 10. AntiRadiationMissile (ARM) Behavior ===")
arm = AntiRadiationMissile(101, distance_km=200)
check(3.5 <= arm.speed_mach <= 4.5, f"ARM speed should be Mach 3.5-4.5, got {arm.speed_mach:.2f}")
check(arm.seeker_locked == True, "ARM should initialize with seeker_locked=True")
check(arm.scenario == "SEAD", "ARM scenario should be SEAD")
arm.identify_target()
check("ARM-" in arm.id_code, f"ARM id_code should contain 'ARM-', got {arm.id_code}")

# ARM homing toward (0, 0) under ACTIVE EMCON
cmd_arm = CommandCenter()
cmd_arm.emcon_mode = "ACTIVE"
arm.x_km = 100.0
arm.y_km = 0.0
arm.distance_km = 100.0
arm.move(cmd_arm)
check(arm.x_km < 100.0, f"ARM should move towards origin: x={arm.x_km:.2f}")
check(arm.seeker_locked == True, "ARM should maintain seeker lock in ACTIVE EMCON")

# ARM dropping lock under SILENT EMCON
cmd_arm.emcon_mode = "SILENT"
arm.move(cmd_arm)
check(arm.seeker_locked == False, "ARM should drop lock when EMCON is SILENT")
warning_logged = any("lost radar emitter lock" in msg for msg in cmd_arm.tactical_log)
check(warning_logged, "Tactical warning should be logged when ARM drops lock")

# ARM seduced by active RF decoy
arm2 = AntiRadiationMissile(102, distance_km=150)
cmd_decoy = CommandCenter()
cmd_decoy.active_decoys = [{"id": "TEST_DECOY", "x": 15.0, "y": 15.0, "timer": 20, "active": True}]
arm2.x_km = 20.0
arm2.y_km = 20.0
arm2.move(cmd_decoy)
check(arm2.target_x == 15.0 and arm2.target_y == 15.0, f"ARM should target active decoy at (15, 15), got ({arm2.target_x}, {arm2.target_y})")


print("\n=== 11. CruiseMissile and Terrain Masking ===")
cm = CruiseMissile(201, distance_km=300)
check(cm.speed_mach == 0.85, f"Cruise missile speed should be 0.85 Mach, got {cm.speed_mach}")
check(cm.altitude_ft == 200, f"Cruise missile altitude should be 200 ft, got {cm.altitude_ft}")
check(cm.rcs == 0.01, f"Cruise missile RCS should be 0.01, got {cm.rcs}")
cm.identify_target()
check("CRUISE-" in cm.id_code, f"Cruise missile id_code should contain 'CRUISE-', got {cm.id_code}")

# Line of sight masking test:
# Doi Inthanon is at x=-217.9, y=534.3, alt=8415 ft
# Collinear target at 1.2x distance: x=-261.48, y=641.16 at alt=200 ft has LOS directly through Doi Inthanon
is_masked = is_line_of_sight_masked(-261.48, 641.16, 200)
check(is_masked == True, "Target at (-261.48, 641.16) at 200 ft should be masked by Doi Inthanon")

# Same target at high altitude (10000 ft) should NOT be masked
not_masked = is_line_of_sight_masked(-261.48, 641.16, 10000)
check(not_masked == False, "Target at (-261.48, 641.16) at 10000 ft should NOT be masked")

# Target in clear sector (e.g. x=300, y=0) should NOT be masked
clear_masked = is_line_of_sight_masked(300, 0, 200)
check(clear_masked == False, "Target at (300, 0) at 200 ft should NOT be masked (clear sector)")

# Detection check with ground radar (radar_alt_ft=150):
cm_test = CruiseMissile(202)
cm_test.x_km = -261.48
cm_test.y_km = 641.16
cm_test.distance_km = math.hypot(-261.48, 641.16)
cm_test.altitude_ft = 200
check(cm_test.is_detectable_by_radar(radar_alt_ft=150) == False, "Masked cruise missile must NOT be detectable by ground radar")
check(cm_test.is_masked == True, "cm_test.is_masked should be set to True")

# Clear line-of-sight cruise missile within airborne sensor horizon
cm_air = CruiseMissile(203)
cm_air.x_km = 0
cm_air.y_km = 50
cm_air.distance_km = 50
cm_air.altitude_ft = 200
check(cm_air.is_detectable_by_radar(radar_alt_ft=30000) == True, "Cruise missile should be detectable from airborne sensor altitude")


print("\n=== 12. EMCON Toggle and Sensor Detection Gating ===")
cmd_emcon = CommandCenter()
check(cmd_emcon.emcon_mode == "ACTIVE", "Default EMCON mode should be ACTIVE")
cmd_emcon.toggle_emcon()
check(cmd_emcon.emcon_mode == "SECTOR", "First toggle should switch to SECTOR")
cmd_emcon.toggle_emcon()
check(cmd_emcon.emcon_mode == "SILENT", "Second toggle should switch to SILENT")
cmd_emcon.toggle_emcon()
check(cmd_emcon.emcon_mode == "ACTIVE", "Third toggle should wrap to ACTIVE")

# In SILENT mode, ground radar does not detect contacts outside sensor coverage
cmd_emcon.emcon_mode = "SILENT"
test_contact = Drone(301)
test_contact.distance_km = 100
test_contact.x_km = 100
test_contact.y_km = 0
test_contact.bearing = 90
cmd_emcon.contacts = [test_contact]
cmd_emcon.update_world()
check(test_contact.brightness == 0.0, "Contact without AWACS/CAP should have brightness 0.0 in SILENT mode")


print("\n=== 13. Salvo Firing Doctrine & P_k Calculation ===")
cmd_salvo = CommandCenter()
check(cmd_salvo.salvo_mode == "SINGLE", "Default salvo mode should be SINGLE")
cmd_salvo.toggle_salvo()
check(cmd_salvo.salvo_mode == "RIPPLE", "Toggle should switch to RIPPLE")
cmd_salvo.toggle_salvo()
check(cmd_salvo.salvo_mode == "SALVO", "Toggle should switch to SALVO")
cmd_salvo.toggle_salvo()
check(cmd_salvo.salvo_mode == "SINGLE", "Toggle should cycle back to SINGLE")

tgt = Aircraft(401)
tgt.status = "HOSTILE"
tgt.distance_km = 50
tgt.x_km = 0
tgt.y_km = 50
tgt.speed_mach = 1.0
tgt.altitude_ft = 20000
cmd_salvo.contacts = [tgt]

# Single mode consumes 1 SAM
initial_sam = cmd_salvo.ammo["SAM"]
cmd_salvo.salvo_mode = "SINGLE"
cmd_salvo.manual_override_fire(tgt, "SAM")
check(cmd_salvo.ammo["SAM"] == initial_sam - 1, f"SINGLE mode should consume 1 SAM: {initial_sam} -> {cmd_salvo.ammo['SAM']}")
check(len(cmd_salvo.active_engagements) == 1, "Should create 1 engagement")
check(cmd_salvo.active_engagements[0].salvo_count == 1, "Engagement salvo_count should be 1")

# Ripple mode consumes 2 SAMs
cmd_salvo.active_engagements.clear()
initial_sam = cmd_salvo.ammo["SAM"]
cmd_salvo.salvo_mode = "RIPPLE"
cmd_salvo.manual_override_fire(tgt, "SAM")
check(cmd_salvo.ammo["SAM"] == initial_sam - 2, f"RIPPLE mode should consume 2 SAMs: {initial_sam} -> {cmd_salvo.ammo['SAM']}")
check(cmd_salvo.active_engagements[0].salvo_count == 2, "Engagement salvo_count should be 2")

# Salvo mode consumes 3 SAMs
cmd_salvo.active_engagements.clear()
initial_sam = cmd_salvo.ammo["SAM"]
cmd_salvo.salvo_mode = "SALVO"
cmd_salvo.manual_override_fire(tgt, "SAM")
check(cmd_salvo.ammo["SAM"] == initial_sam - 3, f"SALVO mode should consume 3 SAMs: {initial_sam} -> {cmd_salvo.ammo['SAM']}")
check(cmd_salvo.active_engagements[0].salvo_count == 3, "Engagement salvo_count should be 3")


print("\n=== 14. Active RF Decoys Countermeasure ===")
cmd_dec = CommandCenter()
check(cmd_dec.decoys_remaining == 3, "Should start with 3 decoys")
deployed = cmd_dec.deploy_decoy()
check(deployed == True, "Decoy deployment should succeed")
check(cmd_dec.decoys_remaining == 2, "Remaining decoys should be 2")
check(len(cmd_dec.active_decoys) == 1, "Active decoys list should have 1 decoy")
check(cmd_dec.active_decoys[0]["timer"] == 20, "Decoy duration should be 20s")

cmd_dec.deploy_decoy()
cmd_dec.deploy_decoy()
check(cmd_dec.decoys_remaining == 0, "Decoys remaining should be 0")
failed_deploy = cmd_dec.deploy_decoy()
check(failed_deploy == False, "Deployment should fail when 0 decoys remaining")

# Ticking update_world decrements decoy timer
cmd_dec.active_decoys = [{"id": "D1", "x": 10, "y": 10, "timer": 1, "active": True}]
cmd_dec.update_world()
check(len(cmd_dec.active_decoys) == 0, "Expired decoy should be removed from active_decoys")


print("\n=== 15. Tactical Event Bus ===")
cmd_bus = CommandCenter()
check(len(cmd_bus.event_bus) == 0, "Event bus should start empty")
evt = cmd_bus.emit_event("TEST_EVENT", detail="Test payload")
check(len(cmd_bus.event_bus) == 1, "Event bus should contain 1 event")
check(cmd_bus.event_bus[0]["type"] == "TEST_EVENT", "Event type should match")

# Verify DEFCON change event emission
icbm_defcon = ICBM(777)
icbm_defcon.status = "HOSTILE"
cmd_bus.contacts = [icbm_defcon]
cmd_bus.calculate_defcon()
check(any(e["type"] == "DEFCON_CHANGE" for e in cmd_bus.event_bus), "DEFCON_CHANGE should be emitted on DEFCON shift")


print("\n=== 16. RTAF Career Rank & XP Progression ===")
cmd_career = CommandCenter()
check(cmd_career.rank == "Airman", f"Initial rank should be 'Airman', got '{cmd_career.rank}'")
check(cmd_career.xp == 0, "Initial XP should be 0")

# Award XP below threshold
cmd_career.award_xp(200, "Minor action")
check(cmd_career.rank == "Airman", "Rank should remain Airman under 500 XP")

# Award XP to trigger promotion to Leading Airman (>= 500)
cmd_career.award_xp(350, "Intercept kill")
check(cmd_career.rank == "Leading Airman", f"Rank should be 'Leading Airman' at 550 XP, got '{cmd_career.rank}'")
check(any(e["type"] == "PROMOTION" and e["new_rank"] == "Leading Airman" for e in cmd_career.event_bus), "PROMOTION event should be emitted")

# High-tier threat XP and long-range bonus
icbm_target = ICBM(501)
icbm_target.distance_km = 450 # Long range >400 km
xp_before = cmd_career.xp
cmd_career.record_kill(icbm_target, "THAAD")
# ICBM = 1000 XP + 300 long range bonus = 1300 XP
check(cmd_career.xp == xp_before + 1300, f"ICBM kill >400km should award 1300 XP, got {cmd_career.xp - xp_before}")

# Airliner kill triggers immediate Court-Martial
airliner = Airliner(502)
cmd_career.record_kill(airliner, "SAM")
check(cmd_career.is_court_martialed == True, "Shooting down airliner must set is_court_martialed=True")
check(cmd_career.rank == "COURT-MARTIALED", f"Rank should become 'COURT-MARTIALED', got '{cmd_career.rank}'")
check(cmd_career.base_hp == 0, "Base HP should drop to 0 on Court-Martial")


print("\n=== 17. After-Action Report (AAR) ===")
cmd_aar = CommandCenter()
cmd_aar.award_xp(1500)
dummy_drone = Drone(601)
cmd_aar.record_kill(dummy_drone, "CIWS")
aar = cmd_aar.get_after_action_report()
check(isinstance(aar, dict), "AAR should return a dictionary")
check("outcome" in aar, "AAR dict must include 'outcome'")
check("rank" in aar, "AAR dict must include 'rank'")
check("kills" in aar and aar["kills"] == 1, "AAR kills should equal 1")
check("summary" in aar and "AFTER-ACTION REPORT" in aar["summary"], "AAR summary should include formatted header text")

# 18. Tactical Tech Upgrades Tree Tests
print("\n=== 18. Tactical Tech Upgrades Tree ===")
cmd_up = CommandCenter()
cmd_up.xp = 5000
check(len(cmd_up.unlocked_upgrades) == 0, "Upgrades should initially be empty")
ok, msg = cmd_up.unlock_upgrade("AESA_RANGE")
check(ok and "AESA_RANGE" in cmd_up.unlocked_upgrades, "AESA_RANGE should unlock successfully")
check(cmd_up.radar_max_km == 1000.0, "AESA_RANGE should increase radar_max_km to 1000.0")
check(cmd_up.xp == 3800, f"XP should be deducted: expected 3800, got {cmd_up.xp}")

# Test duplicate purchase
ok_dup, _ = cmd_up.unlock_upgrade("AESA_RANGE")
check(not ok_dup, "Duplicate upgrade purchase should be rejected")

# Test decoy pack
ok_dec, _ = cmd_up.unlock_upgrade("DECOY_PACK")
check(ok_dec and cmd_up.decoys_remaining == 6, f"DECOY_PACK should give +3 decoys: got {cmd_up.decoys_remaining}")

# Test insufficient XP
cmd_up.xp = 100
ok_fail, reason = cmd_up.unlock_upgrade("AESA_SEEKERS")
check(not ok_fail, "Purchase with insufficient XP should fail")

# 19. Mission Operations Campaign Engine Tests
print("\n=== 19. Mission Operations Campaign Engine ===")
cmd_mis = CommandCenter()
check(cmd_mis.mission_mgr.current.code == "OP-DEFENSE", "Default mission should be OP-DEFENSE")

# Test cycling to VIP Escort mission
vip_mis = cmd_mis.mission_mgr.cycle_mission(cmd_mis)
check(vip_mis.code == "OP-GUARDIAN", f"Cycled mission should be OP-GUARDIAN, got {vip_mis.code}")
check(any(c.id_code == "VIP-ROYAL" for c in cmd_mis.contacts), "VIPTransport should be present in contacts")

# Test cycling to Iron Swarm mission
swarm_mis = cmd_mis.mission_mgr.cycle_mission(cmd_mis)
check(swarm_mis.code == "OP-IRONSWARM", f"Cycled mission should be OP-IRONSWARM, got {swarm_mis.code}")

# Test cycling to Ghost Hunter mission
ghost_mis = cmd_mis.mission_mgr.cycle_mission(cmd_mis)
check(ghost_mis.code == "OP-GHOST", f"Cycled mission should be OP-GHOST, got {ghost_mis.code}")
check(len(ghost_mis.bombers) == 2, "Ghost Hunter should spawn 2 Stealth Bombers")

# 20. High-Fidelity Tactical Map & Neighbor Geodata Tests
print("\n=== 20. Real Tactical Map & Geodata Engine ===")
from map_manager import MapManager, latlon_to_km
map_test = MapManager()

# Thailand map validation
check("THA" in map_test.country_polys, "Thailand should be loaded in country polygons")
tha_rings = map_test.country_polys["THA"]
check(len(tha_rings) >= 15, f"Thailand should have mainland + major islands (expected >= 15 rings, got {len(tha_rings)})")
tha_total_pts = sum(len(r) for r in tha_rings)
check(tha_total_pts >= 1000, f"Thailand total polygon vertices should be high-res (>= 1000 pts, got {tha_total_pts})")

# Neighbor countries validation
expected_neighbors = ["MMR", "LAO", "KHM", "VNM", "MYS", "SGP", "IDN", "CHN"]
for iso in expected_neighbors:
    check(iso in map_test.country_polys, f"Neighbor country {iso} should be loaded")
    n_pts = sum(len(r) for r in map_test.country_polys[iso])
    check(n_pts >= 10, f"Neighbor {iso} should have valid geometry ({n_pts} pts)")

# Coastlines and land borders validation
check(len(map_test.coastlines_km) >= 100, f"Coastlines should have >= 100 segments, got {len(map_test.coastlines_km)}")
check(len(map_test.borders_km) >= 100, f"International land borders should have >= 100 segments, got {len(map_test.borders_km)}")

# Bangkok FIR / Thai ADIZ validation
check(len(map_test.adiz_km) >= 25, f"Bangkok FIR / Thai ADIZ should have >= 25 points, got {len(map_test.adiz_km)}")

# Airbases and Waypoints validation
check(len(map_test.airbases) >= 15, f"Strategic airbases and regional hubs should be >= 15, got {len(map_test.airbases)}")
check(any(b[2] == "BANGKOK (C2 HQ)" and abs(b[0]) < 0.1 and abs(b[1]) < 0.1 for b in map_test.airbases), "Bangkok C2 HQ must be at origin (0, 0)")
check(any("WING 1" in b[2] for b in map_test.airbases), "Wing 1 (Korat) airbase must be present")
check(any("WING 7" in b[2] for b in map_test.airbases), "Wing 7 (Surat Thani) airbase must be present")
check(any("WING 41" in b[2] for b in map_test.airbases), "Wing 41 (Chiang Mai) airbase must be present")

# Map Mode Cycling
m1, name1 = map_test.cycle_mode()
check(m1 == MapManager.MODE_SOVEREIGN_FOCUS, f"First cycle should be SOVEREIGN FOCUS, got {name1}")
m2, name2 = map_test.cycle_mode()
check(m2 == MapManager.MODE_MINIMAL, f"Second cycle should be MINIMAL, got {name2}")
m3, name3 = map_test.cycle_mode()
check(m3 == MapManager.MODE_OFF, f"Third cycle should be OFF, got {name3}")
m0, name0 = map_test.cycle_mode()
check(m0 == MapManager.MODE_FULL_TACTICAL, f"Fourth cycle should wrap to FULL TACTICAL, got {name0}")

# 21. CIWS Manual Engagement & Rapid CIWS Upgrade
print("\n=== 21. CIWS Manual Engagement & Upgrades ===")
cmd_ciws = CommandCenter()
ciws_tgt = Drone(999)
ciws_tgt.distance_km = 15.0
ciws_tgt.x_km = 0.0
ciws_tgt.y_km = 15.0
cmd_ciws.contacts.append(ciws_tgt)
initial_rounds = cmd_ciws.ammo["CIWS"]
cmd_ciws.manual_override_fire(ciws_tgt, "CIWS")
check(cmd_ciws.ammo["CIWS"] == initial_rounds - 1, f"CIWS manual fire should consume 1 magazine burst: {initial_rounds} -> {cmd_ciws.ammo['CIWS']}")
check(len(cmd_ciws.active_engagements) == 1, "CIWS engagement should be added to active_engagements list")
check(cmd_ciws.active_engagements[0].weapon_name == "CIWS", "Engagement weapon must be CIWS")

# Test Rapid CIWS Upgrade
cmd_ciws.unlocked_upgrades.add("RAPID_CIWS")
cmd_ciws.process_engagements() # Resolves engagement
check(ciws_tgt.status in ["CLEARED", "HOSTILE"], "Target status should be updated after engagement resolution")

# 22. AWACS and CAP Landing Recovery
print("\n=== 22. AWACS and CAP Landing Recovery ===")
cmd_recovery = CommandCenter()
# Initial launch through process_reloads()
cmd_recovery.process_reloads()
awacs_list = [c for c in cmd_recovery.contacts if isinstance(c, AWACS)]
check(len(awacs_list) >= 1, "AWACS should launch during process_reloads")
aw = awacs_list[0]
init_awacs = cmd_recovery.awacs_pool
# Simulate AWACS RTB landing
aw.state = "RTB"
aw.active = False
cmd_recovery.update_world()
check(cmd_recovery.awacs_pool == init_awacs + 1, f"AWACS pool should recover landed aircraft: {init_awacs} + 1 == {cmd_recovery.awacs_pool}")

# 23. Friendly Fire & Court-Martial Triggers
print("\n=== 23. Friendly Fire & Court-Martial Triggers ===")
cmd_cm = CommandCenter()
friendly_jet = Aircraft(888, friendly_weight=100)
friendly_jet.status = "FRIENDLY"
friendly_jet.is_friendly = True
friendly_jet.distance_km = 50.0
friendly_jet.x_km = 0.0
friendly_jet.y_km = 50.0
cmd_cm.contacts.append(friendly_jet)

# Call record_kill directly to verify Court-Martial mechanics on friendly fire
cmd_cm.record_kill(friendly_jet, "SAM")
check(cmd_cm.is_court_martialed == True, "Shooting down friendly aircraft must trigger Court-Martial")
check(cmd_cm.base_hp == 0, "Base HP must drop to 0 on Court-Martial")
check(any(e.get("type") == "COURT_MARTIAL" for e in cmd_cm.event_bus), "COURT_MARTIAL event must be dispatched to event bus")

# 24. Peak Altitude Masking Safety (3-tuple & 4-tuple support)
print("\n=== 24. Peak Altitude Masking Safety ===")
from targets import is_line_of_sight_masked
# Test that is_line_of_sight_masked handles both standard and legacy peak data without errors
masked_3tuple = is_line_of_sight_masked(-261.48, 641.16, 200)
check(isinstance(masked_3tuple, bool), "Masking evaluation with 3-tuple peaks should return a boolean")
unmasked_high = is_line_of_sight_masked(-261.48, 641.16, 15000)
check(unmasked_high == False, "High altitude target should not be masked")

# 25. Historical Events Retention for AAR
print("\n=== 25. Historical Events Retention for AAR ===")
cmd_aar = CommandCenter()
dummy_target = Drone(101)
cmd_aar.record_kill(dummy_target, "THAAD")
cmd_aar.airliners_safe += 1
cmd_aar.emit_event("AIRLINER_SAVED", id_code="TG-920")

# Emulate UI draining the event_bus
while cmd_aar.event_bus:
    ev = cmd_aar.event_bus.pop(0)

aar_report = cmd_aar.get_after_action_report()
check(aar_report["kills"] == 1, f"AAR kills must retain count even after event_bus is drained (expected 1, got {aar_report['kills']})")
check(aar_report["airliners_safe"] == 1, f"AAR airliners_safe must retain count (expected 1, got {aar_report['airliners_safe']})")
check(aar_report["total_events"] >= 1, f"AAR total_events must be recorded in historical_events (got {aar_report['total_events']})")
check("survival_time_sec" in aar_report, "AAR must contain survival_time_sec")
check("grade" in aar_report, "AAR must contain performance grade")

# 26. Tier 2 Black Ops Upgrade Tree
print("\n=== 26. Tier 2 Black Ops Upgrade Tree ===")
tier_2_keys = [
    "QUANTUM_SPACE_RADAR",
    "METEOR_HYPERSONIC",
    "IRON_BEAM_DIRECTED_ENERGY",
    "TACTICAL_EMP_BURST",
    "NANOTECH_AEGIS_SHIELD"
]

def get_t2_cost(cmd_obj, up_id):
    if hasattr(cmd_obj, "UPGRADE_TIER_2") and up_id in cmd_obj.UPGRADE_TIER_2:
        return cmd_obj.UPGRADE_TIER_2[up_id].get("cost", 0)
    if hasattr(cmd_obj, "UPGRADE_CATALOG") and up_id in cmd_obj.UPGRADE_CATALOG:
        return cmd_obj.UPGRADE_CATALOG[up_id].get("cost", 0)
    return 0

# --- 1. Incomplete Tier 1 gates Tier 2 ---
cmd_t2 = CommandCenter()
cmd_t2.xp = 50000

# 0 Tier 1 upgrades unlocked
check(hasattr(cmd_t2, "is_tier_1_complete") and cmd_t2.is_tier_1_complete is False,
      "is_tier_1_complete should be False with 0 upgrades unlocked")

# Unlock partial Tier 1 upgrades (2 of 5)
cmd_t2.unlock_upgrade("AESA_RANGE")
cmd_t2.unlock_upgrade("DOPPLER_FILTER")
check(hasattr(cmd_t2, "is_tier_1_complete") and cmd_t2.is_tier_1_complete is False,
      "is_tier_1_complete should be False when only 2/5 Tier 1 upgrades unlocked")

# Unlock 4 of 5
cmd_t2.unlock_upgrade("DECOY_PACK")
cmd_t2.unlock_upgrade("RAPID_CIWS")
check(hasattr(cmd_t2, "is_tier_1_complete") and cmd_t2.is_tier_1_complete is False,
      "is_tier_1_complete should be False when 4/5 Tier 1 upgrades unlocked")

# Attempt to purchase all Tier 2 upgrades while Tier 1 is incomplete
for t2_id in tier_2_keys:
    ok_lock, msg_lock = cmd_t2.unlock_upgrade(t2_id)
    check(not ok_lock, f"Attempting to buy {t2_id} when Tier 1 is incomplete must fail")
    check(msg_lock == "Locked: Complete Tier 1 First",
          f"Attempting to buy {t2_id} when Tier 1 incomplete must return 'Locked: Complete Tier 1 First' (got '{msg_lock}')")

# --- 2. Complete Tier 1 unlocks Tier 2 purchasability & catalog ---
cmd_t2.unlock_upgrade("AESA_SEEKERS")
check(hasattr(cmd_t2, "is_tier_1_complete") and cmd_t2.is_tier_1_complete is True,
      "is_tier_1_complete becomes True when all 5 Tier 1 upgrades are unlocked")

has_t2_catalog = hasattr(cmd_t2, "UPGRADE_TIER_2")
check(has_t2_catalog, "CommandCenter should have UPGRADE_TIER_2 catalog attribute")
if has_t2_catalog:
    check(all(k in cmd_t2.UPGRADE_TIER_2 for k in tier_2_keys),
          "UPGRADE_TIER_2 must contain all 5 Black Ops upgrades")
else:
    check(False, "UPGRADE_TIER_2 must contain all 5 Black Ops upgrades")

check(all(k in cmd_t2.UPGRADE_CATALOG for k in tier_2_keys),
      "UPGRADE_CATALOG must contain all 5 Tier 2 upgrades")

# --- 3. Purchase each Tier 2 upgrade with sufficient XP ---
cmd_t2.xp = 50000

# 3a. QUANTUM_SPACE_RADAR
cost_q = get_t2_cost(cmd_t2, "QUANTUM_SPACE_RADAR")
xp_before_q = cmd_t2.xp
ok_q, msg_q = cmd_t2.unlock_upgrade("QUANTUM_SPACE_RADAR")
check(ok_q is True and "QUANTUM_SPACE_RADAR" in cmd_t2.unlocked_upgrades,
      "QUANTUM_SPACE_RADAR should unlock successfully")
check(cost_q > 0 and cmd_t2.xp == xp_before_q - cost_q,
      f"QUANTUM_SPACE_RADAR should deduct {cost_q} XP (got xp={cmd_t2.xp}, expected {xp_before_q - cost_q})")

# Terrain masking bypass test
masked_cm = CruiseMissile(991)
masked_cm.x_km = -261.48
masked_cm.y_km = 641.16
masked_cm.distance_km = math.hypot(-261.48, 641.16)
masked_cm.altitude_ft = 200
cmd_t2.contacts = []
cmd_t2.unseen_contacts = [masked_cm]
cmd_t2.emcon_mode = "ACTIVE"
cmd_t2.detect_airspace()
check(masked_cm in cmd_t2.contacts,
      "QUANTUM_SPACE_RADAR enables quantum detection bypassing terrain masking into contacts")

# 3b. METEOR_HYPERSONIC
cmd_t2.max_ammo["FIGHTER"] = 15
cmd_t2.ammo["FIGHTER"] = 5  # Depleted
cost_m = get_t2_cost(cmd_t2, "METEOR_HYPERSONIC")
xp_before_m = cmd_t2.xp
ok_m, msg_m = cmd_t2.unlock_upgrade("METEOR_HYPERSONIC")
check(ok_m is True and "METEOR_HYPERSONIC" in cmd_t2.unlocked_upgrades,
      "METEOR_HYPERSONIC should unlock successfully")
check(cost_m > 0 and cmd_t2.xp == xp_before_m - cost_m,
      f"METEOR_HYPERSONIC should deduct {cost_m} XP (got xp={cmd_t2.xp}, expected {xp_before_m - cost_m})")
check(cmd_t2.max_ammo["FIGHTER"] == 25,
      f"METEOR_HYPERSONIC should increase fighter max ammo by +10 (expected 25, got {cmd_t2.max_ammo['FIGHTER']})")
check(cmd_t2.ammo["FIGHTER"] == 25,
      f"METEOR_HYPERSONIC should restore fighter ammo to max 25 (got {cmd_t2.ammo['FIGHTER']})")

# 3c. IRON_BEAM_DIRECTED_ENERGY
cost_ib = get_t2_cost(cmd_t2, "IRON_BEAM_DIRECTED_ENERGY")
xp_before_ib = cmd_t2.xp
ok_ib, msg_ib = cmd_t2.unlock_upgrade("IRON_BEAM_DIRECTED_ENERGY")
check(ok_ib is True and "IRON_BEAM_DIRECTED_ENERGY" in cmd_t2.unlocked_upgrades,
      "IRON_BEAM_DIRECTED_ENERGY should unlock successfully")
check(cost_ib > 0 and cmd_t2.xp == xp_before_ib - cost_ib,
      f"IRON_BEAM_DIRECTED_ENERGY should deduct {cost_ib} XP (got xp={cmd_t2.xp}, expected {xp_before_ib - cost_ib})")
ciws_range = getattr(cmd_t2, 'ciws_engage_range', getattr(cmd_t2, 'ciws_range_km', None))
check(ciws_range == 30.0,
      f"IRON_BEAM_DIRECTED_ENERGY should increase CIWS engage range to 30km (got {ciws_range})")

# 3d. TACTICAL_EMP_BURST
cost_emp = get_t2_cost(cmd_t2, "TACTICAL_EMP_BURST")
xp_before_emp = cmd_t2.xp
ok_emp, msg_emp = cmd_t2.unlock_upgrade("TACTICAL_EMP_BURST")
check(ok_emp is True and "TACTICAL_EMP_BURST" in cmd_t2.unlocked_upgrades,
      "TACTICAL_EMP_BURST should unlock successfully")
check(cost_emp > 0 and cmd_t2.xp == xp_before_emp - cost_emp,
      f"TACTICAL_EMP_BURST should deduct {cost_emp} XP (got xp={cmd_t2.xp}, expected {xp_before_emp - cost_emp})")

has_emp_burst = hasattr(cmd_t2, "trigger_emp_burst")
check(has_emp_burst, "CommandCenter should provide trigger_emp_burst() method")

emp_ghost1 = EWGhostTrack(993)
emp_ghost2 = GhostTrack(994)
emp_arm = AntiRadiationMissile(995)
emp_arm.seeker_locked = True
emp_drone = Drone(996)
emp_drone.status = "HOSTILE"
cmd_t2.contacts = [emp_ghost1, emp_ghost2, emp_arm, emp_drone]

if has_emp_burst:
    cmd_t2.trigger_emp_burst()

active_ghosts = [c for c in cmd_t2.contacts if isinstance(c, (GhostTrack, EWGhostTrack)) and c.active]
check(len(active_ghosts) == 0, "trigger_emp_burst() should clear all EW ghost tracks")
check(emp_arm.seeker_locked is False, "trigger_emp_burst() should disable ARM seeker locks")
check(emp_drone in cmd_t2.contacts and emp_drone.active, "trigger_emp_burst() should preserve non-ghost targets")

# 3e. NANOTECH_AEGIS_SHIELD
cmd_t2.base_hp = 35  # Damaged base
cost_nano = get_t2_cost(cmd_t2, "NANOTECH_AEGIS_SHIELD")
xp_before_nano = cmd_t2.xp
ok_nano, msg_nano = cmd_t2.unlock_upgrade("NANOTECH_AEGIS_SHIELD")
check(ok_nano is True and "NANOTECH_AEGIS_SHIELD" in cmd_t2.unlocked_upgrades,
      "NANOTECH_AEGIS_SHIELD should unlock successfully")
check(cost_nano > 0 and cmd_t2.xp == xp_before_nano - cost_nano,
      f"NANOTECH_AEGIS_SHIELD should deduct {cost_nano} XP (got xp={cmd_t2.xp}, expected {xp_before_nano - cost_nano})")
check(cmd_t2.base_hp == 150,
      f"NANOTECH_AEGIS_SHIELD should restore base_hp to 150 (got {cmd_t2.base_hp})")
max_base_hp = getattr(cmd_t2, 'max_base_hp', None)
check(max_base_hp == 150,
      f"NANOTECH_AEGIS_SHIELD should set max_base_hp to 150 (got {max_base_hp})")

# --- 4. Duplicate purchase of Tier 2 upgrades rejected ---
ok_dup_t2, msg_dup_t2 = cmd_t2.unlock_upgrade("QUANTUM_SPACE_RADAR")
check(ok_dup_t2 is False, "Duplicate Tier 2 upgrade purchase should be rejected")
check(msg_dup_t2 == "Already Unlocked",
      f"Duplicate Tier 2 purchase should return 'Already Unlocked', got '{msg_dup_t2}'")

# --- 5. Buying Tier 2 with insufficient XP fails ---
cmd_low_xp = CommandCenter()
cmd_low_xp.unlocked_upgrades.update([
    "AESA_RANGE", "DOPPLER_FILTER", "DECOY_PACK", "RAPID_CIWS", "AESA_SEEKERS"
])
cmd_low_xp.xp = 10  # Insufficient XP
ok_low_t2, msg_low_t2 = cmd_low_xp.unlock_upgrade("QUANTUM_SPACE_RADAR")
check(ok_low_t2 is False, "Buying Tier 2 upgrade with insufficient XP should fail")
check("Insufficient XP" in msg_low_t2,
      f"Failure message should indicate insufficient XP (got '{msg_low_t2}')")
check("QUANTUM_SPACE_RADAR" not in cmd_low_xp.unlocked_upgrades,
      "Upgrade should not be in unlocked_upgrades when purchase fails due to XP")

print("\n=== 27. AI Interceptor Prioritization & EW Suppression ===")

# --- 1. Strategic EW Threat Score Bonus ---
normal_plane = Aircraft(9901)
normal_plane.status = "HOSTILE"
normal_plane.speed_mach = 0.9
normal_plane.distance_km = 600.0
normal_plane.altitude_ft = 30000
normal_plane.rcs = 3.0
normal_plane.is_heavy_ew = False
normal_plane.type_name = "Su-30MKM Flanker"
score_normal = normal_plane.calculate_threat_score()

ew_plane = Aircraft(9902)
ew_plane.is_friendly = False
ew_plane.status = "HOSTILE"
ew_plane.speed_mach = 0.9
ew_plane.distance_km = 600.0
ew_plane.altitude_ft = 30000
ew_plane.rcs = 3.0
ew_plane.is_heavy_ew = True
ew_plane.type_name = "EA-18G Growler (HEAVY EW)"
score_ew = ew_plane.calculate_threat_score()

check(score_ew >= score_normal + 800,
      f"EW platform threat score should include >=800 EW strategic bonus: got {score_ew} vs normal {score_normal}")

# --- 2. Proactive AI Fighter Scramble for Unengaged Standoff Jammers ---
cmd_ai = CommandCenter()
cmd_ai.ammo["FIGHTER"] = 15
cmd_ai.active_engagements = []

# Insert hostile EW contact at standoff distance (600 km)
cmd_ai.contacts = [ew_plane]
ew_plane.active = True
ew_plane.status = "HOSTILE"

check(hasattr(cmd_ai, 'process_ew_interceptor_defense'),
      "CommandCenter should implement process_ew_interceptor_defense()")
if hasattr(cmd_ai, 'process_ew_interceptor_defense'):
    scrambled = cmd_ai.process_ew_interceptor_defense()
    check(scrambled is True, "process_ew_interceptor_defense should return True when scrambling")
    check(cmd_ai.ammo["FIGHTER"] == 14,
          f"Fighter ammo should decrement by 1: expected 14, got {cmd_ai.ammo['FIGHTER']}")
    check(len(cmd_ai.active_engagements) == 1,
          f"Active engagements should have 1 fighter sortie: got {len(cmd_ai.active_engagements)}")
    check(cmd_ai.active_engagements[0].target == ew_plane,
          "Scrambled fighter must target the active EW jammer")
    check(ew_plane.status in ["ENGAGING", "INTERCEPTING"],
          f"EW plane status should be ENGAGING or INTERCEPTING, got {ew_plane.status}")

    # --- 3. Anti-Duplicate: Do not double scramble while already engaged ---
    scrambled_again = cmd_ai.process_ew_interceptor_defense()
    check(scrambled_again is False, "Should NOT double-scramble fighters against already-targeted jammer")
    check(cmd_ai.ammo["FIGHTER"] == 14,
          f"Fighter ammo should remain 14 on double-scramble attempt: got {cmd_ai.ammo['FIGHTER']}")
    check(len(cmd_ai.active_engagements) == 1,
          "Active engagements count should remain 1")

# --- 4. Ammo Exhaustion Respect ---
cmd_empty = CommandCenter()
cmd_empty.ammo["FIGHTER"] = 0
ew_plane_2 = Aircraft(9903)
ew_plane_2.status = "HOSTILE"
ew_plane_2.is_heavy_ew = True
ew_plane_2.type_name = "EA-18G Growler (HEAVY EW)"
cmd_empty.contacts = [ew_plane_2]

if hasattr(cmd_empty, 'process_ew_interceptor_defense'):
    scrambled_empty = cmd_empty.process_ew_interceptor_defense()
    check(scrambled_empty is False, "Should NOT scramble when FIGHTER ammo is 0")
    check(len(cmd_empty.active_engagements) == 0,
          "No engagements should be created when out of fighter ammo")

# --- 5. Realistic Standoff Loiter & Bingo Fuel Egress ---
ew_loiter = Aircraft(9904)
ew_loiter.status = "HOSTILE"
ew_loiter.is_heavy_ew = True
ew_loiter.type_name = "EA-18G Growler (HEAVY EW)"
ew_loiter.distance_km = 450.0
cmd_loiter = CommandCenter()
cmd_loiter.contacts = [ew_loiter]

check(hasattr(ew_loiter, 'loiter_timer'),
      "EW aircraft should have a loiter_timer attribute for realistic mission duration")
if hasattr(ew_loiter, 'loiter_timer'):
    ew_loiter.loiter_timer = 1  # Force immediate bingo fuel expiration
    hp_before_egress = cmd_loiter.base_hp
    # Process movement / tick
    ew_loiter.move(cmd_loiter)
    check(ew_loiter.active is False, "EW aircraft should deactivate / egress on bingo fuel")
    check(cmd_loiter.base_hp == hp_before_egress,
          "Egressing EW aircraft must NOT damage base HP")

# --- 6. Engagement Resolution: Interceptor splashes jammer ---
if hasattr(cmd_ai, 'active_engagements') and len(cmd_ai.active_engagements) > 0:
    cmd_ai.active_engagements[0].time_to_impact = 1
    kills_before = cmd_ai.kills
    old_f16_hit = GameConfig.HIT_CHANCE_F16
    try:
        GameConfig.HIT_CHANCE_F16 = 1.0  # Guarantee hit for deterministic test
        cmd_ai.process_engagements()
        check(ew_plane.active is False or ew_plane.status == "CLEARED",
              "Interceptor must neutralize active EW jammer upon missile impact")
        check(cmd_ai.kills == kills_before + 1,
              f"Kills count should increment: expected {kills_before + 1}, got {cmd_ai.kills}")
    finally:
        GameConfig.HIT_CHANCE_F16 = old_f16_hit

print("\n=== 28. Anti-Jammer Electronic Counter-Countermeasures (ECCM) ===")

cmd_eccm = CommandCenter()

# --- 1. Radar Burn-Through Mode ([F]) ---
check(hasattr(cmd_eccm, 'burn_through_active'), "CommandCenter should have burn_through_active state")
check(hasattr(cmd_eccm, 'toggle_burn_through'), "CommandCenter should implement toggle_burn_through()")

if hasattr(cmd_eccm, 'toggle_burn_through'):
    initial_bt = cmd_eccm.burn_through_active
    new_state, msg_bt = cmd_eccm.toggle_burn_through()
    check(new_state != initial_bt, f"toggle_burn_through should toggle state: {initial_bt} -> {new_state}")
    check(cmd_eccm.burn_through_active is True, "burn_through_active should be True after toggle")
    
    # Check jamming factor under burn-through
    ew_bogey = Aircraft(9910)
    ew_bogey.is_heavy_ew = True
    ew_bogey.status = "HOSTILE"
    ew_bogey.bearing = 90.0
    
    target_masked = Aircraft(9911)
    target_masked.bearing = 92.0 # Inside the 10 degree strobe cone
    
    factor_active = cmd_eccm.get_jamming_factor(target_masked, [ew_bogey])
    check(factor_active >= 1.5, f"Burn-through mode should boost factor to >=1.5 (got {factor_active})")
    
    # Toggle off
    cmd_eccm.toggle_burn_through()
    factor_normal = cmd_eccm.get_jamming_factor(target_masked, [ew_bogey])
    check(factor_normal <= 0.31, f"Normal jamming factor should be 0.3 without burn-through (got {factor_normal})")

# --- 2. Home-On-Jam (HOJ) Missile Guidance Doctrine ([H]) ---
check(hasattr(cmd_eccm, 'hoj_mode'), "CommandCenter should have hoj_mode state")
check(hasattr(cmd_eccm, 'toggle_hoj_mode'), "CommandCenter should implement toggle_hoj_mode()")

if hasattr(cmd_eccm, 'toggle_hoj_mode'):
    check(cmd_eccm.hoj_mode is False, "hoj_mode should default to False (STANDBY)")
    state_hoj, msg_hoj = cmd_eccm.toggle_hoj_mode()
    check(cmd_eccm.hoj_mode is True, "hoj_mode should be True after toggle")
    
    # Test SAM engagement range extension against radiating jammer
    standoff_jammer = Aircraft(9912)
    standoff_jammer.is_heavy_ew = True
    standoff_jammer.status = "HOSTILE"
    standoff_jammer.distance_km = 300.0 # Standard SAM range is only 200 km!
    standoff_jammer.altitude_ft = 35000
    cmd_eccm.contacts = [standoff_jammer]
    cmd_eccm.ammo["SAM"] = 10
    
    # In HOJ mode, SAM can engage radiating jammer out to 350 km
    check(cmd_eccm.can_engage_with_sam(standoff_jammer) is True,
          "HOJ mode should permit SAM engagement out to 350 km against radiating jammer")
    
    # When HOJ is disabled, SAM cannot engage beyond 200 km
    cmd_eccm.hoj_mode = False
    check(cmd_eccm.can_engage_with_sam(standoff_jammer) is False,
          "Without HOJ, SAM cannot engage target beyond 200 km")

# --- 3. Passive ESM Cross-Bearing Triangulation (Saab 340 AEW&C) ---
cmd_esm = CommandCenter()
jam_target = Aircraft(9913)
jam_target.is_heavy_ew = True
jam_target.status = "HOSTILE"
jam_target.x_km = 350.0
jam_target.y_km = 200.0
jam_target.bearing = math.degrees(math.atan2(350.0, 200.0))
cmd_esm.contacts = [jam_target]

# Without AWACS, no triangulation
check(hasattr(cmd_esm, 'process_esm_triangulation'),
      "CommandCenter should implement process_esm_triangulation()")
if hasattr(cmd_esm, 'process_esm_triangulation'):
    cmd_esm.process_esm_triangulation()
    check(getattr(jam_target, 'is_esm_triangulated', False) is False,
          "Without AWACS, jammer should NOT be triangulated")
    
    # Deploy active AWACS
    awacs_bird = AWACS(9914)
    awacs_bird.active = True
    awacs_bird.set_xy(100.0, -250.0) # Loitering over Gulf of Thailand
    cmd_esm.contacts.append(awacs_bird)
    
    cmd_esm.process_esm_triangulation()
    check(getattr(jam_target, 'is_esm_triangulated', False) is True,
          "With active AWACS, jammer should be marked as triangulated (is_esm_triangulated=True)")
    check(hasattr(jam_target, 'esm_fix_coord') and jam_target.esm_fix_coord == (350.0, 200.0),
          "Triangulated jammer should record exact esm_fix_coord (350, 200)")

    # Non-radiating contacts (civilian airliner) should NOT be ESM-triangulated
    airliner = Airliner(9915)
    airliner.active = True
    cmd_esm.contacts.append(airliner)
    cmd_esm.process_esm_triangulation()
    check(getattr(airliner, 'is_esm_triangulated', False) is False,
          "Civilian airliner should NOT be marked as ESM triangulated")

# --- 4. Burn-Through Timer Countdown & Auto-Expiration in update_world ---
cmd_timer = CommandCenter()
cmd_timer.toggle_burn_through()
check(cmd_timer.burn_through_active is True and cmd_timer.burn_through_timer == 20,
      "Burn-through timer should initialize to 20 seconds")
cmd_timer.burn_through_timer = 1
cmd_timer.update_world()
check(cmd_timer.burn_through_active is False,
      "Burn-through should automatically deactivate when timer reaches 0")

# --- 5. Manual SAM Override Range Enforcement with HOJ ---
cmd_sam_range = CommandCenter()
long_range_jammer = Aircraft(9916)
long_range_jammer.is_heavy_ew = True
long_range_jammer.status = "HOSTILE"
long_range_jammer.x_km = 280.0
long_range_jammer.y_km = 0.0
long_range_jammer.distance_km = 280.0
long_range_jammer.altitude_ft = 30000
cmd_sam_range.contacts = [long_range_jammer]
cmd_sam_range.ammo["SAM"] = 5

# Without HOJ, firing SAM at 280km must be rejected
cmd_sam_range.hoj_mode = False
cmd_sam_range.manual_override_fire(long_range_jammer, "SAM")
check(cmd_sam_range.ammo["SAM"] == 5,
      "SAM ammo should NOT be consumed when target is out of range without HOJ")
check(len(cmd_sam_range.active_engagements) == 0,
      "No engagement should be created when SAM is fired out of range without HOJ")

# With HOJ enabled, firing SAM at 280km must succeed
cmd_sam_range.toggle_hoj_mode()
cmd_sam_range.manual_override_fire(long_range_jammer, "SAM")
check(cmd_sam_range.ammo["SAM"] == 4,
      "SAM ammo should be consumed when firing at 280km with HOJ active")
check(len(cmd_sam_range.active_engagements) == 1,
      "Active engagement should be created when firing SAM with HOJ active")

print("\n=== 29. Controllable AWACS Operations & Sensor Fusion ===")

# --- 1. Initial State & Configuration ---
awacs = AWACS(9920)
check(awacs.state == "TRANSIT_TO_STATION",
      f"AWACS initial state should be TRANSIT_TO_STATION, got {awacs.state}")
check(awacs.orbit_center_x == 20.0 and awacs.orbit_center_y == -150.0,
      f"AWACS default orbit center should be (20.0, -150.0), got ({getattr(awacs, 'orbit_center_x', None)}, {getattr(awacs, 'orbit_center_y', None)})")
check(getattr(awacs, 'orbit_radius_km', None) == 50,
      f"AWACS initial orbit_radius_km should be 50, got {getattr(awacs, 'orbit_radius_km', None)}")

# --- 2. Retask Station ---
check(hasattr(awacs, 'retask_station'), "AWACS should implement retask_station(new_x, new_y)")
if hasattr(awacs, 'retask_station'):
    awacs.retask_station(new_x=120.0, new_y=250.0)
    check(awacs.orbit_center_x == 120.0 and awacs.orbit_center_y == 250.0,
          f"AWACS retask_station should set orbit center to (120.0, 250.0), got ({awacs.orbit_center_x}, {awacs.orbit_center_y})")
    check(awacs.state == "TRANSIT_TO_STATION",
          f"AWACS retask_station should set state to TRANSIT_TO_STATION, got {awacs.state}")
    expected_heading = (math.degrees(math.atan2(120.0 - awacs.x_km, 250.0 - awacs.y_km)) + 360) % 360
    check(abs(awacs.heading - expected_heading) < 1.0,
          f"AWACS heading should point towards new waypoint {expected_heading:.1f}, got {awacs.heading:.1f}")
else:
    check(False, "awacs.retask_station missing: cannot verify orbit center (120.0, 250.0)")
    check(False, "awacs.retask_station missing: cannot verify state TRANSIT_TO_STATION")
    check(False, "awacs.retask_station missing: cannot verify heading recalculation")

# --- 3. Set Orbit Radius ---
check(hasattr(awacs, 'set_orbit_radius'), "AWACS should implement set_orbit_radius(radius_km)")
if hasattr(awacs, 'set_orbit_radius'):
    awacs.set_orbit_radius(radius_km=75)
    check(getattr(awacs, 'orbit_radius_km', None) == 75,
          f"AWACS orbit_radius_km should be 75 after set_orbit_radius(75), got {getattr(awacs, 'orbit_radius_km', None)}")
else:
    check(False, "awacs.set_orbit_radius missing: cannot verify orbit_radius_km = 75")

# --- 4. Order RTB ---
check(hasattr(awacs, 'order_rtb'), "AWACS should implement order_rtb()")
if hasattr(awacs, 'order_rtb'):
    awacs.order_rtb()
    check(awacs.state == "RTB", f"AWACS order_rtb should set state to RTB, got {awacs.state}")
    expected_rtb_heading = (math.degrees(math.atan2(awacs.home_x - awacs.x_km, awacs.home_y - awacs.y_km)) + 360) % 360
    check(abs(awacs.heading - expected_rtb_heading) < 1.0,
          f"AWACS heading should point towards home base {expected_rtb_heading:.1f}, got {awacs.heading:.1f}")
else:
    check(False, "awacs.order_rtb missing: cannot verify state RTB")
    check(False, "awacs.order_rtb missing: cannot verify heading towards home base")

# --- 5. Sensor Coverage with Retasked AWACS in CommandCenter ---
cmd_coverage = CommandCenter()
retasked_awacs = AWACS(9921)
retasked_awacs.set_xy(300.0, 100.0)
retasked_awacs.active = True
cmd_coverage.contacts = [retasked_awacs]

low_contact = CruiseMissile(9922, distance_km=370.0)
low_contact.x_km = 350.0
low_contact.y_km = 120.0
low_contact.distance_km = 370.0
low_contact.altitude_ft = 200

dist_to_awacs = math.hypot(low_contact.x_km - retasked_awacs.x_km, low_contact.y_km - retasked_awacs.y_km)
check(abs(dist_to_awacs - 53.85) < 0.1,
      f"Distance between contact and AWACS should be ~53.8 km, got {dist_to_awacs:.1f}")
check(cmd_coverage.is_in_sensor_coverage(low_contact) is True,
      "cmd.is_in_sensor_coverage(contact) should return True when contact is ~53.8 km from AWACS (<= 400 km)")

retasked_awacs.set_xy(-200.0, -300.0)
dist_far = math.hypot(low_contact.x_km - retasked_awacs.x_km, low_contact.y_km - retasked_awacs.y_km)
check(dist_far > 400.0,
      f"AWACS repositioned far away: distance should be > 400 km, got {dist_far:.1f}")
check(cmd_coverage.is_in_sensor_coverage(low_contact) is False,
      "cmd.is_in_sensor_coverage(contact) should return False when AWACS is > 400 km away")

print("\n=== 30. Tactical Audio Engine & Alarm Cooldown Logic ===")

# --- 1. SoundManager Alarm State & Auto-Cutoff ---
sound_mgr = SoundManager.get_instance()
check(hasattr(sound_mgr, 'start_alarm'), "SoundManager should have start_alarm() method")
check(hasattr(sound_mgr, 'stop_alarm'), "SoundManager should have stop_alarm() method")

sig_alarm = inspect.signature(sound_mgr.start_alarm)
check('timeout_sec' in sig_alarm.parameters,
      "SoundManager.start_alarm should accept timeout_sec parameter")

check(hasattr(sound_mgr, 'is_alarm_active'),
      "SoundManager should have is_alarm_active property")

if hasattr(sound_mgr, 'is_alarm_active') and 'timeout_sec' in sig_alarm.parameters:
    sound_mgr.start_alarm(timeout_sec=5.0)
    check(sound_mgr.is_alarm_active is True,
          "sound_mgr.is_alarm_active should be True when start_alarm(timeout_sec=5.0) is called")
    sound_mgr.stop_alarm()
    check(sound_mgr.is_alarm_active is False,
          "sound_mgr.is_alarm_active should become False when stop_alarm() is called")
else:
    check(False, "sound_mgr.start_alarm(timeout_sec=5.0): missing timeout_sec or is_alarm_active")
    check(False, "sound_mgr.stop_alarm(): cannot verify is_alarm_active becomes False")

# --- 2. Voice Callout Debounce ---
check(hasattr(sound_mgr, 'radio_callout'), "SoundManager should have radio_callout() method")
sig_callout = inspect.signature(sound_mgr.radio_callout)
check('category' in sig_callout.parameters and 'debounce_sec' in sig_callout.parameters,
      "SoundManager.radio_callout should accept category and debounce_sec parameters")

if 'category' in sig_callout.parameters and 'debounce_sec' in sig_callout.parameters:
    # Clear worker queue
    while not sound_mgr._radio_queue.empty():
        try:
            sound_mgr._radio_queue.get_nowait()
        except Exception:
            break

    res1 = sound_mgr.radio_callout("Vampire! Vampire inbound!", category="VAMPIRE", debounce_sec=1.5)
    res2 = sound_mgr.radio_callout("Vampire! Vampire inbound!", category="VAMPIRE", debounce_sec=1.5)
    q_items = sound_mgr._radio_queue.qsize()
    check(res2 is False or q_items <= 1,
          f"Duplicate radio_callout within debounce window should be dropped/debounced (res2={res2}, queue size={q_items})")
else:
    check(False, "sound_mgr.radio_callout missing category/debounce_sec: duplicate callout debounce not verified")

# --- 3. Synthesized Missile Launch Sound ---
launch_audio = synth_missile_launch()
check(isinstance(launch_audio, np.ndarray),
      "synth_missile_launch should return a numpy ndarray")
check(launch_audio.ndim == 2 and launch_audio.shape[1] == 2,
      f"synth_missile_launch shape should be (N, 2), got {launch_audio.shape}")
max_amplitude = float(np.max(np.abs(launch_audio)))
check(max_amplitude <= 1.0,
      f"synth_missile_launch max absolute amplitude should be <= 1.0, got {max_amplitude:.4f}")
sound_duration = len(launch_audio) / 44100.0
check(sound_duration > 0.5,
      f"synth_missile_launch duration should be > 0.5s, got {sound_duration:.2f}s")

print("\n=== 31. Visual Effects Subsystem & EMP Shockwave Ring ===")
from visual_effects import VFXManager, ShockwaveRing
vfx = VFXManager()
check(hasattr(vfx, 'add_shockwave'), "VFXManager should have add_shockwave method")
if hasattr(vfx, 'add_shockwave'):
    sw = vfx.add_shockwave(x=100.0, y=100.0, max_radius=600.0, color=(180, 80, 255))
    check(isinstance(sw, ShockwaveRing), "add_shockwave should return a ShockwaveRing instance")
    check(sw.color == (180, 80, 255), f"Shockwave color should be (180, 80, 255), got {sw.color}")
    check(sw.max_radius == 600.0, f"Shockwave max_radius should be 600.0, got {sw.max_radius}")
    check(sw in vfx.shockwaves, "Shockwave should be added to vfx.shockwaves")
    
    vfx.update(dt=0.2)
    check(sw.radius > sw.start_radius, "Shockwave radius should increase after update(dt=0.2)")
    
    vfx.update(dt=1.0)
    check(sw not in vfx.shockwaves, "Expired shockwave should be pruned from vfx.shockwaves after update(dt=1.0)")
else:
    check(False, "vfx.add_shockwave missing: cannot verify shockwave properties")

print("\n=== 32. Simulation Profiles (Spectator vs Player) ===")
from profiles import SimulationProfile, SPECTATOR_PROFILE, PLAYER_PROFILE

_gc_snapshot_before = {k: getattr(GameConfig, k) for k in
                        ("WAVE_CHANCE", "WAVE_SIZE_MIN", "WAVE_SIZE_MAX",
                         "WAVE_COOLDOWN_INITIAL", "WAVE_COOLDOWN_AFTER")}

_spectator_cfg = SPECTATOR_PROFILE.resolve_config()
_player_cfg = PLAYER_PROFILE.resolve_config()

_gc_snapshot_after = {k: getattr(GameConfig, k) for k in
                       ("WAVE_CHANCE", "WAVE_SIZE_MIN", "WAVE_SIZE_MAX",
                        "WAVE_COOLDOWN_INITIAL", "WAVE_COOLDOWN_AFTER")}

check(_gc_snapshot_before == _gc_snapshot_after,
      "Reading SimulationProfile configs must not mutate GameConfig class attributes")

check(SPECTATOR_PROFILE.autonomous_weapons is True and SPECTATOR_PROFILE.player_input_enabled is False,
      "SPECTATOR_PROFILE should be autonomous and not accept player input")
check(PLAYER_PROFILE.autonomous_weapons is False and PLAYER_PROFILE.player_input_enabled is True,
      "PLAYER_PROFILE should require player input and not be autonomous")

check(_spectator_cfg["WAVE_CHANCE"] > _player_cfg["WAVE_CHANCE"],
      "SPECTATOR_PROFILE wave_chance should exceed PLAYER_PROFILE wave_chance")
check(_spectator_cfg["WAVE_SIZE_MAX"] > _player_cfg["WAVE_SIZE_MAX"],
      "SPECTATOR_PROFILE wave_size_max should exceed PLAYER_PROFILE wave_size_max")
check(_spectator_cfg["WAVE_SIZE_MIN"] >= _player_cfg["WAVE_SIZE_MIN"],
      "SPECTATOR_PROFILE wave_size_min should be >= PLAYER_PROFILE wave_size_min")
check(_spectator_cfg["WAVE_COOLDOWN_INITIAL"] < _player_cfg["WAVE_COOLDOWN_INITIAL"],
      "SPECTATOR_PROFILE should have shorter initial wave cooldown than PLAYER_PROFILE")
check(_spectator_cfg["WAVE_COOLDOWN_AFTER"] < _player_cfg["WAVE_COOLDOWN_AFTER"],
      "SPECTATOR_PROFILE should have shorter repeat wave cooldown than PLAYER_PROFILE")

_default_profile = SimulationProfile(name="TEST_DEFAULT")
check(_default_profile.resolve_config()["WAVE_CHANCE"] == GameConfig.WAVE_CHANCE,
      "A SimulationProfile with no overrides should fall back to GameConfig.WAVE_CHANCE")

print("\n=== 33. Cinematic Camera Director ===")
from camera_director import CameraDirector

cam = CameraDirector(seconds_per_leg=2.0)
samples = [cam.values]
for _ in range(10):
    cam.update(0.15)
    samples.append(cam.values)

check(all(all(math.isfinite(v) for v in s) for s in samples),
      "CameraDirector.update should never produce NaN/inf camera values")

distinct_positions = len({(round(x, 3), round(y, 3)) for x, y, _z in samples})
check(distinct_positions > 1,
      "CameraDirector.update should produce smoothly changing (non-identical) positions over time")

check(samples[0] != samples[-1],
      "CameraDirector values after several updates should differ from the initial values")

print("\n=== 34. CommandCenter Profile-Driven Spawn & Weapon Autonomy ===")
from profiles import PLAYER_PROFILE as _PLAYER_PROFILE, SPECTATOR_PROFILE as _SPECTATOR_PROFILE

_gc_snapshot_cc_before = {k: getattr(GameConfig, k) for k in
                           ("WAVE_CHANCE", "WAVE_SIZE_MIN", "WAVE_SIZE_MAX",
                            "WAVE_COOLDOWN_INITIAL", "WAVE_COOLDOWN_AFTER")}

# (a) Spectator produces strictly larger wave pressure than Player (seeded for determinism)
random.seed(1234)
spec_cmd = CommandCenter(profile=_SPECTATOR_PROFILE)
spec_cmd.tick_count = 400  # WARTIME phase, waves enabled
spec_cmd.wave_cooldown = 0
spec_sizes = []
for _ in range(40):
    before = len(spec_cmd.unseen_contacts)
    spec_cmd.detect_airspace()
    spec_sizes.append(len(spec_cmd.unseen_contacts) - before)
    spec_cmd.tick_count += 1

random.seed(1234)
plyr_cmd = CommandCenter(profile=_PLAYER_PROFILE)
plyr_cmd.tick_count = 400
plyr_cmd.wave_cooldown = 0
plyr_sizes = []
for _ in range(40):
    before = len(plyr_cmd.unseen_contacts)
    plyr_cmd.detect_airspace()
    plyr_sizes.append(len(plyr_cmd.unseen_contacts) - before)
    plyr_cmd.tick_count += 1

check(sum(spec_sizes) > sum(plyr_sizes),
      f"CommandCenter(SPECTATOR_PROFILE) should spawn more contacts over time than PLAYER_PROFILE "
      f"(spectator={sum(spec_sizes)}, player={sum(plyr_sizes)})")

# (b) GameConfig is still unmutated after constructing CommandCenters with both profiles
_gc_snapshot_cc_after = {k: getattr(GameConfig, k) for k in
                          ("WAVE_CHANCE", "WAVE_SIZE_MIN", "WAVE_SIZE_MAX",
                           "WAVE_COOLDOWN_INITIAL", "WAVE_COOLDOWN_AFTER")}
check(_gc_snapshot_cc_before == _gc_snapshot_cc_after,
      "Constructing CommandCenters with SPECTATOR/PLAYER profiles must not mutate GameConfig")

# (c) player_input_enabled flags
check(_SPECTATOR_PROFILE.player_input_enabled is False,
      "SPECTATOR_PROFILE.player_input_enabled should be False (view-only)")
check(_PLAYER_PROFILE.player_input_enabled is True,
      "PLAYER_PROFILE.player_input_enabled should be True (commands accepted)")

# (d) Backup auto-fire rule: does NOT fire in the non-imminent case under PLAYER_PROFILE,
# but DOES fire under SPECTATOR_PROFILE (autonomous_weapons=True always engages).
far_fighter = Aircraft(999, friendly_weight=0)
far_fighter.scenario = "HOSTILE_FIGHTER"
far_fighter.status = "HOSTILE"
far_fighter.distance_km = 500  # far outside the backup imminent radius, not a ballistic threat

plyr_backup_cmd = CommandCenter(profile=_PLAYER_PROFILE)
check(plyr_backup_cmd._is_backup_engagement(far_fighter) is False,
      "PLAYER_PROFILE backup auto-fire should NOT treat a far, non-ballistic contact as imminent")
plyr_backup_cmd.contacts = [far_fighter]
plyr_backup_cmd.process_personnel()
check(far_fighter.status == "HOSTILE",
      "Under PLAYER_PROFILE, a non-imminent hostile should NOT be auto-engaged (human holds the trigger)")

spec_backup_cmd = CommandCenter(profile=_SPECTATOR_PROFILE)
spec_backup_cmd.contacts = [far_fighter]
far_fighter.status = "HOSTILE"
spec_backup_cmd.process_personnel()
check(far_fighter.status in ("ENGAGING", "INTERCEPTING"),
      "Under SPECTATOR_PROFILE, autonomous_weapons should auto-engage even a non-imminent hostile")

# Imminent/leaking case: PLAYER_PROFILE should still auto-engage as a backstop
close_fighter = Aircraft(998, friendly_weight=0)
close_fighter.scenario = "HOSTILE_FIGHTER"
close_fighter.status = "HOSTILE"
close_fighter.distance_km = 10  # inside BACKUP_ENGAGEMENT_RADIUS_KM
check(plyr_backup_cmd._is_backup_engagement(close_fighter) is True,
      "PLAYER_PROFILE backup auto-fire SHOULD treat an imminent/leaking close contact as backup-engageable")


print("\n=== 35. Auto-CIWS Last-Ditch Leaker Discrimination ===")

from targets import GhostTrack as _GhostTrack


def _place(contact, dist_km, closing_km=1.0, bearing=0.0):
    """Position a contact at `dist_km` on `bearing` and set its previous
    position so it reads as closing (closing_km > 0) or opening (< 0)."""
    contact.bearing = bearing
    contact.distance_km = dist_km
    contact.x_km = dist_km * math.sin(math.radians(bearing))
    contact.y_km = dist_km * math.cos(math.radians(bearing))
    prev = dist_km + closing_km
    contact.prev_x_km = prev * math.sin(math.radians(bearing))
    contact.prev_y_km = prev * math.cos(math.radians(bearing))
    return contact


def _silent_cmd():
    c = CommandCenter()
    c.tactical_log = []
    return c


# --- 1. Closure geometry helper on AirContact ---
_closing = _place(TacticalBM(4001), 3.0, closing_km=2.0)
_opening = _place(TacticalBM(4002), 3.0, closing_km=-2.0)
check(_closing.is_closing_on_base() is True, "A contact whose range is decreasing must read as closing on the base")
check(_opening.is_closing_on_base() is False, "A contact whose range is increasing must NOT read as closing on the base")

# --- 2. WARRANTED: an unengaged, closing leaker inside the bubble IS engaged ---
random.seed(20250911)
cmd_ciws_fire = _silent_cmd()
leaker = _place(TacticalBM(4010), 3.0, closing_km=2.0)
leaker.status = "HOSTILE"
cmd_ciws_fire.contacts = [leaker]
check(leaker in cmd_ciws_fire.get_ciws_priority_targets(),
      "Auto-CIWS MUST select a closing, unengaged leaker inside the terminal bubble")
_ammo_before = cmd_ciws_fire.ammo["CIWS"]
cmd_ciws_fire.process_auto_ciws()
check(cmd_ciws_fire.ammo["CIWS"] < _ammo_before,
      f"Auto-CIWS must expend rounds on a genuine leaker ({_ammo_before} -> {cmd_ciws_fire.ammo['CIWS']})")

# --- 3. UNWARRANTED: a contact in range but NOT closing on the base is held ---
cmd_ciws_hold = _silent_cmd()
drifter = _place(Drone(4011), 3.0, closing_km=-1.5)
drifter.status = "HOSTILE"
cmd_ciws_hold.contacts = [drifter]
check(drifter not in cmd_ciws_hold.get_ciws_priority_targets(),
      "Auto-CIWS must HOLD FIRE on a contact that is inside the bubble but opening/not closing")
_ammo_before = cmd_ciws_hold.ammo["CIWS"]
cmd_ciws_hold.process_auto_ciws()
check(cmd_ciws_hold.ammo["CIWS"] == _ammo_before,
      "Auto-CIWS must not burn rounds on a non-closing contact")

# --- 4. UNWARRANTED: already handled by an outer layer (SAM in the air, non-terminal) ---
cmd_ciws_layer = _silent_cmd()
handled = _place(TacticalBM(4012), 12.0, closing_km=2.0)
handled.speed_mach = 0.5          # ETA well beyond the terminal override window
handled.status = "ENGAGING"
cmd_ciws_layer.contacts = [handled]
cmd_ciws_layer.active_engagements = [Engagement(handled, "SAM", 3)]
check(handled.get_eta() > cmd_ciws_layer.CIWS_TERMINAL_ETA_TICKS,
      "Test fixture sanity: outer-layer target must be outside the CIWS terminal override window")
check(handled not in cmd_ciws_layer.get_ciws_priority_targets(),
      "Auto-CIWS must HOLD FIRE on a contact already engaged by the outer SAM/THAAD/fighter layer")
_ammo_before = cmd_ciws_layer.ammo["CIWS"]
cmd_ciws_layer.process_auto_ciws()
check(cmd_ciws_layer.ammo["CIWS"] == _ammo_before,
      "Auto-CIWS must not double-spend on a target the outer layer already has a shot at")

# --- 5. WARRANTED: the outer layer failed and the leaker is now terminal ---
cmd_ciws_term = _silent_cmd()
terminal = _place(TacticalBM(4013), 1.0, closing_km=2.0)
terminal.speed_mach = 6.0          # ETA ~ 0.5 ticks: last-ditch, override the hold
terminal.status = "ENGAGING"
cmd_ciws_term.contacts = [terminal]
cmd_ciws_term.active_engagements = [Engagement(terminal, "SAM", 5)]
check(terminal in cmd_ciws_term.get_ciws_priority_targets(),
      "Auto-CIWS MUST override the outer-layer hold when the leaker is inside the terminal window")

# --- 6. UNWARRANTED: injected EW ghosts / clutter cannot hurt the base ---
cmd_ciws_ghost = _silent_cmd()
fake = _place(EWGhostTrack(4014), 2.0, closing_km=1.0)
fake.status = "UNIDENTIFIED"
clutter = _place(_GhostTrack(4015), 2.0, closing_km=1.0)
clutter.status = "UNIDENTIFIED"
cmd_ciws_ghost.contacts = [fake, clutter]
check(cmd_ciws_ghost.get_ciws_priority_targets() == [],
      "Auto-CIWS must HOLD FIRE on injected EW ghosts and weather/bird clutter")
_ammo_before = cmd_ciws_ghost.ammo["CIWS"]
cmd_ciws_ghost.process_auto_ciws()
check(cmd_ciws_ghost.ammo["CIWS"] == _ammo_before,
      "Auto-CIWS must not expend its magazine on non-kinetic radar returns")

# --- 7. UNWARRANTED: a contact squawking valid IFF is never a last-ditch target ---
cmd_ciws_iff = _silent_cmd()
squawker = _place(Aircraft(4016, friendly_weight=100), 2.0, closing_km=1.0)
squawker.has_transponder = True
squawker.status = "UNIDENTIFIED"
cmd_ciws_iff.contacts = [squawker]
check(squawker not in cmd_ciws_iff.get_ciws_priority_targets(),
      "Auto-CIWS must HOLD FIRE on an IFF-squawking contact (blue-on-blue / airliner protection)")

# --- 8. PRIORITISATION: the highest threat score is serviced first ---
cmd_ciws_prio = _silent_cmd()
low = _place(Drone(4017), 4.0, closing_km=1.0); low.status = "HOSTILE"
high = _place(ICBM(4018), 4.0, closing_km=1.0); high.status = "HOSTILE"
mid = _place(TacticalBM(4019), 4.0, closing_km=1.0); mid.status = "HOSTILE"
cmd_ciws_prio.contacts = [low, mid, high]
_prio = cmd_ciws_prio.get_ciws_priority_targets()
check(_prio and _prio[0] is high,
      f"Auto-CIWS must service the highest calculate_threat_score() leaker first (got {_prio[0].id_code if _prio else None})")
check(low not in _prio,
      "Auto-CIWS must not service the lowest-value contact while higher-value leakers are inbound")

# --- 9. MAGAZINE DISCIPLINE: bounded targets per tick, single-target on low ammo ---
cmd_ciws_budget = _silent_cmd()
swarm = []
for i in range(6):
    d = _place(Drone(4100 + i), 4.0, closing_km=1.0)
    d.status = "HOSTILE"
    swarm.append(d)
cmd_ciws_budget.contacts = list(swarm)
check(len(cmd_ciws_budget.get_ciws_priority_targets()) <= cmd_ciws_budget.CIWS_MAX_TARGETS_PER_TICK,
      "Auto-CIWS must not slew onto more than CIWS_MAX_TARGETS_PER_TICK leakers in one tick")
cmd_ciws_budget.ammo["CIWS"] = 5   # below the reserve fraction
check(len(cmd_ciws_budget.get_ciws_priority_targets()) == 1,
      "Auto-CIWS on a near-empty magazine must engage only the single highest-value leaker")

# --- 10. GameConfig remains untouched by the CIWS doctrine ---
check(GameConfig.MAX_AMMO["CIWS"] == 150, "CIWS doctrine must not mutate GameConfig.MAX_AMMO")


print("\n=== 36. Context-Derived Chaff / Evasion Countermeasures ===")

# --- 1. Countermeasure loadout is a real, finite resource ---
random.seed(777)
_civ = Aircraft(4200, friendly_weight=100)
check(_civ.is_friendly is True, "Test fixture sanity: friendly_weight=100 should produce a civil aircraft")
check(getattr(_civ, 'chaff_remaining', None) == 0,
      "Civil/friendly aircraft carry no chaff dispensers")

_combat = Aircraft(4201, friendly_weight=0)
check(getattr(_combat, 'chaff_remaining', 0) > 0,
      "Hostile combat aircraft must carry a finite chaff load")

# --- 2. UNWARRANTED: no countermeasures left => chaff can never trigger ---
_dry = Aircraft(4202, friendly_weight=0)
_dry.distance_km = 200.0
_dry.chaff_remaining = 0
check(_dry.chaff_evasion_chance(salvo_count=1) == 0.0,
      "An aircraft out of chaff must have ZERO evasion chance (not a dice roll)")

# --- 3. WARRANTED: a stocked EW platform under a single-missile shot evades often ---
_ew = Aircraft(4203, friendly_weight=0)
_ew.distance_km = 200.0
_ew.is_heavy_ew = True
_ew.chaff_remaining = 5
_plain = Aircraft(4204, friendly_weight=0)
_plain.distance_km = 200.0
_plain.true_type = "Su-30MKM Flanker"
_plain.chaff_remaining = 5
check(_ew.chaff_evasion_chance(salvo_count=1) > _plain.chaff_evasion_chance(salvo_count=1),
      "A heavy EW platform must defeat a radar-guided shot more often than a plain fighter")
check(0.0 < _plain.chaff_evasion_chance(salvo_count=1) < 1.0,
      "A stocked combat aircraft must have a non-trivial but non-certain chaff chance")

# --- 4. Geometry: a terminal-range shot leaves no time for chaff to bloom ---
_near = Aircraft(4205, friendly_weight=0); _near.chaff_remaining = 5
_near.true_type = "Su-30MKM Flanker"; _near.distance_km = 3.0
_far = Aircraft(4206, friendly_weight=0); _far.chaff_remaining = 5
_far.true_type = "Su-30MKM Flanker"; _far.distance_km = 250.0
check(_near.chaff_evasion_chance(salvo_count=1) < _far.chaff_evasion_chance(salvo_count=1),
      "Chaff must be far less effective against a terminal-range shot than a long-range shot")

# --- 5. A ripple/salvo cannot all be decoyed by one bundle; ECCM burn-through degrades it ---
check(_far.chaff_evasion_chance(salvo_count=3) < _far.chaff_evasion_chance(salvo_count=1),
      "A 3-missile salvo must be harder to defeat with chaff than a single missile")
check(_far.chaff_evasion_chance(salvo_count=1, eccm_active=True) < _far.chaff_evasion_chance(salvo_count=1),
      "Radar burn-through ECCM must degrade chaff effectiveness")

# --- 6. Not a constant: the probability varies with context ---
_samples = {
    _plain.chaff_evasion_chance(salvo_count=1),
    _near.chaff_evasion_chance(salvo_count=1),
    _ew.chaff_evasion_chance(salvo_count=1),
    _far.chaff_evasion_chance(salvo_count=3),
}
check(len(_samples) >= 4, f"Chaff probability must be derived from context, not constant (got {sorted(_samples)})")

# --- 7. INTEGRATION: dry aircraft NEVER chaffs, stocked aircraft DOES (seeded) ---
def _run_sam_shot(target, trials, seed):
    random.seed(seed)
    decoyed = 0
    for _ in range(trials):
        target.active = True
        target.status = "ENGAGING"
        c = CommandCenter()
        c.tactical_log = []
        c.contacts = [target]
        c.active_engagements = [Engagement(target, "SAM", 1)]
        c.process_engagements()
        if any("DEPLOYED CHAFF" in entry for entry in c.tactical_log):
            decoyed += 1
    return decoyed

_dry_tgt = Aircraft(4207, friendly_weight=0)
_dry_tgt.distance_km = 250.0
_dry_tgt.chaff_remaining = 0
check(_run_sam_shot(_dry_tgt, 40, 31337) == 0,
      "INTEGRATION: an aircraft with no countermeasures must NEVER deploy chaff")

_wet_tgt = Aircraft(4208, friendly_weight=0)
_wet_tgt.distance_km = 250.0
_wet_tgt.is_heavy_ew = True
_wet_tgt.chaff_remaining = 10**6   # effectively unlimited for the statistical check
check(_run_sam_shot(_wet_tgt, 40, 31337) > 0,
      "INTEGRATION: a stocked EW platform under a long-range SAM shot must sometimes chaff")

# --- 8. Chaff consumes the dispenser load ---
_finite = Aircraft(4209, friendly_weight=0)
_finite.distance_km = 250.0
_finite.is_heavy_ew = True
_finite.chaff_remaining = 3
_before = _finite.chaff_remaining
_run_sam_shot(_finite, 60, 999)
check(_finite.chaff_remaining < _before,
      f"Deploying chaff must consume the dispenser load ({_before} -> {_finite.chaff_remaining})")


print("\n=== 37. EW Ghost Flood Gated on Real Electronic-Warfare State ===")

def _jammer_at(cmd, dist_km, heavy=True, track=4300):
    j = Aircraft(track, friendly_weight=0)
    j.distance_km = dist_km
    j.x_km, j.y_km = 0.0, dist_km
    j.active = True
    j.status = "HOSTILE"
    if heavy:
        j.is_heavy_ew = True
        j.true_type = "EA-18G Growler (HEAVY EW)"
        j.type_name = "EA-18G Growler (HEAVY EW)"
    else:
        j.true_type = "Y-9G EW"
        j.type_name = "Y-9G EW"
    cmd.contacts = [j]
    return j

# --- 1. UNWARRANTED: no jammer at all => no flood ---
cmd_ew_none = CommandCenter()
cmd_ew_none.tactical_log = []
cmd_ew_none.contacts = []
check(cmd_ew_none.get_ew_flood_chance()[0] == 0.0,
      "No jammer present => EW ghost flood chance must be exactly 0")

# --- 2. UNWARRANTED: radar is not radiating (EMCON SILENT) => no flood ---
cmd_ew_silent = CommandCenter()
cmd_ew_silent.tactical_log = []
_jammer_at(cmd_ew_silent, 60.0)
cmd_ew_silent.emcon_mode = "SILENT"
check(cmd_ew_silent.get_ew_flood_chance()[0] == 0.0,
      "A jammer cannot flood a radar that is not radiating (EMCON SILENT) => chance must be 0")

# --- 3. WARRANTED: radiating radar + close heavy jammer => strong flood ---
cmd_ew_active = CommandCenter()
cmd_ew_active.tactical_log = []
_jammer_at(cmd_ew_active, 60.0)
cmd_ew_active.emcon_mode = "ACTIVE"
_close_chance = cmd_ew_active.get_ew_flood_chance()[0]
check(_close_chance > 0.0, "A radiating radar under a close heavy jammer must suffer a ghost flood")

# --- 4. Derived from range: a distant jammer floods less than a close one ---
cmd_ew_far = CommandCenter()
cmd_ew_far.tactical_log = []
_jammer_at(cmd_ew_far, 1100.0)
cmd_ew_far.emcon_mode = "ACTIVE"
_far_chance = cmd_ew_far.get_ew_flood_chance()[0]
check(_far_chance > 0.0, "A distant jammer still injects some false targets into a radiating radar")
check(_far_chance < _close_chance,
      f"Flood rate must fall with jammer range ({_far_chance:.3f} at 1100km vs {_close_chance:.3f} at 60km)")

# --- 5. Derived from strength: a heavy jammer out-floods a standard EW platform ---
cmd_ew_light = CommandCenter()
cmd_ew_light.tactical_log = []
_jammer_at(cmd_ew_light, 60.0, heavy=False)
cmd_ew_light.emcon_mode = "ACTIVE"
check(cmd_ew_light.get_ew_flood_chance()[0] < _close_chance,
      "A standard EW platform must flood less than a heavy dedicated jammer at the same range")

# --- 6. EMCON SECTOR (partial emission) and ECCM burn-through both suppress the flood ---
cmd_ew_sector = CommandCenter()
cmd_ew_sector.tactical_log = []
_jammer_at(cmd_ew_sector, 60.0)
cmd_ew_sector.emcon_mode = "SECTOR"
check(0.0 < cmd_ew_sector.get_ew_flood_chance()[0] < _close_chance,
      "Sector-limited emission must reduce (but not eliminate) the ghost flood")

cmd_ew_eccm = CommandCenter()
cmd_ew_eccm.tactical_log = []
_jammer_at(cmd_ew_eccm, 60.0)
cmd_ew_eccm.emcon_mode = "ACTIVE"
cmd_ew_eccm.burn_through_active = True
check(cmd_ew_eccm.get_ew_flood_chance()[0] < _close_chance,
      "Radar burn-through ECCM must suppress the ghost flood rate")

# --- 7. The flood must not feed on itself: injected ghosts are not jammers ---
cmd_ew_self = CommandCenter()
cmd_ew_self.tactical_log = []
_self_ghost = EWGhostTrack(4350)
check(cmd_ew_self.get_jammer_strength(_self_ghost) == 0.0,
      "An injected EW ghost track must never be counted as a jammer (no self-amplifying flood)")

# --- 8. INTEGRATION: SILENT radar produces zero ghosts, ACTIVE radar produces ghosts ---
random.seed(9090)
cmd_int_silent = CommandCenter()
cmd_int_silent.tactical_log = []
_jammer_at(cmd_int_silent, 80.0, track=4360)
cmd_int_silent.emcon_mode = "SILENT"
for _ in range(40):
    cmd_int_silent.detect_airspace()
_silent_ghosts = sum(1 for c in cmd_int_silent.contacts if isinstance(c, EWGhostTrack))
check(_silent_ghosts == 0,
      f"INTEGRATION: EMCON SILENT must yield zero injected EW ghosts over 40 ticks (got {_silent_ghosts})")

random.seed(9090)
cmd_int_active = CommandCenter()
cmd_int_active.tactical_log = []
_jammer_at(cmd_int_active, 80.0, track=4361)
cmd_int_active.emcon_mode = "ACTIVE"
for _ in range(40):
    cmd_int_active.detect_airspace()
_active_ghosts = sum(1 for c in cmd_int_active.contacts if isinstance(c, EWGhostTrack))
check(_active_ghosts > 0,
      f"INTEGRATION: a radiating radar under a close heavy jammer must be flooded (got {_active_ghosts})")

# --- 9. UNWARRANTED: our own AEW&C is not an enemy jammer ---
cmd_ew_blue = CommandCenter()
cmd_ew_blue.tactical_log = []
_own_awacs = AWACS(4370)          # true_type "Saab 340 AEW&C" contains the "EW" substring
_own_awacs.distance_km = 150.0
cmd_ew_blue.contacts = [_own_awacs]
cmd_ew_blue.emcon_mode = "ACTIVE"
check(cmd_ew_blue.get_jammer_strength(_own_awacs) == 0.0,
      "A friendly AEW&C must never be scored as an enemy jammer")
check(cmd_ew_blue.get_ew_flood_chance()[0] == 0.0,
      "Friendly AEW&C on station must NOT trigger an enemy EW ghost flood")

# --- 10. GameConfig untouched by the EW doctrine ---
check(GameConfig.WAVE_CHANCE == 0.20, "EW flood doctrine must not mutate GameConfig.WAVE_CHANCE")

print("\n=== 38. DEFAULT_PROFILE Retains Command Input ===")
from profiles import DEFAULT_PROFILE as _DEFAULT_PROFILE, SPECTATOR_PROFILE as _SPECTATOR_PROFILE_38, PLAYER_PROFILE as _PLAYER_PROFILE_38

# Un-profiled callers (running radar_ui.py directly, or start_radar(profile=None))
# must land on a fully interactive console, not a silent view-only mode.
check(_DEFAULT_PROFILE.player_input_enabled is True,
      "DEFAULT_PROFILE.player_input_enabled must be True -- otherwise running radar_ui.py "
      "directly (or start_radar(profile=None)) silently disables firing/restart input")
check(_SPECTATOR_PROFILE_38.player_input_enabled is False,
      "SPECTATOR_PROFILE.player_input_enabled must remain False (true view-only mode)")
check(_PLAYER_PROFILE_38.player_input_enabled is True,
      "PLAYER_PROFILE.player_input_enabled must remain True (human holds the trigger)")
# Guard against the three profiles ever drifting to the same value by accident.
check(len({_DEFAULT_PROFILE.player_input_enabled, _SPECTATOR_PROFILE_38.player_input_enabled}) == 2,
      "DEFAULT and SPECTATOR profiles must not collapse to the same player_input_enabled value")

print("\n=== 39. Spectator Cannot Reach IFF Re-Designation (Court-Martial Guard) ===")
# The Flight Info Panel's H/S/F/U IFF buttons live under MOUSEBUTTONDOWN in
# radar_ui.py (panel button block, ~line 388-397), OUTSIDE the KEYDOWN command
# gate. That block is only reachable when `profile.player_input_enabled` is
# True (see radar_ui.py:389 `if selected_contact and profile.player_input_enabled:`).
# SPECTATOR_PROFILE.player_input_enabled == False is therefore the ONLY thing
# standing between a spectator and a court-martial: prove the flag is correct,
# and separately prove the underlying kill path really is that dangerous.
check(_SPECTATOR_PROFILE_38.player_input_enabled is False,
      "GATE CHECK: radar_ui.py's IFF panel-button block (H/S/F/U) is guarded by "
      "profile.player_input_enabled; SPECTATOR_PROFILE must keep this False or the "
      "gate at radar_ui.py:389 is bypassed")

_civilian = Airliner(4400)
_civilian.status = "HOSTILE"  # exactly what clicking "H" in the panel does to selected_contact
_cc_39 = CommandCenter()
_cc_39.tactical_log = []
check(_cc_39.is_court_martialed is False and _cc_39.base_hp > 0,
      "Sanity: CommandCenter starts un-court-martialed with a healthy base")
_cc_39.record_kill(_civilian, "SAM")
check(_cc_39.is_court_martialed is True and _cc_39.base_hp == 0,
      "DANGER CONFIRMED: killing a civilian Airliner re-designated HOSTILE via the IFF "
      "panel triggers court-martial + base_hp=0 (record_kill checks isinstance(..., Airliner), "
      "not the possibly-tampered .status) -- this is exactly why the panel button block "
      "MUST stay gated on profile.player_input_enabled")

print("\n=== 40. Restart After Death Reachable in Both Modes ===")
# radar_ui.py's AAR screen (~line 993) always renders "Press [R] to Re-Scramble
# Sortie" regardless of profile, so the K_r-on-death restart handler at
# radar_ui.py:347 (`if event.type == pygame.KEYDOWN and event.key == pygame.K_r
# and cmd.base_hp <= 0:`) MUST stay OUTSIDE the player-input gate (the gate is
# only for event.type == pygame.KEYDOWN and profile.player_input_enabled at
# radar_ui.py:221) -- otherwise Spectator is stranded on a dead screen with
# only ESC/quit. We cannot press a key from this test, so we prove restart
# genuinely works by reconstruction, and that it is not conditioned on
# player_input_enabled.
_dead_cc = CommandCenter(profile=_SPECTATOR_PROFILE_38)
_dead_cc.base_hp = 0
_dead_cc.is_court_martialed = False
check(_dead_cc.base_hp <= 0, "Sanity: simulated death leaves base_hp <= 0")

# "Press [R]" reconstructs a fresh CommandCenter (radar_ui.py's restart path
# does `cmd = CommandCenter(profile=profile)`); this must produce a healthy
# game under SPECTATOR_PROFILE too, since the AAR screen offers it there.
_restarted_spectator_cc = CommandCenter(profile=_SPECTATOR_PROFILE_38)
check(_restarted_spectator_cc.base_hp > 0 and _restarted_spectator_cc.is_court_martialed is False,
      "RESTART MUST WORK UNGATED: a fresh CommandCenter(profile=SPECTATOR_PROFILE) built "
      "after death must have a healthy base_hp -- the K_r-on-death handler at radar_ui.py:347 "
      "must NOT be nested inside `profile.player_input_enabled`, or Spectator can never "
      "reach the restart the AAR screen promises")
_restarted_player_cc = CommandCenter(profile=_PLAYER_PROFILE_38)
check(_restarted_player_cc.base_hp > 0 and _restarted_player_cc.is_court_martialed is False,
      "Restart-by-reconstruction must also work under PLAYER_PROFILE")

print("\n=== 41. Player-Mode Backup Fire Must Not Starve on a Distant Priority Threat ===")
# Verified repro: a distant, backup-INELIGIBLE CruiseMissile (highest threat
# score) pops before a close, backup-ELIGIBLE Drone (leaker). The old
# process_personnel() popped exactly one threat per tick and discarded the
# tick entirely if that one threat wasn't backup-eligible, starving the
# leaker forever. The fix walks the queue within the same tick instead of
# stopping at the first pop.
random.seed(4141)
_cm_41 = CruiseMissile(501)
_cm_41.distance_km = 120.0
_cm_41.active = True
_cm_41.status = "HOSTILE"

_dr_41 = Drone(502)
_dr_41.distance_km = 15.0
_dr_41.active = True
_dr_41.status = "HOSTILE"

_c_41 = CommandCenter(profile=_PLAYER_PROFILE_38)
_c_41.contacts = [_cm_41, _dr_41]

# Confirm the verified pop order and eligibility split before relying on it.
_c_41.threat_queue.build_queue(_c_41.contacts)
_first_pop = _c_41.threat_queue.pop_highest_priority()
_second_pop = _c_41.threat_queue.pop_highest_priority()
check(_first_pop is _cm_41 and _second_pop is _dr_41,
      "Pop order check: the distant CruiseMissile (higher threat score) must pop before "
      "the close Drone -- this is what causes starvation if the tick is discarded on the first pop")
check(_c_41._is_backup_engagement(_cm_41) is False and _c_41._is_backup_engagement(_dr_41) is True,
      "Eligibility check: the CruiseMissile must be backup-INELIGIBLE and the close Drone "
      "backup-ELIGIBLE -- this is the exact combination that starves the leaker")

# PREP_TIME_THAAD=20 / SAM=12 / F16=10 -- a short loop would read as a false
# zero, so run a horizon of 40 ticks (well beyond any single prep time).
for _ in range(40):
    _c_41.process_personnel()
check(len(_c_41.active_engagements) >= 1,
      "STARVATION BUG: after 40 ticks under PLAYER_PROFILE, the close leaking Drone must "
      "get engaged (active_engagements >= 1) even though a distant, backup-ineligible "
      "CruiseMissile pops first every tick -- without the fix this stays 0 forever")

# Mode contrast: a leaker (15km) is engaged under BOTH profiles; a genuinely
# distant contact (100km) is engaged under SPECTATOR but correctly left for
# the human under PLAYER (backup fire must not become full autonomy).
random.seed(4142)
_dr_leaker_spec = Drone(503); _dr_leaker_spec.distance_km = 15.0; _dr_leaker_spec.active = True; _dr_leaker_spec.status = "HOSTILE"
_cc_leaker_spec = CommandCenter(profile=_SPECTATOR_PROFILE_38)
_cc_leaker_spec.contacts = [_dr_leaker_spec]
for _ in range(40):
    _cc_leaker_spec.process_personnel()
check(len(_cc_leaker_spec.active_engagements) >= 1,
      "Mode contrast: a 15km leaker Drone must be engaged under SPECTATOR_PROFILE over 40 ticks")

random.seed(4143)
_dr_leaker_ply = Drone(504); _dr_leaker_ply.distance_km = 15.0; _dr_leaker_ply.active = True; _dr_leaker_ply.status = "HOSTILE"
_cc_leaker_ply = CommandCenter(profile=_PLAYER_PROFILE_38)
_cc_leaker_ply.contacts = [_dr_leaker_ply]
for _ in range(40):
    _cc_leaker_ply.process_personnel()
check(len(_cc_leaker_ply.active_engagements) >= 1,
      "Mode contrast: a 15km leaker Drone must ALSO be engaged under PLAYER_PROFILE over "
      "40 ticks (backup fire backstop)")

random.seed(4144)
_dr_distant_spec = Drone(505); _dr_distant_spec.distance_km = 100.0; _dr_distant_spec.active = True; _dr_distant_spec.status = "HOSTILE"
_cc_distant_spec = CommandCenter(profile=_SPECTATOR_PROFILE_38)
_cc_distant_spec.contacts = [_dr_distant_spec]
for _ in range(40):
    _cc_distant_spec.process_personnel()
check(len(_cc_distant_spec.active_engagements) >= 1,
      "Mode contrast: a 100km distant Drone must be engaged under SPECTATOR_PROFILE (full autonomy)")

random.seed(4145)
_dr_distant_ply = Drone(506); _dr_distant_ply.distance_km = 100.0; _dr_distant_ply.active = True; _dr_distant_ply.status = "HOSTILE"
_cc_distant_ply = CommandCenter(profile=_PLAYER_PROFILE_38)
_cc_distant_ply.contacts = [_dr_distant_ply]
for _ in range(40):
    _cc_distant_ply.process_personnel()
check(len(_cc_distant_ply.active_engagements) == 0,
      "Mode contrast: a 100km distant Drone must NOT be auto-engaged under PLAYER_PROFILE "
      "(correctly left for the human to fire on manually), proving backup fire stays restricted")


print("\n=== 42. Geodata Theatre Registration & Fidelity (v1.4.1 map expansion) ===")
import json as _json42
import re as _re42
import main as _main42
from map_manager import MapManager as _MapManager42

_here42 = os.path.dirname(__file__)

# The loader is generic: it iterates country_files and projects each ring. Parse the
# registry straight from the source so a file added to the dict but missing from disk
# (or vice versa) fails here rather than silently rendering nothing.
_src42 = open(os.path.join(_here42, "map_manager.py"), encoding="utf-8").read()
_m42 = _re42.search(r"country_files = \{(.*?)\}", _src42, _re42.S)
check(_m42 is not None,
      "country_files dict must be parseable from map_manager.py (reformatted or renamed?)")
_registry42 = dict(_re42.findall(r'"(\w+)":\s*"([\w.]+\.json)"', _m42.group(1))) if _m42 else {}

_map42 = _MapManager42()

check(len(_registry42) == 21,
      f"Registry must list 21 regions once Japan joins the theatre (found {len(_registry42)})")

_missing42 = [f for f in _registry42.values() if not os.path.exists(os.path.join(_here42, f))]
check(not _missing42,
      f"Every registered country file must exist on disk (missing: {_missing42})")

_empty42 = [iso for iso in _registry42 if not _map42.country_polys.get(iso)]
check(not _empty42,
      f"Every registered region must load at least one >=3-point ring (empty: {_empty42})")

# v1.4.0 baseline must never silently disappear - this is the regression guard.
_BASELINE42 = ["CHN", "IDN", "KHM", "LAO", "MMR", "MYS", "PHL", "SGP", "THA", "TWN", "VNM"]
_lost42 = [iso for iso in _BASELINE42 if iso not in _map42.country_polys]
check(not _lost42,
      f"All 11 v1.4.0 regions must survive the expansion (lost: {_lost42})")

# Each new region must contain the country it claims to. Without a geographic assertion
# every other check here passes even if one file holds a duplicate of another country:
# the region count, the point counts and the theatre span all stay identical while the
# real country silently vanishes from the map.
_BOX42 = {  # iso: (lon_min, lon_max, lat_min, lat_max) from Natural Earth 1:10m
    "IND": (68.1, 97.4, 6.7, 35.5), "BGD": (88.0, 92.6, 20.7, 26.6),
    "LKA": (79.7, 81.9, 5.9, 9.8),  "NPL": (80.0, 88.2, 26.3, 30.4),
    "BTN": (88.7, 92.1, 26.7, 28.4), "BRN": (114.0, 115.4, 4.0, 5.1),
    "TLS": (124.0, 127.3, -9.5, -8.1), "KOR": (124.6, 131.9, 33.2, 38.6),
    "PRK": (124.2, 130.7, 37.7, 43.0), "JPN": (122.9, 145.9, 24.2, 45.6),
}
_TOL42 = 1.5  # degrees of slack for simplification nudging an extremity
for _iso42, (_lo42, _hi42, _la42, _ha42) in sorted(_BOX42.items()):
    _fn42 = _registry42.get(_iso42)
    check(_fn42 is not None, f"{_iso42} must be registered in country_files")
    if not _fn42 or not os.path.exists(os.path.join(_here42, _fn42)):
        continue
    _rings42 = _json42.load(open(os.path.join(_here42, _fn42), encoding="utf-8"))
    _lons42 = [p[0] for r in _rings42 for p in r]
    _lats42 = [p[1] for r in _rings42 for p in r]
    _fits42 = (_lo42 - _TOL42 <= min(_lons42) and max(_lons42) <= _hi42 + _TOL42
               and _la42 - _TOL42 <= min(_lats42) and max(_lats42) <= _ha42 + _TOL42)
    check(_fits42,
          f"{_iso42} ({_fn42}) must actually contain {_iso42} territory: expected lon "
          f"{_lo42}..{_hi42} lat {_la42}..{_ha42} (+/-{_TOL42}), got lon "
          f"{min(_lons42):.1f}..{max(_lons42):.1f} lat {min(_lats42):.1f}..{max(_lats42):.1f}")
    check(sum(len(r) for r in _rings42) >= 80,
          f"{_iso42} outline must carry >=80 points, not a degenerate blocky shape "
          f"(got {sum(len(r) for r in _rings42)}; twn.json shipped at 9 in v1.4.0)")
    _degen42 = [i for i, r in enumerate(_rings42)
                if abs(sum(r[i2][0] * r[(i2 + 1) % len(r)][1] - r[(i2 + 1) % len(r)][0] * r[i2][1]
                           for i2 in range(len(r)))) / 2.0 == 0.0]
    check(not _degen42,
          f"{_iso42} must contain no zero-area rings that draw sub-pixel hairlines "
          f"(ring indices: {_degen42})")

_xs42 = [p[0] for rings in _map42.country_polys.values() for r in rings for p in r]
_ys42 = [p[1] for rings in _map42.country_polys.values() for r in rings for p in r]
_xspan42, _yspan42 = max(_xs42) - min(_xs42), max(_ys42) - min(_ys42)

check(_xspan42 > 3716 and _yspan42 > 2930,
      f"Theatre must exceed the v1.4.0 baseline of 3716 x 2930 km "
      f"(got {_xspan42:.0f} x {_yspan42:.0f} km)")

# radar_ui.py clamps the zoom and sizes the window at 90% of the monitor, so the
# tightest real case is the narrowest supported display. Read the clamp out of the
# source rather than restating it here - a copy of a constant drifts from it.
_MIN_MONITOR_W42 = 1024
_half42 = _MIN_MONITOR_W42 * 0.9 / 2.0
_ui42 = open(os.path.join(_here42, "radar_ui.py"), encoding="utf-8").read()
_fm42 = _re42.search(r"zoom_level = max\((\d+\.\d+),", _ui42)
check(_fm42 is not None, "zoom floor must be parseable from radar_ui.py")
_floor42 = float(_fm42.group(1)) if _fm42 else 0.10
_far42 = max((x * x + y * y) ** 0.5 for x, y in zip(_xs42, _ys42))
check(_far42 * _floor42 < _half42,
      f"At the {_floor42} zoom floor from radar_ui.py the furthest point must stay on "
      f"screen on the narrowest supported {_MIN_MONITOR_W42}px display "
      f"({_far42:.0f} km -> {_far42 * _floor42:.0f} px, limit {_half42:.0f})")

# These two strings drifted apart once before (main.py at 1.3.1 while config.py said
# 1.3.2), so assert against the real module attribute, not just GameConfig.
check(_main42.__version__ == GameConfig.VERSION == "1.7.0",
      f"main.py __version__ ({_main42.__version__}) and GameConfig.VERSION "
      f"({GameConfig.VERSION}) must both read 1.7.0")

# 43. Clip-cut removal and label decluttering
#
# The geodata ships clipped to a rectangular window. Polygons that straddle it
# come back closed along the cut, which drew a straight 3000 km "border" across
# northern China and boxed the whole theatre in a visible frame. Labels then
# rendered at every zoom with no culling, so zooming out smeared the map into
# unreadable text. Both are guarded here because both are invisible to every
# other assertion in this file - the point counts and the theatre span are
# identical either way.
print("\n=== 43. Map Clip-Cut Removal & Label Decluttering ===")
import math as _math43
from map_manager import (MapManager as _MapManager43, detect_clip_lines as _detect43,
                         split_ring_on_frame as _splitring43,
                         split_line_on_frame as _splitline43)

_map43 = _MapManager43()
_cut_lons43, _cut_lats43 = _map43.data_frame

# The window was widened past Japan, so the cut that used to slice the
# archipelago at 130.9E must no longer exist at all. This is the regression
# guard for the refetch: if someone re-cuts the data narrow again, Japan gets
# sliced and this fires.
check(130.9 not in _cut_lons43,
      f"meridian 130.9 must no longer cut the theatre - it sliced Japan in half "
      f"(detected meridians: {sorted(_cut_lons43)})")
check(43.0 not in _cut_lats43,
      f"parallel 43.0 must no longer cut the theatre (detected parallels: {sorted(_cut_lats43)})")

# Japan must arrive whole: Hokkaido in the north and the Ryukyus in the south.
check(_map43.country_polys.get("JPN"), "Japan must be loaded into the theatre")
_jraw43 = _json42.load(open(os.path.join(_here42, "jpn.json"), encoding="utf-8"))
_jlats43 = [_p43[1] for _r43 in _jraw43 for _p43 in _r43]
_jlons43 = [_p43[0] for _r43 in _jraw43 for _p43 in _r43]
check(max(_jlats43) > 45.0,
      f"Hokkaido must survive the window (northernmost Japanese vertex {max(_jlats43):.2f}N)")
check(min(_jlats43) < 25.0,
      f"the Ryukyus must survive the window (southernmost Japanese vertex {min(_jlats43):.2f}N)")
check(max(_jlons43) > 145.0,
      f"eastern Hokkaido must survive the window (easternmost Japanese vertex {max(_jlons43):.2f}E)")

# The real defect: after loading, no long perfectly-axis-aligned run may survive.
# Genuine coastline is never both perfectly straight and hundreds of km long.
_worst43, _where43 = 0.0, None
for _name43, _sets43 in (("country", [r for v in _map43.country_polys.values() for r in v]),
                         ("coastline", _map43.coastlines_km),
                         ("border", _map43.borders_km)):
    for _r43 in _sets43:
        for _a43, _b43 in zip(_r43, _r43[1:]):
            if abs(_a43[0] - _b43[0]) < 1e-9 or abs(_a43[1] - _b43[1]) < 1e-9:
                _d43 = _math43.hypot(_b43[0] - _a43[0], _b43[1] - _a43[1])
                if _d43 > _worst43:
                    _worst43, _where43 = _d43, _name43
check(_worst43 < 100.0,
      f"no clip edge may survive as drawable geometry: longest axis-aligned run is "
      f"{_worst43:.0f} km in {_where43} data (chn.json alone shipped ~3000 km of it)")

# Rings the cut never touched must come back untouched and still closed, or the
# trimming would silently open every island in the theatre.
_square43 = [(10.0, 10.0), (11.0, 10.0), (11.0, 11.0), (10.0, 11.0), (10.0, 10.0)]
_runs43 = _splitring43(_square43, (frozenset(), frozenset()))
check(len(_runs43) == 1 and _runs43[0][1] is True and len(_runs43[0][0]) == 4,
      f"a ring clear of the cut must stay one closed ring (got {_runs43})")

# A ring whose top edge lies on a cut parallel must open up and lose that edge.
_clip43 = (frozenset(), frozenset([11.0]))
_runs43 = _splitring43(_square43, _clip43)
check(_runs43 and all(not _closed43 for _pts43, _closed43 in _runs43),
      f"a ring sitting on a cut must be returned open (got {_runs43})")
_kept43 = [_p43 for _pts43, _c43 in _runs43 for _p43 in _pts43]
check(not any(_a43[1] == _b43[1] == 11.0
              for _pts43, _c43 in _runs43 for _a43, _b43 in zip(_pts43, _pts43[1:])),
      "the cut edge itself must not survive the split")
check(len(_kept43) >= 3, f"the genuine geography either side of a cut must survive (got {_kept43})")

# Open polylines follow the same rule.
_line43 = [(10.0, 11.0), (11.0, 11.0), (11.0, 12.0)]
_runs43 = _splitline43(_line43, _clip43)
check(all(not (_a43[1] == _b43[1] == 11.0)
          for _r43 in _runs43 for _a43, _b43 in zip(_r43, _r43[1:])),
      f"split_line_on_frame must drop the cut segment (got {_runs43})")

# Curved geography must never be mistaken for a cut, and a straight run only
# counts when it sits at the extreme edge - an axis-aligned inland feature
# (a reservoir, a surveyed border) has to survive untouched.
_blob43 = [(100.0 + 10.0 * _math43.cos(_math43.radians(_i43 * 6)),
            15.0 + 10.0 * _math43.sin(_math43.radians(_i43 * 6)))
           for _i43 in range(60)]
_blob43.append(_blob43[0])
check(_detect43([_blob43]) == (frozenset(), frozenset()),
      "curved coastline with no straight extremal run must report no cuts")

_inland43 = [(99.0, 14.0), (101.0, 14.0), (101.0, 16.0), (99.0, 16.0), (99.0, 14.0)]
check(_detect43([_blob43, _inland43]) == (frozenset(), frozenset()),
      "a perfectly straight feature well inside the data extent must not be "
      "mistaken for a clip cut")
_runs43 = _splitring43(_inland43, _detect43([_blob43, _inland43]))
check(len(_runs43) == 1 and _runs43[0][1] is True,
      f"and it must therefore come through the split closed and whole (got {_runs43})")

# A straight run that does sit on the data extent is a cut and must be caught.
_edge43 = [(95.0, 25.0), (105.0, 25.0), (105.0, 24.0), (95.0, 24.0), (95.0, 25.0)]
_, _cuts43 = _detect43([_blob43, _edge43])
check(25.0 in _cuts43,
      f"a straight run along the data extent must be caught as a cut (got {sorted(_cuts43)})")

# Label tiers: priorities unique and ordered, and the tiers that make the map
# unreadable when zoomed out must actually be gated above the zoom floor.
_tiers43 = {_n43: getattr(_MapManager43, _n43) for _n43 in dir(_MapManager43)
            if _n43.startswith("LBL_")}
check(len(_tiers43) >= 8, f"label tiers must be declared on MapManager (found {sorted(_tiers43)})")
_prios43 = [_v43[0] for _v43 in _tiers43.values()]
check(len(set(_prios43)) == len(_prios43),
      f"label tier priorities must be unique so collisions resolve deterministically ({_tiers43})")
check(_MapManager43.LBL_HQ[0] < _MapManager43.LBL_BASE[0] < _MapManager43.LBL_PEAK[0],
      "the C2 HQ must outrank an airbase, which must outrank a mountain peak")

# Operational labels must outrank decorative ones. Ordered the obvious way round
# - country names above bases - the word THAILAND is wide enough to suppress
# WING 4 (TAKHLI) entirely at the DEFAULT zoom, 40 px away from it. On an air
# defence display that is the wrong thing to lose.
check(_MapManager43.LBL_BASE[0] < _MapManager43.LBL_SOVEREIGN[0]
      < _MapManager43.LBL_COUNTRY[0],
      f"an RTAF wing must outrank the sovereign label, which must outrank a "
      f"neighbouring country name (base={_MapManager43.LBL_BASE[0]}, "
      f"sovereign={_MapManager43.LBL_SOVEREIGN[0]}, "
      f"country={_MapManager43.LBL_COUNTRY[0]})")
check(_MapManager43.LBL_HQ[1] == 0.0 and _MapManager43.LBL_SOVEREIGN[1] == 0.0,
      "the HQ and the sovereign label must never be culled by zoom")
_zm43 = _re42.search(r"zoom_level = max\((\d+\.\d+),",
                     open(os.path.join(os.path.dirname(__file__), "radar_ui.py"),
                          encoding="utf-8").read())
check(_zm43 is not None, "zoom floor must be parseable from radar_ui.py")
_ZOOM_FLOOR43 = float(_zm43.group(1)) if _zm43 else 0.07
for _n43 in ("LBL_PEAK", "LBL_HUB", "LBL_BASE", "LBL_MARITIME"):
    check(getattr(_MapManager43, _n43)[1] > _ZOOM_FLOOR43,
          f"{_n43} must be culled at the {_ZOOM_FLOOR43} zoom floor, where it only "
          f"adds to the smear (min zoom {getattr(_MapManager43, _n43)[1]})")

# The label rules above are structural; this renders the map and reads the
# result back off the surface, which is the only way to catch a label that is
# queued correctly and then still lost in the collision pass.
import pygame as _pg43
_pg43.init()
_W43, _H43 = 1600, 900
_Z43 = 0.8
_surf43 = _pg43.Surface((_W43, _H43), _pg43.SRCALPHA)
_fxs43 = _pg43.font.SysFont("consolas", 10)
_fsm43 = _pg43.font.SysFont("consolas", 12)
_fmd43 = _pg43.font.SysFont("consolas", 16, bold=True)
_map43.invalidate_cache()
_map43.render(_surf43, _W43 // 2, _H43 // 2, _Z43, _W43, _H43, _fxs43, _fsm43, _fmd43)


def _anchor43(lat, lon):
    _x43, _y43 = latlon_to_km(lon, lat)
    return _W43 // 2 + _x43 * _Z43, _H43 // 2 - _y43 * _Z43


def _drawn43(tpl, ox, oy):
    """Fraction of a rendered label's own glyph pixels present on the surface."""
    _hit43 = _tot43 = 0
    for _px43 in range(tpl.get_width()):
        for _py43 in range(tpl.get_height()):
            _t43 = tpl.get_at((_px43, _py43))
            if _t43[3] < 200:
                continue
            _tot43 += 1
            _sx43, _sy43 = int(ox) + _px43, int(oy) + _py43
            if not (0 <= _sx43 < _W43 and 0 <= _sy43 < _H43):
                continue
            _s43 = _surf43.get_at((_sx43, _sy43))
            if max(abs(_s43[0] - _t43[0]), abs(_s43[1] - _t43[1]),
                   abs(_s43[2] - _t43[2])) < 40:
                _hit43 += 1
    return (_hit43 / _tot43) if _tot43 else 0.0


# An RTAF wing must actually survive to the surface at the default zoom. With
# country names ranked above bases, WING 4 (TAKHLI) scored 0.00 here - killed
# outright by the word THAILAND 40 px away.
_wx43, _wy43 = _anchor43(15.266, 100.333)
_wing43 = _drawn43(_fxs43.render("WING 4 (TAKHLI)", True, (0, 190, 255)),
                   _wx43 + 8, _wy43 - 4)
check(_wing43 > 0.5,
      f"WING 4 (TAKHLI) must be drawn at the default zoom, not suppressed by a "
      f"decorative country name (glyph match {_wing43:.2f})")

# And a subtitle must never outlive the label it belongs to: once bases started
# winning, "SOVEREIGN AIRSPACE" was left stranded with no THAILAND above it.
_cx43, _cy43 = _anchor43(15.2, 100.8)
_col43 = (0, 220, 100)
_ttl43 = _fmd43.render("THAILAND", True, _col43)
_sub43 = _fxs43.render("SOVEREIGN AIRSPACE", True,
                       (_col43[0] // 2 + 30, _col43[1] // 2 + 30, _col43[2] // 2 + 30))
_title_in43 = _drawn43(_ttl43, _cx43 - _ttl43.get_width() // 2, _cy43 - 10)
_sub_in43 = _drawn43(_sub43, _cx43 - _sub43.get_width() // 2, _cy43 + 8)
check(not (_sub_in43 > 0.9 and _title_in43 < 0.5),
      f"a subtitle must never outlive its own country label (THAILAND "
      f"{_title_in43:.2f}, SOVEREIGN AIRSPACE {_sub_in43:.2f})")

# 44. Viewport culling and level-of-detail
#
# The theatre carries ~97k drawable points and the surface cache misses on every
# pan, so render() rejects off-screen strokes on their bounding box and thins
# strokes finer than LOD_MIN_PX. Both are silent optimisations - if either is
# wrong the map just quietly loses geography, which no other assertion notices.
print("\n=== 44. Viewport Culling & Level Of Detail ===")
from map_manager import (stroke_meta as _meta44, LOD_MIN_PX as _LOD44,
                         thin_stroke as _thin44f)

_line44 = [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0)]
_m44 = _meta44(_line44)
check(_m44[0] == 0.0 and _m44[1] == 0.0 and _m44[2] == 10.0 and _m44[3] == 5.0,
      f"stroke_meta must report the true bounding box (got {_m44[:4]})")
check(abs(_m44[4] - 7.5) < 1e-9,
      f"stroke_meta must report the mean segment length (got {_m44[4]})")

# Metadata must stay index-aligned with the geometry it describes, or culling
# rejects the wrong stroke and the map loses a random country.
for _iso44, _rings44 in _map43.country_polys.items():
    check(len(_map43.country_meta.get(_iso44, [])) == len(_rings44),
          f"{_iso44} metadata must be index-aligned with its rings "
          f"({len(_map43.country_meta.get(_iso44, []))} vs {len(_rings44)})")
check(len(_map43.coast_meta) == len(_map43.coastlines_km),
      f"coastline metadata must be index-aligned ({len(_map43.coast_meta)} vs "
      f"{len(_map43.coastlines_km)})")
check(len(_map43.border_meta) == len(_map43.borders_km),
      f"border metadata must be index-aligned ({len(_map43.border_meta)} vs "
      f"{len(_map43.borders_km)})")

# Every metadata box must actually contain its stroke.
_bad44 = []
for _iso44, _rings44 in _map43.country_polys.items():
    for _i44, _r44 in enumerate(_rings44):
        _b44 = _map43.country_meta[_iso44][_i44]
        if any(not (_b44[0] <= _x44 <= _b44[2] and _b44[1] <= _y44 <= _b44[3])
               for _x44, _y44 in _r44):
            _bad44.append(f"{_iso44}[{_i44}]")
check(not _bad44,
      f"every culling box must contain its own stroke (escaped: {_bad44[:5]})")

# At the default 0.8 zoom the operator must still get every vertex. Mirror the
# stride arithmetic in render() rather than restating a threshold, and drive it
# from the real spacing of Thailand's mainland rather than an assumed figure.
def _stride44(seg_km, zoom):
    step = seg_km * zoom
    if step <= 0.0 or step >= _LOD44:
        return 1
    return max(1, int(_LOD44 / step))

_tha44 = max(_map43.country_polys["THA"], key=len)
_seg44 = _meta44(_tha44)[4]
check(_stride44(_seg44, 0.8) == 1,
      f"Thailand's mainland must keep every vertex at the default 0.8 zoom "
      f"(spacing {_seg44:.2f} km -> {_seg44 * 0.8:.2f} px, threshold {_LOD44})")
check(_stride44(_seg44, 5.0) == 1,
      "LOD must never thin when zoomed right in")
check(_stride44(_seg44, 0.1) > 1,
      f"LOD must thin when zoomed out, or the widened theatre blows the frame "
      f"budget (stride at 0.1 zoom: {_stride44(_seg44, 0.1)})")

# Thailand's mainland is the single most favourable stroke in the theatre, so
# asserting on it alone proves almost nothing. The invariant that actually
# bounds the visual damage holds for every stroke at every zoom: the stride is
# FLOORED, so stride * step_px <= LOD_MIN_PX and vertices never end up further
# apart on screen after thinning than the threshold itself. A stroke's overall
# size is irrelevant; its post-thinning vertex spacing is the thing that shows.
_all44 = ([(_m44x, _r44x) for _iso44 in _map43.country_meta
           for _m44x, _r44x in zip(_map43.country_meta[_iso44], _map43.country_polys[_iso44])]
          + list(zip(_map43.coast_meta, _map43.coastlines_km))
          + list(zip(_map43.border_meta, _map43.borders_km)))
_worst44, _at44 = 0.0, None
for _z44 in (0.07, 0.13, 0.3, 0.5, 0.8, 2.0):
    for _m44x, _r44x in _all44:
        _s44 = _stride44(_m44x[4], _z44)
        if _s44 <= 1:
            continue  # untouched: its natural spacing is not thinning damage
        _after44 = _s44 * _m44x[4] * _z44
        if _after44 > _worst44:
            _worst44, _at44 = _after44, _z44
check(_worst44 <= _LOD44 + 1e-9,
      f"post-thinning vertex spacing must never exceed the {_LOD44} px threshold "
      f"at any zoom (worst {_worst44:.3f} px at zoom {_at44})")

# A stroke must never be thinned into something the draw calls then discard.
# A closed island loop repeats its first vertex last, so the "keep the final
# point" step never fires for one and a hard stride used to collapse it to a
# single point - 369 coastlines and 326 country rings did exactly that.
_ring44 = [(_math43.cos(_math43.radians(_i44 * 12)) * 0.4,
            _math43.sin(_math43.radians(_i44 * 12)) * 0.4) for _i44 in range(30)]
_ring44.append(_ring44[0])
_thin44 = _thin44f(_ring44, _meta44(_ring44)[4], 0.001)
check(len(_thin44) >= 4,
      f"a closed loop must never be thinned below four points (got {len(_thin44)})")

_collapsed44 = []
for _m44x, _r44x in _all44:
    if len(_thin44f(_r44x, _m44x[4], 0.07)) < min(3, len(_r44x)):
        _collapsed44.append(len(_r44x))
check(not _collapsed44,
      f"no stroke may collapse below drawable size at the zoom floor "
      f"({len(_collapsed44)} did)")

# A short straight run at the edge of the data is a coincidence, not a cut.
_short44 = [(68.0, 10.0), (68.0, 10.5), (68.4, 10.5), (68.4, 10.0), (68.0, 10.0)]
_far44 = [(68.0, 0.0), (146.0, 0.0), (146.0, 46.0), (100.0, 23.0), (68.0, 0.0)]
_cl44, _ct44 = _detect43([_far44, _short44])
check(68.0 not in _cl44,
      f"a half-degree straight run at the data edge must not be believed as a "
      f"cut (detected meridians: {sorted(_cl44)})")

# 45. Threat rarity, CAP home fields, zoom anchoring
#
# Three gameplay defects, all invisible to the rest of the suite:
#   - spawn rates were hardcoded so hot that ~90 ballistic launches an hour
#     reached the scope
#   - CAPFighter carried its own copy of the airbase coordinates with the
#     latitude sign flipped, launching northern wings south of Bangkok
#   - zoom scaled about the map origin, so panning to Japan and zooming
#     dragged the view back to Bangkok
print("\n=== 45. Threat Rarity, CAP Fields & Zoom Anchoring ===")
import collections as _coll45
from command_center import CommandCenter as _CC45
from profiles import DEFAULT_PROFILE as _PROF45
from targets import CAPFighter as _CAP45, ICBM as _ICBM45, TacticalBM as _TBM45
from targets import AntiRadiationMissile as _ARM45, CruiseMissile as _CRZ45
from targets import Drone as _DRN45, Helicopter as _HEL45, Aircraft as _AC45

# --- rates live in config, not buried in the spawn function ---
for _k45 in ("THREAT_PHASES", "THREAT_WEIGHTS", "THREAT_MAX_PER_HOUR",
             "THREAT_WINDOW_TICKS", "CAP_STATIONS"):
    check(hasattr(GameConfig, _k45), f"GameConfig must expose {_k45}")

# --- the hourly ceiling must actually bind, over a full simulated hour ---
random.seed(1234)
_cmd45 = _CC45(profile=_PROF45)
_counts45 = _coll45.Counter()
_KINDS45 = [(_ICBM45, "ICBM"), (_TBM45, "TBM"), (_ARM45, "ARM"),
            (_CRZ45, "CRUISE"), (_DRN45, "DRONE"), (_HEL45, "HELI")]
for _t45 in range(1, GameConfig.THREAT_WINDOW_TICKS + 1):
    _cmd45.tick_count = _t45
    _n45 = len(_cmd45.unseen_contacts)
    _cmd45.detect_airspace()
    for _c45 in _cmd45.unseen_contacts[_n45:]:
        for _cls45, _name45 in _KINDS45:
            if isinstance(_c45, _cls45):
                _counts45[_name45] += 1
                break
    _cmd45.unseen_contacts = []

for _kind45, _cap45 in sorted(GameConfig.THREAT_MAX_PER_HOUR.items()):
    _got45 = _counts45.get(_kind45, 0)
    check(_got45 <= _cap45,
          f"{_kind45} must respect its {_cap45}/hour ceiling (spawned {_got45})")

_ball45 = _counts45.get("ICBM", 0) + _counts45.get("TBM", 0)
check(_ball45 <= 5,
      f"ballistic launches must stay rare: {_ball45} in one hour, and the "
      f"player reported 5/hour as already unrealistic (was ~90 before the fix)")

# --- CAP fighters launch from their own field ---
_bad45 = []
for _wing45, _ox45, _oy45, _st45 in GameConfig.CAP_STATIONS:
    _cap_obj45 = _CAP45(9999, _wing45, _ox45, _oy45, "test")
    if (_cap_obj45.home_x, _cap_obj45.home_y) != GameConfig.wing_home(_wing45):
        _bad45.append(_wing45)
check(not _bad45,
      f"every CAP station must spawn at its own AIRBASES field (wrong: {_bad45})")

# Korat, Takhli and Ubon are north of Bangkok. The old hardcoded table put all
# three at negative y, several hundred km south of their real fields.
for _wing45 in (1, 4, 21):
    _x45, _y45 = GameConfig.wing_home(_wing45)
    check(_y45 > 0,
          f"Wing {_wing45} must sit north of Bangkok (got y={_y45:+.1f} km)")

# --- more than the original two wings fly CAP ---
random.seed(7)
_cmd45b = _CC45(profile=_PROF45)
_flown45 = set()
for _t45 in range(0, 1200, 5):
    _cmd45b.tick_count = _t45
    _cmd45b.process_reloads()
    for _c45 in list(_cmd45b.contacts):
        if isinstance(_c45, _CAP45):
            _flown45.add(_c45.wing)
            _c45.active = False
            _cmd45b.contacts.remove(_c45)
            _cmd45b.cap_pool += 1
check(len(_flown45) >= 3,
      f"CAP must rotate across wings, not just two hardcoded ones (flew: {sorted(_flown45)})")

# --- zoom must move the camera, not just the scale ---
# Read it out of the source the same way the zoom-floor check does: the wheel
# handler has to compensate the camera, or zoom magnifies about the map origin.
_ui45 = open(os.path.join(_here42, "radar_ui.py"), encoding="utf-8").read()
_wheel45 = _ui45[_ui45.index("pygame.MOUSEWHEEL"):]
_wheel45 = _wheel45[:_wheel45.index("if event.type", 40)]
check("camera_x =" in _wheel45 and "camera_y =" in _wheel45,
      "the mouse-wheel handler must reposition the camera, otherwise zoom "
      "scales about the map origin and drags the view back to Bangkok")
check("get_pos()" in _wheel45,
      "zoom must anchor on the cursor position")

print("\n" + "="*50)
if errors:
    print(f"FAILED: {len(errors)} test(s)")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
else:
    print("ALL TESTS PASSED")


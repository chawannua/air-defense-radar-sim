"""Headless integration test for the air defense simulator logic."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from targets import (AirContact, Aircraft, Helicopter, Drone, TacticalBM, ICBM,
                     Airliner, AWACS, CAPFighter, GhostTrack, EWGhostTrack,
                     AntiRadiationMissile, CruiseMissile, is_line_of_sight_masked)
from command_center import CommandCenter
from personnel import Engagement
import random
import math

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

print("\n" + "="*50)
if errors:
    print(f"FAILED: {len(errors)} test(s)")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
else:
    print("ALL TESTS PASSED")


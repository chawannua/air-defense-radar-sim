"""Headless integration test for the air defense simulator logic."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from targets import (AirContact, Aircraft, Helicopter, Drone, TacticalBM, ICBM,
                     Airliner, AWACS, CAPFighter, GhostTrack, EWGhostTrack)
from command_center import CommandCenter
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

print("\n" + "="*50)
if errors:
    print(f"FAILED: {len(errors)} test(s)")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
else:
    print("ALL TESTS PASSED")

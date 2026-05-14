# config.py
class GameConfig:
    # Real-world RTAF airbase positions in relative km from Bangkok (center of map)
    AIRBASES = [
        (150, 100, "Wing 1 (Korat)", "F-16A/B ADF"),
        (0, 150, "Wing 4 (Takhli)", "F-16AM Fighting Falcon"),
        (20, -350, "Wing 7 (Surat Thani)", "JAS-39C Gripen"),
        (250, 180, "Wing 21 (Ubon)", "F-5TH Super Tigris"),
        (180, 280, "Wing 23 (Udon)", "Alpha Jet")
    ]

    # Hit probabilities - tuned so enemies occasionally punch through
    HIT_CHANCE_THAAD = 0.35
    HIT_CHANCE_SAM_NUKE = 0.10
    HIT_CHANCE_SAM_TBM = 0.15
    HIT_CHANCE_SAM_NORMAL = 0.40
    HIT_CHANCE_F16 = 0.45
    HIT_CHANCE_CIWS = 0.30

    # Weapon speeds (km/tick)
    WEAPON_SPEED_THAAD = 30.0
    WEAPON_SPEED_SAM = 12.0
    WEAPON_SPEED_F16 = 3.5

    # Inventory and reload times
    MAX_AMMO = {"THAAD": 8, "FIGHTER": 15, "SAM": 50, "CIWS": 150}
    RELOAD_TIMES = {"THAAD": 60, "SAM": 25, "CIWS": 10}

    # Weapon preparation times (ticks)
    PREP_TIME_THAAD = 20
    PREP_TIME_SAM = 12
    PREP_TIME_F16 = 10

    # Fighter RTB times after engagement (ticks)
    F16_RTB_TIME_KILL = 15
    F16_RTB_TIME_ASSIST = 10

    # Damage values per contact type reaching the base
    DAMAGE_AIRCRAFT = 10
    DAMAGE_BOMBER = 15
    DAMAGE_TBM = 25
    DAMAGE_ICBM = 80

    # Massive wave settings
    WAVE_CHANCE = 0.20
    WAVE_COOLDOWN_INITIAL = 120
    WAVE_COOLDOWN_AFTER = 180
    WAVE_SIZE_MIN = 10
    WAVE_SIZE_MAX = 18
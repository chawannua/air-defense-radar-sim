# config.py
class GameConfig:
    VERSION = "1.1.0"

    # Real-world RTAF airbase positions in relative km from Bangkok (harmonized with geodata)
    AIRBASES = [
        (148.2, 107.5, "Wing 1 (Korat)"),
        (24.3, 178.6, "Wing 4 (Takhli)"),
        (-149.7, -511.4, "Wing 7 (Surat Thani)"),
        (412.5, 175.4, "Wing 21 (Ubon)"),
        (218.6, 403.2, "Wing 23 (Udon)"),
        (-217.9, 534.3, "Wing 41 (Chiang Mai)"),
        (-164.2, -738.9, "Wing 56 (Hat Yai)")
    ]

    # aircraft assigned to each wing (real RTAF inventory)
    WING_AIRCRAFT = {
        "Wing 1 (Korat)":        ["F-16A Block 15 OCU", "F-16B Block 15 OCU"],
        "Wing 4 (Takhli)":       ["F-16A Block 15 ADF", "F-16B Block 15 ADF"],
        "Wing 7 (Surat Thani)":  ["JAS-39C Gripen", "JAS-39D Gripen"],
        "Wing 21 (Ubon)":        ["F-16A Block 15 OCU", "F-16B Block 15 OCU"],
        "Wing 23 (Udon)":        ["Alpha Jet", "T-50TH Golden Eagle"],
        "Wing 41 (Chiang Mai)":  ["F-5TH Super Tigris", "T-50TH Golden Eagle"],
        "Wing 56 (Hat Yai)":     ["Gripen C/D Detachment", "F-16A ADF"]
    }

    # Hit probabilities - tuned so enemies occasionally punch through
    HIT_CHANCE_THAAD = 0.35
    HIT_CHANCE_SAM_NUKE = 0.10
    HIT_CHANCE_SAM_TBM = 0.15
    HIT_CHANCE_SAM_NORMAL = 0.40
    HIT_CHANCE_F16 = 0.45
    HIT_CHANCE_CIWS = 0.85  # Point-defense burst lethality

    # Weapon speeds (km/tick)
    WEAPON_SPEED_THAAD = 30.0
    WEAPON_SPEED_SAM = 12.0
    WEAPON_SPEED_F16 = 3.5
    WEAPON_SPEED_CIWS = 25.0

    # Inventory and reload times
    MAX_AMMO = {"THAAD": 8, "FIGHTER": 15, "SAM": 50, "CIWS": 150}
    RELOAD_TIMES = {"THAAD": 60, "SAM": 25, "CIWS": 10, "FIGHTER": 45}

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
    DAMAGE_ARM = 35
    DAMAGE_CRUISE = 25

    # Mountain peaks for terrain masking (x_km, y_km, altitude_ft, name)
    MOUNTAIN_PEAKS = [
        (-217.9, 534.3, 8415, "DOI INTHANON 8415FT"),
        (-82.8, -576.3, 6024, "KHAO LUANG 6024FT"),
        (138.5, 345.7, 4301, "PHU KRADUENG 4301FT"),
        (-129.9, -28.3, 3500, "TENASSERIM 3500FT"),
        (162.0, 60.1, 4400, "KHAO YAI 4400FT"),
        (-162.4, 679.3, 7500, "DOI PHA HOM POK 7500FT")
    ]

    # Massive wave settings
    WAVE_CHANCE = 0.20
    WAVE_COOLDOWN_INITIAL = 120
    WAVE_COOLDOWN_AFTER = 180
    WAVE_SIZE_MIN = 10
    WAVE_SIZE_MAX = 18
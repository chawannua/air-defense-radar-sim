# config.py
class GameConfig:
    # --- อัตราความแม่นยำ (Nerfed: ปรับลดลงเพื่อให้ข้าศึกมีโอกาสหลุดมาโจมตีฐานได้มากขึ้น) ---
    HIT_CHANCE_THAAD = 0.35        
    HIT_CHANCE_SAM_NUKE = 0.10     
    HIT_CHANCE_SAM_TBM = 0.15      
    HIT_CHANCE_SAM_NORMAL = 0.40   
    HIT_CHANCE_F16 = 0.45          
    HIT_CHANCE_CIWS = 0.30         

    # --- ความเร็วอาวุธ (Mach/Tick) ---
    WEAPON_SPEED_THAAD = 30.0
    WEAPON_SPEED_SAM = 12.0
    WEAPON_SPEED_F16 = 3.5

    # --- โลจิสติกส์และเวลาบรรจุ (เพิ่มคูลดาวน์เพื่อสร้างช่วงโหว่ในการป้องกัน) ---
    MAX_AMMO = {"THAAD": 8, "F-16": 15, "SAM": 50, "CIWS": 150}
    RELOAD_TIMES = {"THAAD": 60, "SAM": 25, "CIWS": 10} 
    
    # --- เวลาเตรียมยิง (เพิ่มเวลาตอบโต้ให้ช้าลง เพื่อให้ข้าศึกเข้าใกล้ฐานได้มากขึ้น) ---
    PREP_TIME_THAAD = 20
    PREP_TIME_SAM = 12
    PREP_TIME_F16 = 10

    # F-16 RTB times
    F16_RTB_TIME_KILL = 15         
    F16_RTB_TIME_ASSIST = 10       

    # --- ค่าความเสียหายต่อฐาน (Base HP Damage) ---
    DAMAGE_AIRCRAFT = 10
    DAMAGE_BOMBER = 15
    DAMAGE_TBM = 25
    DAMAGE_ICBM = 80               # เกือบ One-shot kill

    # Massive Wave Settings
    WAVE_CHANCE = 0.20
    WAVE_COOLDOWN_INITIAL = 120
    WAVE_COOLDOWN_AFTER = 180
    WAVE_SIZE_MIN = 10
    WAVE_SIZE_MAX = 18
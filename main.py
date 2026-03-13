# main.py
import sys
from radar_ui import start_radar

if __name__ == "__main__":
    print("Initializing Radar UI...")
    try:
        start_radar()
    except KeyboardInterrupt:
        print("\nSimulation Terminated.")
        sys.exit(0)








# # main.py
# import sys
# import os
# from command_center import CommandCenter




# if __name__ == "__main__":
#     # Launch in new terminal window if no argument
#     if len(sys.argv) == 1 or sys.argv[-1] != "--child":
#         script_path = os.path.abspath(sys.argv[0])
        
#         if os.name == 'nt':
#             os.system(f'start cmd /c python "{script_path}" --child')
#         elif sys.platform == 'darwin':
#             os.system(f"""osascript -e 'tell application "Terminal" to do script "python3 \\"{script_path}\\" --child"'""")
#         else:
#             os.system(f'gnome-terminal -- python3 "{script_path}" --child')
#         sys.exit(0)
    
#     game = CommandCenter()
#     try:
#         game.run()
#     except KeyboardInterrupt:
#         print("\n\033[93m[SYS] SIMULATION TERMINATED BY COMMANDER.\033[0m")
#         sys.exit(0)
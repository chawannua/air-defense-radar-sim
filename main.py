# main.py
__version__ = "1.3.2"
import sys
from radar_ui import start_radar

if __name__ == "__main__":
    print("Initializing Radar UI...")
    try:
        start_radar()
    except KeyboardInterrupt:
        print("\nSimulation Terminated.")
        sys.exit(0)
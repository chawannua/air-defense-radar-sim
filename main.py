# main.py
__version__ = "1.8.0"
import sys
import pygame

from radar_ui import start_radar
from scenes import SceneManager, MenuScene

if __name__ == "__main__":
    print("Initializing Radar UI...")
    try:
        pygame.init()
        info = pygame.display.Info()
        width, height = int(info.current_w * 0.9), int(info.current_h * 0.9)
        screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        pygame.display.set_caption("AEGIS Tactical Air Defense C2 - Main Menu")

        manager = SceneManager(screen)
        label, profile = manager.run(MenuScene(width, height))

        if label != "EXIT":
            start_radar(profile=profile)
    except KeyboardInterrupt:
        print("\nSimulation Terminated.")
        sys.exit(0)

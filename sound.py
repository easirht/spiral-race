# sound.py - tiny sound-effect manager (never crashes if audio is unavailable)
import pygame

NAMES = ("click", "dice", "step", "boost", "trap", "win")


class Sfx:
    def __init__(self):
        self.muted = False
        self.sounds = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except Exception:
            return
        vols = {"click": 0.5, "dice": 0.6, "step": 0.35,
                "boost": 0.6, "trap": 0.6, "win": 0.7}
        for n in NAMES:
            try:
                s = pygame.mixer.Sound(f"assets/sounds/{n}.ogg")
                s.set_volume(vols.get(n, 0.6))
                self.sounds[n] = s
            except Exception:
                pass

    def play(self, name):
        if self.muted:
            return
        s = self.sounds.get(name)
        if s is not None:
            try:
                s.play()
            except Exception:
                pass

    def toggle(self):
        self.muted = not self.muted
        if self.muted:
            try:
                pygame.mixer.stop()
            except Exception:
                pass
        return self.muted

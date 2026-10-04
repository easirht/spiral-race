# player.py
import pygame
from theme import lighten, darken

PLAYER_COLORS = {
    "Red": (235, 70, 80),
    "Blue": (70, 140, 245),
    "Green": (70, 205, 120),
    "Yellow": (250, 205, 60),
}


class Player:
    def __init__(self, name, color, is_ai=False):
        self.name = name
        self.color = color
        self.is_ai = is_ai
        self.position = 0
        self.initial = name[0].upper() if name else "?"
        self.x = 0
        self.y = 0


def draw_token(screen, x, y, color, initial, font, radius=15, lift=0):
    x, y = int(x), int(y - lift)
    # shadow stays on the ground while the token hops
    shadow = pygame.Surface((radius * 2 + 8, radius + 6), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, 110), shadow.get_rect())
    screen.blit(shadow, shadow.get_rect(center=(x, y + radius - 2 + int(lift))))
    # outer ring, body, highlight
    pygame.draw.circle(screen, (255, 255, 255), (x, y), radius + 2)
    pygame.draw.circle(screen, darken(color, 0.3), (x, y), radius)
    pygame.draw.circle(screen, color, (x, y), radius - 3)
    pygame.draw.circle(screen, lighten(color, 0.55),
                       (x - radius // 3, y - radius // 3), max(2, radius // 5))
    t = font.render(initial, True, (255, 255, 255))
    screen.blit(t, t.get_rect(center=(x + 1, y + 2)))
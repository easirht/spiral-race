# theme.py
# Visual helpers: background, glowing tiles, text
import math
import random
import pygame
import settings as S


def make_background(w, h):
    """Pre-render a navy gradient with stars once (fast at runtime)."""
    surf = pygame.Surface((w, h))
    top = (14, 22, 52)
    bottom = (6, 9, 24)
    for y in range(h):
        t = y / h
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        pygame.draw.line(surf, color, (0, y), (w, y))
    rng = random.Random(7)
    for _ in range(90):
        x, y = rng.randint(0, w), rng.randint(0, h)
        r = rng.choice([1, 1, 1, 2])
        b = rng.randint(90, 200)
        pygame.draw.circle(surf, (b, b, min(255, b + 40)), (x, y), r)
    return surf


def make_glow(radius, color, max_alpha=110):
    """Soft circular glow surface."""
    size = radius * 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    for r in range(radius, 0, -2):
        a = int(max_alpha * (1 - r / radius) ** 2)
        pygame.draw.circle(surf, (*color, a), (radius, radius), r)
    return surf


def lighten(color, amount):
    return tuple(min(255, int(c + (255 - c) * amount)) for c in color)


def darken(color, amount):
    return tuple(int(c * (1 - amount)) for c in color)


def draw_tile(screen, cx, cy, size, color, number, font, small_font=None, label=None):
    """Rounded tile with shadow, border and top highlight."""
    half = size // 2
    rect = pygame.Rect(cx - half, cy - half, size, size)
    # shadow
    shadow = rect.move(0, 4)
    pygame.draw.rect(screen, (3, 5, 14), shadow, border_radius=12)
    # base (darker edge for depth)
    pygame.draw.rect(screen, darken(color, 0.35), rect.move(0, 2), border_radius=12)
    # main face
    pygame.draw.rect(screen, color, rect, border_radius=12)
    # top highlight
    hl = pygame.Rect(rect.x + 4, rect.y + 3, rect.w - 8, rect.h // 3)
    pygame.draw.rect(screen, lighten(color, 0.25), hl, border_radius=8)
    # border
    pygame.draw.rect(screen, lighten(color, 0.4), rect, 2, border_radius=12)

    if label and small_font:
        t1 = font.render(label, True, S.WHITE)
        screen.blit(t1, t1.get_rect(center=(cx, cy - 4)))
        t2 = small_font.render(str(number), True, lighten(color, 0.7))
        screen.blit(t2, t2.get_rect(center=(cx, cy + 14)))
    else:
        t = font.render(str(number), True, S.WHITE)
        screen.blit(t, t.get_rect(center=(cx, cy)))
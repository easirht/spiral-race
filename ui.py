# ui.py
# Reusable UI drawing helpers
import pygame
import settings as S
import theme


def draw_button(screen, rect, text, font, enabled=True, color=S.GREEN):
    hover = enabled and rect.collidepoint(pygame.mouse.get_pos())
    pressed = hover and pygame.mouse.get_pressed()[0]
    base = color if enabled else (58, 68, 100)
    if hover:
        base = theme.lighten(base, 0.15)
    r = rect.move(0, 3 if pressed else 0)
    pygame.draw.rect(screen, theme.darken(base, 0.5), rect.move(0, 5), border_radius=18)
    pygame.draw.rect(screen, base, r, border_radius=18)
    hl = pygame.Rect(r.x + 8, r.y + 5, r.w - 16, r.h // 3)
    pygame.draw.rect(screen, theme.lighten(base, 0.2), hl, border_radius=12)
    pygame.draw.rect(screen, theme.lighten(base, 0.45), r, 2, border_radius=18)
    col = S.WHITE if enabled else (140, 150, 180)
    t = font.render(text, True, col)
    screen.blit(t, t.get_rect(center=r.center))


def draw_card(screen, rect, color, number, label, num_font, label_font):
    hover = rect.collidepoint(pygame.mouse.get_pos())
    r = rect.inflate(16, 16) if hover else rect
    pygame.draw.rect(screen, theme.darken(color, 0.55), r.move(0, 6), border_radius=24)
    pygame.draw.rect(screen, color, r, border_radius=24)
    hl = pygame.Rect(r.x + 10, r.y + 8, r.w - 20, r.h // 4)
    pygame.draw.rect(screen, theme.lighten(color, 0.2), hl, border_radius=16)
    pygame.draw.rect(screen, theme.lighten(color, 0.5), r, 3, border_radius=24)
    n = num_font.render(str(number), True, S.WHITE)
    screen.blit(n, n.get_rect(center=(r.centerx, r.centery - 14)))
    l = label_font.render(label, True, S.WHITE)
    screen.blit(l, l.get_rect(center=(r.centerx, r.bottom - 44)))


def draw_panel(screen, rect):
    pygame.draw.rect(screen, (18, 28, 60), rect, border_radius=18)
    pygame.draw.rect(screen, (70, 92, 150), rect, 2, border_radius=18)
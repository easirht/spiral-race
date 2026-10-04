# main.py
import asyncio
import math
import random
import sys
import pygame
import settings as S
import theme
import ui
from board import Board, TOTAL_CELLS
from player import Player, PLAYER_COLORS, draw_token
from particles import Particles

IS_WEB = sys.platform == "emscripten"
if IS_WEB:
    import platform

COLOR_NAMES = ["Red", "Blue", "Green", "Yellow"]
MAX_NAME = 12

# Timings (seconds)
STEP_TIME = 0.10
ROLL_TIME = 0.8
AI_THINK = 0.8
EFFECT_TIME = 0.8
END_TURN_PAUSE = 0.35
FLASH_TIME = 0.35
CONFETTI_TIME = 4.0

TILE = 42
CORE_TILE = 58
TOKEN_R = 15

# Turn phases
IDLE, ROLLING, MOVING, EFFECT_MSG, EFFECT_MOVING, END_TURN, WON = range(7)


class App:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((S.WIDTH, S.HEIGHT))
        pygame.display.set_caption(S.TITLE)
        self.clock = pygame.time.Clock()

        self.font = pygame.font.Font(None, 26)
        self.small_font = pygame.font.Font(None, 16)
        self.core_font = pygame.font.Font(None, 20)
        self.token_font = pygame.font.Font(None, 22)
        self.text_font = pygame.font.Font(None, 30)
        self.head_font = pygame.font.Font(None, 40)
        self.title_font = pygame.font.Font(None, 52)
        self.big_font = pygame.font.Font(None, 120)
        self.banner_font = pygame.font.Font(None, 72)
        self.logo_font = pygame.font.Font(None, 150)
        for f in (self.head_font, self.title_font, self.big_font,
                  self.banner_font, self.logo_font):
            f.set_bold(True)

        self.state = S.MAIN_MENU
        self.running = True
        self.time = 0.0

        self.board = Board(400, 370)
        self.board.randomize(0)
        self.seed = 0
        self.bg = theme.make_background(S.WIDTH, S.HEIGHT)
        self.spiral_deco = self.make_spiral_deco()
        self.glow_gold = theme.make_glow(110, S.GOLD, 140)
        self.glow_green = theme.make_glow(32, S.GREEN, 90)
        self.glow_red = theme.make_glow(32, S.RED, 90)

        self.panel = pygame.Surface((400, 560), pygame.SRCALPHA)
        pygame.draw.rect(self.panel, (18, 28, 60, 205), self.panel.get_rect(), border_radius=20)
        pygame.draw.rect(self.panel, (70, 92, 150, 255), self.panel.get_rect(), 2, border_radius=20)

        # Effects
        self.fx = Particles()
        self.flash_surf = pygame.Surface((S.WIDTH, S.HEIGHT))
        self.flash_col = (0, 0, 0)
        self.flash_t = 0.0
        self.win_t = 0.0

        cx = S.WIDTH // 2
        self.roll_btn = pygame.Rect(820, 570, 400, 70)
        self.again_btn = pygame.Rect(cx - 130, 470, 260, 64)
        self.win_menu_btn = pygame.Rect(cx - 130, 550, 260, 64)
        self.play_btn = pygame.Rect(cx - 160, 380, 320, 64)
        self.how_btn = pygame.Rect(cx - 160, 460, 320, 64)
        self.exit_btn = pygame.Rect(cx - 160, 540, 320, 64)
        self.count_rects = [pygame.Rect(195 + i * 230, 240, 200, 220) for i in range(4)]
        self.back_btn = pygame.Rect(cx - 130, 560, 260, 64)
        self.setup_back = pygame.Rect(cx - 270, 620, 250, 64)
        self.setup_start = pygame.Rect(cx + 20, 620, 250, 64)
        self.how_back = pygame.Rect(cx - 130, 610, 260, 64)

        self.particles = [[random.uniform(0, S.WIDTH), random.uniform(0, S.HEIGHT),
                           random.uniform(8, 28), random.choice([1, 2, 2, 3]),
                           random.uniform(0, 6)] for _ in range(45)]

        self.setup = []
        self.n_humans = 2
        self.focus = 0

        self.players = []
        self.phase = IDLE
        self.banner_t = 0.0
        self.banner = None
        self.triggered = set()

    # ---------- decorative ----------
    def make_spiral_deco(self):
        surf = pygame.Surface((S.WIDTH, S.HEIGHT), pygame.SRCALPHA)
        cx, cy = S.WIDTH // 2, S.HEIGHT // 2
        pts = []
        theta_max = 4.2 * 2 * math.pi
        steps = 600
        for k in range(steps):
            th = theta_max * (1 - k / steps)
            r = 20 + 560 * th / theta_max
            ang = -th
            pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        pygame.draw.lines(surf, (70, 100, 180, 45), False, pts, 5)
        return surf

    def update_particles(self, dt):
        for p in self.particles:
            p[1] -= p[2] * dt
            if p[1] < -5:
                p[1] = S.HEIGHT + 5
                p[0] = random.uniform(0, S.WIDTH)

    def draw_menu_bg(self):
        self.screen.blit(self.bg, (0, 0))
        self.screen.blit(self.spiral_deco, (0, 0))
        for p in self.particles:
            a = int(110 + 90 * math.sin(self.time * 2 + p[4]))
            pygame.draw.circle(self.screen, (a, a, min(255, a + 40)),
                               (int(p[0]), int(p[1])), p[3])

    def draw_title(self, text, y=70):
        t = self.title_font.render(text, True, S.GOLD)
        self.screen.blit(t, t.get_rect(center=(S.WIDTH // 2, y)))

    def draw_button(self, rect, text, enabled=True, color=S.GREEN):
        ui.draw_button(self.screen, rect, text, self.head_font, enabled, color)

    # ---------- game flow ----------
    def start_game(self):
        players = []
        for i, row in enumerate(self.setup):
            name = row["name"].strip()
            if not name:
                name = "Computer" if row["ai"] else f"Player {i + 1}"
            players.append(Player(name, PLAYER_COLORS[COLOR_NAMES[row["color"]]], row["ai"]))
        self.players = players
        self.reset_game()
        self.state = S.GAME

    def reset_game(self):
        # New random BOOST/TRAP layout every game
        self.seed = random.randrange(1 << 30)
        self.board.randomize(self.seed)
        start = self.board.get_cell(0)
        for p in self.players:
            p.position = 0
            p.x, p.y = start.x, start.y
        self.current = 0
        self.dice_shown = None
        self.roller = None
        self.winner = None
        self.banner = None
        self.banner_t = 0.0
        self.hop = 0.0
        self.path = []
        self.pending = 0
        self.fx.clear()
        self.flash_t = 0.0
        self.win_t = 0.0
        self.start_turn()

    def cur(self):
        return self.players[self.current]

    def start_turn(self):
        self.phase = IDLE
        self.triggered = set()
        self.timer = AI_THINK if self.cur().is_ai else 0.0

    def can_roll(self):
        return self.phase == IDLE and not self.cur().is_ai

    def start_roll(self):
        self.phase = ROLLING
        self.timer = ROLL_TIME
        self.tick = 0.0
        self.final_roll = random.randint(1, 6)
        self.roller = self.cur()

    def set_banner(self, title, sub, color, dur=1.2):
        self.banner = (title, sub, color)
        self.banner_t = dur

    def do_flash(self, color):
        self.flash_col = color
        self.flash_t = FLASH_TIME

    def after_roll(self):
        p = self.cur()
        target = p.position + self.final_roll
        if target > TOTAL_CELLS:
            self.set_banner("EXACT ROLL!", f"Need exactly {TOTAL_CELLS - p.position} to reach the Core", S.WHITE, 1.0)
            self.phase = END_TURN
            self.timer = 1.0
            return
        self.begin_move(list(range(p.position + 1, target + 1)), MOVING)

    def begin_move(self, path, phase):
        self.path = path
        self.phase = phase
        self.seg_t = 0.0
        p = self.cur()
        self.seg_from = (p.x, p.y)
        if not path:
            self.finish_move()

    def update_move(self, dt):
        p = self.cur()
        if not self.path:
            self.finish_move()
            return
        self.seg_t += dt / STEP_TIME
        cell = self.board.get_cell(self.path[0])
        if self.seg_t >= 1:
            p.x, p.y = cell.x, cell.y
            p.position = self.path.pop(0)
            self.seg_t = 0.0
            self.seg_from = (p.x, p.y)
            self.hop = 0.0
            if not self.path:
                self.finish_move()
        else:
            t = self.seg_t
            t = t * t * (3 - 2 * t)
            p.x = self.seg_from[0] + (cell.x - self.seg_from[0]) * t
            p.y = self.seg_from[1] + (cell.y - self.seg_from[1]) * t
            self.hop = math.sin(self.seg_t * math.pi) * 9

    def finish_move(self):
        p = self.cur()
        self.hop = 0.0
        if p.position == TOTAL_CELLS:
            self.winner = p
            self.phase = WON
            self.win_t = 0.0
            self.fx.burst(p.x, p.y, S.GOLD, n=70, speed=280, gravity=180, size=(3, 6), life=(0.7, 1.4))
            self.fx.burst(p.x, p.y, S.WHITE, n=30, speed=200, gravity=120, life=(0.5, 1.0))
            self.fx.ring(p.x, p.y, S.GOLD, max_r=120, life=0.9)
            return

        if self.phase == EFFECT_MOVING:
            col = S.GREEN if self.pending > 0 else S.RED
            self.fx.burst(p.x, p.y, col, n=12, speed=110)

        # Chain reaction: each cell can trigger only once per turn.
        eff = self.board.get_cell(p.position).effect
        if eff != 0 and p.position not in self.triggered:
            self.triggered.add(p.position)
            self.pending = eff
            if eff > 0:
                self.set_banner(f"BOOST! +{eff}", f"Move {eff} steps forward", S.GREEN, 1.4)
                self.fx.burst(p.x, p.y, S.GREEN, n=30, speed=190, gravity=-60)
                self.fx.ring(p.x, p.y, S.GREEN)
                self.do_flash((20, 120, 60))
            else:
                self.set_banner(f"TRAP! {eff}", f"Move {-eff} steps backward", S.RED, 1.4)
                self.fx.burst(p.x, p.y, S.RED, n=30, speed=190, gravity=320)
                self.fx.ring(p.x, p.y, S.RED)
                self.do_flash((150, 25, 35))
            self.phase = EFFECT_MSG
            self.timer = EFFECT_TIME
            return

        self.phase = END_TURN
        self.timer = END_TURN_PAUSE

    def start_effect_move(self):
        p = self.cur()
        target = max(0, min(TOTAL_CELLS, p.position + self.pending))
        if target >= p.position:
            path = list(range(p.position + 1, target + 1))
        else:
            path = list(range(p.position - 1, target - 1, -1))
        self.begin_move(path, EFFECT_MOVING)

    def next_turn(self):
        self.current = (self.current + 1) % len(self.players)
        self.start_turn()

    # ---------- setup helpers ----------
    def open_setup(self, n):
        self.n_humans = n
        if n == 1:
            self.setup = [
                {"name": "", "color": 0, "ai": False},
                {"name": "Nova", "color": 3, "ai": True},
            ]
        else:
            self.setup = [{"name": "", "color": i, "ai": False} for i in range(n)]
        self.focus = 0
        self.state = S.PLAYER_SETUP

    def row_rect(self, i):
        return pygame.Rect(240, 110 + i * 104, 800, 92)

    def name_rect(self, i):
        r = self.row_rect(i)
        return pygame.Rect(r.x + 250, r.y + 22, 270, 48)

    def swatch_center(self, i, k):
        r = self.row_rect(i)
        return (r.x + 580 + k * 58, r.centery)

    def pick_color(self, i, c):
        for j, row in enumerate(self.setup):
            if j != i and row["color"] == c:
                row["color"] = self.setup[i]["color"]
        self.setup[i]["color"] = c

    @staticmethod
    def is_touch():
        if not IS_WEB:
            return False
        try:
            return bool(platform.window.matchMedia("(pointer: coarse)").matches)
        except Exception:
            return False

    def ask_name(self, i):
        """On phones there is no keyboard for the canvas, so use a popup box."""
        row = self.setup[i]
        try:
            res = platform.window.prompt("Enter name (max 12 letters):", row["name"])
        except Exception:
            res = None
        if res is not None:
            row["name"] = str(res).strip()[:MAX_NAME]

    # ---------- input ----------
    @staticmethod
    def clicked(event, rect):
        return (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and rect.collidepoint(event.pos))

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue
            if self.state == S.MAIN_MENU:
                self.ev_menu(event)
            elif self.state == S.PLAYER_COUNT:
                self.ev_count(event)
            elif self.state == S.PLAYER_SETUP:
                self.ev_setup(event)
            elif self.state == S.HOW_TO_PLAY:
                self.ev_how(event)
            elif self.state == S.GAME:
                self.ev_game(event)

    def ev_menu(self, event):
        if self.clicked(event, self.play_btn):
            self.state = S.PLAYER_COUNT
        elif self.clicked(event, self.how_btn):
            self.state = S.HOW_TO_PLAY
        elif self.clicked(event, self.exit_btn):
            self.running = False

    def ev_count(self, event):
        for i, r in enumerate(self.count_rects):
            if self.clicked(event, r):
                self.open_setup(i + 1)
                return
        if self.clicked(event, self.back_btn) or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            self.state = S.MAIN_MENU

    def ev_setup(self, event):
        if self.clicked(event, self.setup_back):
            self.state = S.PLAYER_COUNT
            return
        if self.clicked(event, self.setup_start):
            self.start_game()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i in range(len(self.setup)):
                if self.name_rect(i).collidepoint(event.pos):
                    self.focus = i
                    if self.is_touch():
                        self.ask_name(i)
                        return
                for k in range(4):
                    cx, cy = self.swatch_center(i, k)
                    if math.hypot(event.pos[0] - cx, event.pos[1] - cy) <= 22:
                        self.pick_color(i, k)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = S.PLAYER_COUNT
            elif event.key == pygame.K_RETURN:
                self.start_game()
            elif event.key == pygame.K_TAB:
                self.focus = (self.focus + 1) % len(self.setup)
            elif event.key == pygame.K_BACKSPACE:
                row = self.setup[self.focus]
                row["name"] = row["name"][:-1]
            elif event.unicode and event.unicode.isprintable():
                row = self.setup[self.focus]
                if len(row["name"]) < MAX_NAME:
                    row["name"] += event.unicode

    def ev_how(self, event):
        if self.clicked(event, self.how_back) or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            self.state = S.MAIN_MENU

    def ev_game(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = S.MAIN_MENU
            elif event.key == pygame.K_SPACE:
                if self.can_roll():
                    self.start_roll()
                elif self.phase == WON:
                    self.reset_game()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.can_roll() and self.roll_btn.collidepoint(event.pos):
                self.start_roll()
            elif self.phase == WON:
                if self.again_btn.collidepoint(event.pos):
                    self.reset_game()
                elif self.win_menu_btn.collidepoint(event.pos):
                    self.state = S.MAIN_MENU

    # ---------- update ----------
    def update(self, dt):
        self.time += dt
        self.update_particles(dt)
        if self.state != S.GAME:
            return
        self.fx.update(dt, S.HEIGHT)
        if self.banner_t > 0:
            self.banner_t -= dt
        if self.flash_t > 0:
            self.flash_t -= dt

        if self.phase == WON:
            self.win_t += dt
            if self.win_t < CONFETTI_TIME:
                self.fx.confetti(S.WIDTH, 3)
            return

        if self.phase == IDLE:
            if self.cur().is_ai:
                self.timer -= dt
                if self.timer <= 0:
                    self.start_roll()
        elif self.phase == ROLLING:
            self.timer -= dt
            self.tick -= dt
            if self.tick <= 0:
                self.dice_shown = random.randint(1, 6)
                self.tick = 0.07
            if self.timer <= 0:
                self.dice_shown = self.final_roll
                self.after_roll()
        elif self.phase in (MOVING, EFFECT_MOVING):
            self.update_move(dt)
        elif self.phase == EFFECT_MSG:
            self.timer -= dt
            if self.timer <= 0:
                self.start_effect_move()
        elif self.phase == END_TURN:
            self.timer -= dt
            if self.timer <= 0:
                self.next_turn()

    # ---------- drawing: game ----------
    def draw_board(self):
        cells = self.board.cells
        pts = [(c.x, c.y) for c in cells]
        pygame.draw.lines(self.screen, (8, 12, 30), False, pts, 12)
        pygame.draw.lines(self.screen, (44, 62, 110), False, pts, 6)

        pulse = 1.0 + 0.06 * math.sin(self.time * 3)
        g = pygame.transform.smoothscale(
            self.glow_gold, (int(220 * pulse), int(220 * pulse)))
        core = cells[-1]
        self.screen.blit(g, g.get_rect(center=(core.x, core.y)))

        s = self.board.get_cell(0)
        theme.draw_tile(self.screen, int(s.x), int(s.y), TILE, S.GREEN, "GO", self.core_font)

        for c in cells:
            if c.position == TOTAL_CELLS:
                continue
            if c.effect > 0:
                color, glow = S.GREEN, self.glow_green
                label = f"+{c.effect}"
            elif c.effect < 0:
                color, glow = S.RED, self.glow_red
                label = f"{c.effect}"
            else:
                color, glow, label = (52, 68, 112), None, None
            if glow:
                self.screen.blit(glow, glow.get_rect(center=(c.x, c.y)))
            theme.draw_tile(self.screen, int(c.x), int(c.y), TILE, color,
                            c.position, self.font, self.small_font, label)

        theme.draw_tile(self.screen, int(core.x), int(core.y), CORE_TILE, S.GOLD,
                        "CORE", self.core_font)

    def draw_tokens(self):
        order = [p for p in self.players if p is not self.cur()] + [self.cur()]
        offsets = [(-9, -7), (9, -7), (-9, 9), (9, 9)]
        for p in order:
            shared = any(o is not p and o.position == p.position for o in self.players)
            idx = self.players.index(p)
            ox, oy = offsets[idx] if shared else (0, 0)
            lift = self.hop if p is self.cur() and self.phase in (MOVING, EFFECT_MOVING) else 0
            draw_token(self.screen, p.x + ox, p.y + oy - 6, p.color, p.initial,
                       self.token_font, TOKEN_R, lift)

    def draw_ui(self):
        a = self.title_font.render("SPIRAL", True, S.WHITE)
        b = self.title_font.render(" RACE", True, S.GOLD)
        self.screen.blit(a, (28, 22))
        self.screen.blit(b, (28 + a.get_width(), 22))

        p = self.cur()
        txt = f"{self.winner.name} wins!" if self.phase == WON else f"{p.name}'s Turn"
        t = self.head_font.render(txt, True, S.WHITE)
        tx = 820
        draw_token(self.screen, tx + 16, 44, p.color, p.initial, self.token_font, 14)
        self.screen.blit(t, (tx + 44, 30))

        self.screen.blit(self.panel, (820, 80))
        h = self.head_font.render("PLAYERS", True, S.GOLD)
        self.screen.blit(h, (845, 98))

        for i, pl in enumerate(self.players):
            r = pygame.Rect(840, 148 + i * 56, 360, 48)
            active = pl is p and self.phase != WON
            fill = (44, 62, 112) if active else (26, 38, 78)
            pygame.draw.rect(self.screen, fill, r, border_radius=14)
            if active:
                glow = 0.5 + 0.5 * math.sin(self.time * 4)
                col = theme.lighten(pl.color, 0.2 * glow)
                pygame.draw.rect(self.screen, col, r, 3, border_radius=14)
            draw_token(self.screen, r.x + 28, r.centery - 2, pl.color, pl.initial, self.token_font, 13)
            nm = self.text_font.render(pl.name + ("  (AI)" if pl.is_ai else ""), True, S.WHITE)
            self.screen.blit(nm, (r.x + 56, r.y + 14))
            ps = self.text_font.render(f"Pos {pl.position}", True, theme.lighten(pl.color, 0.3))
            self.screen.blit(ps, ps.get_rect(midright=(r.right - 16, r.centery)))

        box = pygame.Rect(840, 400, 360, 150)
        pygame.draw.rect(self.screen, (10, 16, 40), box, border_radius=18)
        pygame.draw.rect(self.screen, (70, 92, 150), box, 2, border_radius=18)
        if self.phase == ROLLING:
            label = "ROLLING..."
        elif self.phase == IDLE and p.is_ai:
            label = f"{p.name.upper()} IS THINKING..."
        elif self.phase == IDLE and self.dice_shown is None:
            label = "ROLL THE DICE"
        elif self.roller is not None:
            label = f"{self.roller.name.upper()} ROLLED"
        else:
            label = ""
        lt = self.text_font.render(label, True, S.WHITE)
        self.screen.blit(lt, lt.get_rect(center=(box.centerx, box.y + 26)))
        val = str(self.dice_shown) if self.dice_shown else "-"
        col = S.GOLD if self.phase != ROLLING else S.WHITE
        n = self.big_font.render(val, True, col)
        self.screen.blit(n, n.get_rect(center=(box.centerx, box.y + 92)))

        self.draw_button(self.roll_btn, "ROLL", self.can_roll())

    def draw_banner(self):
        if self.banner_t <= 0 or not self.banner:
            return
        title, sub, color = self.banner
        a = min(1.0, self.banner_t / 0.3)
        t = self.banner_font.render(title, True, color)
        s = self.text_font.render(sub, True, S.WHITE)
        t.set_alpha(int(255 * a))
        s.set_alpha(int(255 * a))
        self.screen.blit(t, t.get_rect(center=(400, 70)))
        self.screen.blit(s, s.get_rect(center=(400, 112)))

    def draw_flash(self):
        if self.flash_t <= 0:
            return
        self.flash_surf.fill(self.flash_col)
        self.flash_surf.set_alpha(int(80 * self.flash_t / FLASH_TIME))
        self.screen.blit(self.flash_surf, (0, 0))

    def draw_win(self):
        dim = pygame.Surface((S.WIDTH, S.HEIGHT), pygame.SRCALPHA)
        dim.fill((4, 8, 22, 190))
        self.screen.blit(dim, (0, 0))
        w = self.winner
        bob = math.sin(self.time * 3) * 5
        draw_token(self.screen, S.WIDTH // 2, 200 + bob, w.color, w.initial, self.head_font, 44)
        t = self.banner_font.render("WINNER!", True, S.GOLD)
        self.screen.blit(t, t.get_rect(center=(S.WIDTH // 2, 300)))
        n = self.big_font.render(w.name.upper(), True, S.WHITE)
        n = pygame.transform.smoothscale(n, (n.get_width() * 55 // 100, n.get_height() * 55 // 100))
        self.screen.blit(n, n.get_rect(center=(S.WIDTH // 2, 380)))
        r = self.text_font.render("Reached the Core!", True, S.WHITE)
        self.screen.blit(r, r.get_rect(center=(S.WIDTH // 2, 430)))
        self.draw_button(self.again_btn, "PLAY AGAIN", True, S.GOLD)
        self.draw_button(self.win_menu_btn, "MAIN MENU", True, (70, 110, 200))

    # ---------- drawing: menus ----------
    def draw_main_menu(self):
        self.draw_menu_bg()
        cx = S.WIDTH // 2
        a = self.logo_font.render("SPIRAL", True, S.WHITE)
        b = self.logo_font.render("RACE", True, S.GOLD)
        bob = math.sin(self.time * 2) * 4
        self.screen.blit(a, a.get_rect(center=(cx, 105 + bob)))
        self.screen.blit(b, b.get_rect(center=(cx, 215 + bob)))
        s = self.head_font.render("Race to the Core", True, (170, 190, 235))
        self.screen.blit(s, s.get_rect(center=(cx, 305)))
        self.draw_button(self.play_btn, "PLAY")
        self.draw_button(self.how_btn, "HOW TO PLAY", True, (70, 110, 200))
        self.draw_button(self.exit_btn, "EXIT", True, S.RED)

    def draw_player_count(self):
        self.draw_menu_bg()
        self.draw_title("SELECT NUMBER OF PLAYERS", 130)
        for i, r in enumerate(self.count_rects):
            color = PLAYER_COLORS[COLOR_NAMES[i]]
            ui.draw_card(self.screen, r, color, i + 1,
                         "PLAYER" if i == 0 else "PLAYERS",
                         self.big_font, self.text_font)
        sub = self.text_font.render("1 Player = you vs. the computer", True, (170, 190, 235))
        self.screen.blit(sub, sub.get_rect(center=(S.WIDTH // 2, 500)))
        self.draw_button(self.back_btn, "BACK", True, (70, 110, 200))

    def draw_setup(self):
        self.draw_menu_bg()
        self.draw_title("PLAYER SETUP", 60)
        for i, row in enumerate(self.setup):
            r = self.row_rect(i)
            ui.draw_panel(self.screen, r)
            color = PLAYER_COLORS[COLOR_NAMES[row["color"]]]
            shown = row["name"].strip() or ("Computer" if row["ai"] else f"Player {i + 1}")
            draw_token(self.screen, r.x + 44, r.centery - 2, color, shown[0].upper(),
                       self.token_font, 18)
            if self.n_humans == 1:
                label = "AI OPPONENT" if row["ai"] else "YOUR PLAYER"
            else:
                label = f"PLAYER {i + 1}"
            lt = self.text_font.render(label, True, S.WHITE)
            self.screen.blit(lt, lt.get_rect(midleft=(r.x + 80, r.centery)))

            nr = self.name_rect(i)
            pygame.draw.rect(self.screen, (10, 16, 40), nr, border_radius=12)
            border = S.GOLD if self.focus == i else (70, 92, 150)
            pygame.draw.rect(self.screen, border, nr, 2, border_radius=12)
            if row["name"]:
                txt = row["name"]
                tcol = S.WHITE
            else:
                txt = "Computer" if row["ai"] else f"Player {i + 1}"
                tcol = (100, 115, 160)
            caret = "|" if (self.focus == i and int(self.time * 2) % 2 == 0) else ""
            if row["name"]:
                txt += caret
            ts = self.text_font.render(txt, True, tcol)
            self.screen.blit(ts, ts.get_rect(midleft=(nr.x + 14, nr.centery)))
            if not row["name"] and caret:
                cs = self.text_font.render("|", True, S.WHITE)
                self.screen.blit(cs, cs.get_rect(midleft=(nr.x + 8, nr.centery)))

            for k in range(4):
                c = PLAYER_COLORS[COLOR_NAMES[k]]
                sx, sy = self.swatch_center(i, k)
                if row["color"] == k:
                    pygame.draw.circle(self.screen, S.WHITE, (sx, sy), 23)
                pygame.draw.circle(self.screen, theme.darken(c, 0.3), (sx, sy), 19)
                pygame.draw.circle(self.screen, c, (sx, sy), 16)
                pygame.draw.circle(self.screen, theme.lighten(c, 0.5), (sx - 5, sy - 5), 4)
        msg = ("Tap a name box to type your name. Colors can't repeat."
               if self.is_touch() else
               "Click a name box and type. Colors can't repeat. Empty name = default.")
        hint = self.small_font.render(msg, True, (150, 170, 215))
        self.screen.blit(hint, hint.get_rect(center=(S.WIDTH // 2, 592)))
        self.draw_button(self.setup_back, "BACK", True, (70, 110, 200))
        self.draw_button(self.setup_start, "START GAME", True, S.GREEN)

    def draw_how(self):
        self.draw_menu_bg()
        self.draw_title("HOW TO PLAY", 70)
        items = [
            ("dice", "Roll the dice: 1 to 6"),
            ("path", "Move along the spiral path"),
            ("green", "Green BOOST cells push you forward"),
            ("red", "Red TRAP cells push you backward"),
            ("core", "Reach the Core (50) exactly to win"),
        ]
        navy = (52, 68, 112)
        for i, (kind, text) in enumerate(items):
            y = 170 + i * 82
            cx = 400
            if kind == "dice":
                theme.draw_tile(self.screen, cx, y, 52, navy, "1-6", self.font)
            elif kind == "path":
                theme.draw_tile(self.screen, cx - 30, y, 46, navy, "1", self.font)
                theme.draw_tile(self.screen, cx + 30, y, 46, navy, "2", self.font)
            elif kind == "green":
                theme.draw_tile(self.screen, cx, y, 52, S.GREEN, 5, self.font, self.small_font, "+3")
            elif kind == "red":
                theme.draw_tile(self.screen, cx, y, 52, S.RED, 9, self.font, self.small_font, "-2")
            else:
                theme.draw_tile(self.screen, cx, y, 52, S.GOLD, "CORE", self.core_font)
            t = self.text_font.render(text, True, S.WHITE)
            self.screen.blit(t, t.get_rect(midleft=(490, y)))
        self.draw_button(self.how_back, "BACK", True, (70, 110, 200))

    def draw(self):
        if self.state == S.MAIN_MENU:
            self.draw_main_menu()
        elif self.state == S.PLAYER_COUNT:
            self.draw_player_count()
        elif self.state == S.PLAYER_SETUP:
            self.draw_setup()
        elif self.state == S.HOW_TO_PLAY:
            self.draw_how()
        elif self.state == S.GAME:
            self.screen.blit(self.bg, (0, 0))
            self.draw_board()
            self.draw_tokens()
            self.draw_flash()
            self.draw_ui()
            self.draw_banner()
            if self.phase == WON:
                self.draw_win()
            self.fx.draw(self.screen)
        pygame.display.flip()


async def main():
    app = App()
    while app.running:
        dt = min(app.clock.tick(S.FPS) / 1000, 0.05)
        app.handle_events()
        app.update(dt)
        app.draw()
        await asyncio.sleep(0)
    pygame.quit()


asyncio.run(main())
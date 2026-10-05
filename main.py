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
from net import Net
from sound import Sfx

IS_WEB = sys.platform == "emscripten"
if IS_WEB:
    import platform

ONLINE_MENU = "ONLINE_MENU"
ONLINE_LOBBY = "ONLINE_LOBBY"
SITE = "https://easirht.github.io/spiral-race/"

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
(IDLE, ROLLING, MOVING, EFFECT_MSG, EFFECT_MOVING,
 END_TURN, WON, WAIT_ROLL, WAIT_TURN) = range(9)


class App:
    def __init__(self):
        pygame.init()
        self.landscape = True
        self.W, self.H = S.WIDTH, S.HEIGHT
        self.screen = pygame.display.set_mode((self.W, self.H))
        pygame.display.set_caption(S.TITLE)
        self.clock = pygame.time.Clock()
        self.sfx = Sfx()

        self.font = pygame.font.Font(None, 26)
        self.small_font = pygame.font.Font(None, 18)
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
        self.seed = 0
        self.board = None

        # Effects
        self.fx = Particles()
        self.flash_col = (0, 0, 0)
        self.flash_t = 0.0
        self.win_t = 0.0
        self.glow_gold = theme.make_glow(110, S.GOLD, 140)
        self.glow_green = theme.make_glow(32, S.GREEN, 90)
        self.glow_red = theme.make_glow(32, S.RED, 90)

        self.setup = []
        self.n_humans = 2
        self.focus = 0

        self.players = []
        self.phase = IDLE
        self.current = 0
        self.banner_t = 0.0
        self.banner = None
        self.triggered = set()
        self.path = []
        self.seg_t = 0.0
        self.seg_from = (0, 0)
        self.hop = 0.0
        self.pending = 0
        self.dice_shown = None
        self.roller = None
        self.winner = None
        self.timer = 0.0

        # Online
        self.net = Net()
        self.online = False
        self.me = 0
        self.lobby = {"code": "", "players": [], "started": False}
        self.net_name = ""
        self.net_code = ""
        self.net_focus = 0
        self.net_msg = ""
        self.inbox = []
        self.copied_t = 0.0
        self.toast = ("", 0.0)
        self.size_t = 0.0

        self.build_layout(True)

        if IS_WEB:
            self.net.warm()  # wake the free server early
            room = self.net.room_param()
            if room:
                self.net_code = room
                self.net_msg = "You are invited! Type your name, then press JOIN ROOM."
                self.state = ONLINE_MENU

    # ================= layout (landscape / portrait) =================
    def build_layout(self, landscape):
        self.landscape = landscape
        L = landscape
        W, H = (1280, 720) if L else (720, 1280)
        self.W, self.H = W, H
        if self.screen.get_size() != (W, H):
            self.screen = pygame.display.set_mode((W, H))
        cx = W // 2

        # board
        self.board = Board(400, 370) if L else Board(360, 466)
        self.board.randomize(self.seed)

        # pre-rendered surfaces
        self.bg = theme.make_background(W, H)
        self.spiral_deco = self.make_spiral_deco()
        self.flash_surf = pygame.Surface((W, H))
        if L:
            self.panel_pos = (820, 80)
            self.panel = self.make_panel(400, 560)
        else:
            self.panel_pos = (8, 808)
            self.panel = self.make_panel(704, 466)

        # in-game
        self.title_pos = (28, 22) if L else (24, 16)
        self.turn_tok = (836, 44) if L else (40, 104)
        self.turn_txt = (864, 30) if L else (68, 88)
        self.banner_pos = ((400, 70), (400, 112)) if L else ((360, 150), (360, 192))
        self.dice_box = pygame.Rect(840, 400, 360, 150) if L else pygame.Rect(24, 1048, 306, 200)
        self.roll_btn = pygame.Rect(820, 570, 400, 70) if L else pygame.Rect(350, 1048, 346, 200)
        oy = (H - 720) // 2
        if L:
            self.again_btn = pygame.Rect(cx - 130, 470, 260, 64)
            self.win_menu_btn = pygame.Rect(cx - 130, 550, 260, 64)
        else:
            self.again_btn = pygame.Rect(cx - 180, 470 + oy, 360, 76)
            self.win_menu_btn = pygame.Rect(cx - 180, 570 + oy, 360, 76)
        self.win_oy = oy

        # main menu
        if L:
            bw, bh, y0, st = 320, 58, 340, 66
            self.logo_y = (100, 205, 292)
        else:
            bw, bh, y0, st = 440, 72, 560, 90
            self.logo_y = (250, 365, 465)
        keys = ["play", "online", "how", "share", "exit"]
        self.menu_btn = {k: pygame.Rect(cx - bw // 2, y0 + i * st, bw, bh)
                         for i, k in enumerate(keys)}

        # player count
        if L:
            self.count_rects = [pygame.Rect(195 + i * 230, 240, 200, 220) for i in range(4)]
            self.count_title_y, self.count_sub_y = 130, 500
            self.back_btn = pygame.Rect(cx - 130, 560, 260, 64)
        else:
            self.count_rects = [pygame.Rect(48 + (i % 2) * 324, 290 + (i // 2) * 250, 300, 220)
                                for i in range(4)]
            self.count_title_y, self.count_sub_y = 170, 800
            self.back_btn = pygame.Rect(cx - 150, 880, 300, 76)

        # player setup
        if L:
            self.setup_back = pygame.Rect(cx - 270, 620, 250, 64)
            self.setup_start = pygame.Rect(cx + 20, 620, 250, 64)
            self.setup_title_y, self.setup_hint_y = 60, 592
        else:
            self.setup_back = pygame.Rect(40, 880, 300, 76)
            self.setup_start = pygame.Rect(380, 880, 300, 76)
            self.setup_title_y, self.setup_hint_y = 70, 810
        self.sk = 1.0 if L else 1.25  # swatch scale

        # how to play
        self.how_back = pygame.Rect(cx - 130, 610, 260, 64) if L else pygame.Rect(cx - 150, 930, 300, 76)

        # online menu
        if L:
            self.on_name = pygame.Rect(cx - 220, 160, 440, 56)
            self.on_code = pygame.Rect(cx - 220, 280, 440, 56)
            self.on_create = pygame.Rect(cx - 220, 370, 440, 64)
            self.on_join = pygame.Rect(cx - 220, 450, 440, 64)
            self.on_back = pygame.Rect(cx - 130, 610, 260, 64)
            self.on_msg_y, self.on_title_y = 550, 70
        else:
            self.on_name = pygame.Rect(60, 300, 600, 64)
            self.on_code = pygame.Rect(60, 440, 600, 64)
            self.on_create = pygame.Rect(60, 550, 600, 76)
            self.on_join = pygame.Rect(60, 645, 600, 76)
            self.on_back = pygame.Rect(cx - 150, 900, 300, 76)
            self.on_msg_y, self.on_title_y = 770, 140

        # lobby
        if L:
            self.lb_copy = pygame.Rect(cx - 300, 525, 290, 60)
            self.lb_start = pygame.Rect(cx + 10, 525, 290, 60)
            self.lb_back = pygame.Rect(cx - 130, 622, 260, 64)
            self.lb_y = {"title": 50, "code": 125, "link": 190, "share": 212,
                         "rows": 235, "step": 66, "rowh": 58, "hint": 600}
        else:
            self.lb_copy = pygame.Rect(40, 720, 640, 72)
            self.lb_start = pygame.Rect(40, 810, 640, 76)
            self.lb_back = pygame.Rect(cx - 150, 960, 300, 76)
            self.lb_y = {"title": 110, "code": 210, "link": 290, "share": 316,
                         "rows": 370, "step": 76, "rowh": 64, "hint": 915}

        # sound button (top-right)
        self.sound_c = (W - 44, 44)
        self.sound_rect = pygame.Rect(self.sound_c[0] - 28, self.sound_c[1] - 28, 56, 56)

        # ambient particles
        self.particles = [[random.uniform(0, W), random.uniform(0, H),
                           random.uniform(8, 28), random.choice([1, 2, 2, 3]),
                           random.uniform(0, 6)] for _ in range(45)]

        self.fx.clear()
        self.resync_tokens()

    @staticmethod
    def make_panel(w, h):
        p = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(p, (18, 28, 60, 205), p.get_rect(), border_radius=20)
        pygame.draw.rect(p, (70, 92, 150, 255), p.get_rect(), 2, border_radius=20)
        return p

    def resync_tokens(self):
        if not self.players:
            return
        for p in self.players:
            c = self.board.get_cell(p.position)
            p.x, p.y = c.x, c.y
        if self.path:
            cp = self.cur()
            self.seg_from = (cp.x, cp.y)
            self.seg_t = 0.0

    def player_row(self, i):
        if self.landscape:
            return pygame.Rect(840, 148 + i * 56, 360, 48)
        return pygame.Rect(24, 826 + i * 50, 672, 44)

    # ---------- decorative ----------
    def make_spiral_deco(self):
        surf = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        cx, cy = self.W // 2, self.H // 2
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
                p[1] = self.H + 5
                p[0] = random.uniform(0, self.W)

    def draw_menu_bg(self):
        self.screen.blit(self.bg, (0, 0))
        self.screen.blit(self.spiral_deco, (0, 0))
        for p in self.particles:
            a = int(110 + 90 * math.sin(self.time * 2 + p[4]))
            pygame.draw.circle(self.screen, (a, a, min(255, a + 40)),
                               (int(p[0]), int(p[1])), p[3])

    def draw_title(self, text, y=70):
        t = self.title_font.render(text, True, S.GOLD)
        self.screen.blit(t, t.get_rect(center=(self.W // 2, y)))

    def draw_button(self, rect, text, enabled=True, color=S.GREEN):
        ui.draw_button(self.screen, rect, text, self.head_font, enabled, color)

    def draw_input(self, rect, text, placeholder, focused):
        pygame.draw.rect(self.screen, (10, 16, 40), rect, border_radius=12)
        border = S.GOLD if focused else (70, 92, 150)
        pygame.draw.rect(self.screen, border, rect, 2, border_radius=12)
        caret = "|" if (focused and int(self.time * 2) % 2 == 0) else ""
        if text:
            ts = self.text_font.render(text + caret, True, S.WHITE)
        else:
            ts = self.text_font.render(placeholder, True, (100, 115, 160))
        self.screen.blit(ts, ts.get_rect(midleft=(rect.x + 14, rect.centery)))
        if not text and caret:
            cs = self.text_font.render("|", True, S.WHITE)
            self.screen.blit(cs, cs.get_rect(midleft=(rect.x + 8, rect.centery)))

    def draw_sound_icon(self):
        cx, cy = self.sound_c
        hover = self.sound_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.circle(self.screen, (44, 62, 112) if hover else (26, 38, 78), (cx, cy), 24)
        pygame.draw.circle(self.screen, (70, 92, 150), (cx, cy), 24, 2)
        col = S.WHITE if not self.sfx.muted else (150, 160, 190)
        pygame.draw.polygon(self.screen, col, [(cx - 10, cy - 4), (cx - 4, cy - 4),
                                               (cx + 3, cy - 10), (cx + 3, cy + 10),
                                               (cx - 4, cy + 4), (cx - 10, cy + 4)])
        if self.sfx.muted:
            pygame.draw.line(self.screen, S.RED, (cx + 6, cy - 7), (cx + 15, cy + 7), 3)
            pygame.draw.line(self.screen, S.RED, (cx + 15, cy - 7), (cx + 6, cy + 7), 3)
        else:
            pygame.draw.arc(self.screen, col, pygame.Rect(cx - 2, cy - 8, 14, 16), -1.0, 1.0, 2)
            pygame.draw.arc(self.screen, col, pygame.Rect(cx - 4, cy - 13, 22, 26), -0.9, 0.9, 2)

    def draw_toast(self):
        text, t = self.toast
        if t <= 0 or not text:
            return
        ts = self.text_font.render(text, True, S.WHITE)
        r = ts.get_rect(center=(self.W // 2, self.H - 46)).inflate(40, 22)
        pygame.draw.rect(self.screen, (18, 28, 60), r, border_radius=18)
        pygame.draw.rect(self.screen, S.GOLD, r, 2, border_radius=18)
        self.screen.blit(ts, ts.get_rect(center=r.center))

    # ---------- share ----------
    def do_share(self, text):
        res = self.net.share(SITE, text)
        if res == "shared":
            return
        if res == "copied":
            self.toast = ("Link copied!", 2.0)
            self.copied_t = 2.0
        else:
            self.toast = ("Sharing works in the web version", 2.0)

    # ---------- game flow ----------
    def start_game(self):
        players = []
        for i, row in enumerate(self.setup):
            name = row["name"].strip()
            if not name:
                name = "Computer" if row["ai"] else f"Player {i + 1}"
            players.append(Player(name, PLAYER_COLORS[COLOR_NAMES[row["color"]]], row["ai"]))
        self.players = players
        self.online = False
        self.inbox = []
        self.reset_game()
        self.state = S.GAME

    def start_online_game(self, msg):
        self.players = [
            Player(p["name"], PLAYER_COLORS[COLOR_NAMES[int(p["color"]) % 4]], False)
            for p in msg["players"]
        ]
        self.online = True
        self.me = int(msg.get("you", 0))
        self.inbox = []
        self.reset_game(int(msg["seed"]))
        self.state = S.GAME

    def reset_game(self, seed=None):
        self.seed = seed if seed is not None else random.randrange(1 << 30)
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
        if self.phase != IDLE:
            return False
        if self.online:
            return self.current == self.me
        return not self.cur().is_ai

    def start_roll(self):
        if self.online:
            self.net.send({"t": "roll"})
            self.phase = WAIT_ROLL
            return
        self.begin_roll(random.randint(1, 6), self.current)

    def begin_roll(self, value, idx):
        self.current = idx
        self.phase = ROLLING
        self.timer = ROLL_TIME
        self.tick = 0.0
        self.final_roll = value
        self.roller = self.players[idx]
        self.sfx.play("dice")

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
            self.sfx.play("step")
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
            self.inbox = []
            if self.online and self.current == self.me:
                self.net.send({"t": "win"})
            self.sfx.play("win")
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
                self.sfx.play("boost")
                self.set_banner(f"BOOST! +{eff}", f"Move {eff} steps forward", S.GREEN, 1.4)
                self.fx.burst(p.x, p.y, S.GREEN, n=30, speed=190, gravity=-60)
                self.fx.ring(p.x, p.y, S.GREEN)
                self.do_flash((20, 120, 60))
            else:
                self.sfx.play("trap")
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

    # ---------- online helpers ----------
    def leave_online(self):
        self.net.close()
        self.online = False
        self.inbox = []

    def do_create(self):
        if self.net.connecting:
            return
        name = self.net_name.strip() or "Player"
        self.net_msg = ""
        self.net.connect({"t": "create", "name": name})

    def do_join(self):
        if self.net.connecting:
            return
        code = self.net_code.strip().upper()
        if len(code) != 4:
            self.net_msg = "Enter the 4-letter room code first."
            return
        name = self.net_name.strip() or "Player"
        self.net_msg = ""
        self.net.connect({"t": "join", "code": code, "name": name})

    def invite_link(self):
        return f"{SITE}?room={self.lobby.get('code', '')}"

    def handle_net(self, m):
        t = m.get("t")
        if t == "lobby":
            self.lobby = m
            self.me = int(m.get("you", 0))
            if self.state == ONLINE_MENU:
                self.state = ONLINE_LOBBY
                self.net_msg = ""
        elif t == "error":
            self.net_msg = str(m.get("msg", "Error"))
        elif t == "start":
            self.start_online_game(m)
        elif t in ("roll", "turn"):
            self.inbox.append(m)
        elif t == "abort":
            self.inbox = []
            self.online = False
            self.net_msg = f"{m.get('name', 'A player')} left. Game stopped."
            if self.state == S.GAME:
                self.state = ONLINE_LOBBY
        elif t == "closed":
            if self.state in (S.GAME, ONLINE_LOBBY):
                self.net_msg = "Disconnected from server."
                self.state = ONLINE_MENU
            self.online = False
            self.inbox = []

    def process_inbox(self):
        if not self.inbox:
            return
        m = self.inbox[0]
        if m["t"] == "roll" and self.phase in (IDLE, WAIT_ROLL):
            self.inbox.pop(0)
            self.begin_roll(int(m["v"]), int(m["i"]) % len(self.players))
        elif m["t"] == "turn" and self.phase == WAIT_TURN:
            self.inbox.pop(0)
            self.current = int(m["i"]) % len(self.players)
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
        if self.landscape:
            return pygame.Rect(240, 110 + i * 104, 800, 92)
        return pygame.Rect(24, 130 + i * 164, 672, 150)

    def name_rect(self, i):
        r = self.row_rect(i)
        if self.landscape:
            return pygame.Rect(r.x + 250, r.y + 22, 270, 48)
        return pygame.Rect(r.x + 24, r.y + 76, 300, 56)

    def swatch_center(self, i, k):
        r = self.row_rect(i)
        if self.landscape:
            return (r.x + 580 + k * 58, r.centery)
        return (r.x + 384 + k * 74, r.y + 104)

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

    @staticmethod
    def ask_text(title, current):
        """Phones have no keyboard for the canvas, so use a popup box."""
        try:
            res = platform.window.prompt(title, current)
        except Exception:
            res = None
        return None if res is None else str(res).strip()

    def ask_name(self, i):
        row = self.setup[i]
        res = self.ask_text("Enter name (max 12 letters):", row["name"])
        if res is not None:
            row["name"] = res[:MAX_NAME]

    # ---------- lobby layout ----------
    def lobby_row(self, i):
        y = self.lb_y
        return pygame.Rect(self.W // 2 - 300, y["rows"] + i * y["step"], 600, y["rowh"])

    def lobby_swatch(self, i, k):
        r = self.lobby_row(i)
        return (r.right - 190 + k * 46, r.centery)

    # ---------- input ----------
    def clicked(self, event, rect):
        hit = (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
               and rect.collidepoint(event.pos))
        if hit:
            self.sfx.play("click")
        return hit

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue
            if event.type == pygame.KEYDOWN and event.key == pygame.K_m and not (
                    self.state in (S.PLAYER_SETUP, ONLINE_MENU)):
                self.sfx.toggle()
                continue
            if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and self.sound_rect.collidepoint(event.pos)):
                self.sfx.toggle()
                self.sfx.play("click")
                continue
            if self.state == S.MAIN_MENU:
                self.ev_menu(event)
            elif self.state == S.PLAYER_COUNT:
                self.ev_count(event)
            elif self.state == S.PLAYER_SETUP:
                self.ev_setup(event)
            elif self.state == S.HOW_TO_PLAY:
                self.ev_how(event)
            elif self.state == ONLINE_MENU:
                self.ev_online_menu(event)
            elif self.state == ONLINE_LOBBY:
                self.ev_lobby(event)
            elif self.state == S.GAME:
                self.ev_game(event)

    def ev_menu(self, event):
        b = self.menu_btn
        if self.clicked(event, b["play"]):
            self.state = S.PLAYER_COUNT
        elif self.clicked(event, b["online"]):
            self.net_msg = ""
            self.state = ONLINE_MENU
        elif self.clicked(event, b["how"]):
            self.state = S.HOW_TO_PLAY
        elif self.clicked(event, b["share"]):
            self.do_share("Play Spiral Race with me! A fast spiral board game, free in your browser.")
        elif self.clicked(event, b["exit"]):
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
            hit_r = 22 * self.sk
            for i in range(len(self.setup)):
                if self.name_rect(i).collidepoint(event.pos):
                    self.focus = i
                    if self.is_touch():
                        self.ask_name(i)
                        return
                for k in range(4):
                    cx, cy = self.swatch_center(i, k)
                    if math.hypot(event.pos[0] - cx, event.pos[1] - cy) <= hit_r:
                        self.sfx.play("click")
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

    def ev_online_menu(self, event):
        if self.clicked(event, self.on_back) or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            self.leave_online()
            self.net_msg = ""
            self.state = S.MAIN_MENU
            return
        if self.clicked(event, self.on_create):
            self.do_create()
        elif self.clicked(event, self.on_join):
            self.do_join()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.on_name.collidepoint(event.pos):
                self.net_focus = 0
                if self.is_touch():
                    res = self.ask_text("Enter your name (max 12 letters):", self.net_name)
                    if res is not None:
                        self.net_name = res[:MAX_NAME]
            elif self.on_code.collidepoint(event.pos):
                self.net_focus = 1
                if self.is_touch():
                    res = self.ask_text("Enter 4-letter room code:", self.net_code)
                    if res is not None:
                        self.net_code = "".join(c for c in res.upper() if c.isalpha())[:4]
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                self.net_focus = 1 - self.net_focus
            elif event.key == pygame.K_RETURN:
                if len(self.net_code) == 4:
                    self.do_join()
                else:
                    self.do_create()
            elif event.key == pygame.K_BACKSPACE:
                if self.net_focus == 0:
                    self.net_name = self.net_name[:-1]
                else:
                    self.net_code = self.net_code[:-1]
            elif event.unicode and event.unicode.isprintable():
                if self.net_focus == 0:
                    if len(self.net_name) < MAX_NAME:
                        self.net_name += event.unicode
                elif event.unicode.isalpha() and len(self.net_code) < 4:
                    self.net_code += event.unicode.upper()

    def ev_lobby(self, event):
        if self.clicked(event, self.lb_back) or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            self.leave_online()
            self.net_msg = ""
            self.state = S.MAIN_MENU
            return
        if self.clicked(event, self.lb_copy):
            code = self.lobby.get("code", "")
            link = self.invite_link()
            res = self.net.share(link, f"Join my Spiral Race room {code}!")
            if res != "shared":
                self.copied_t = 2.0
                self.toast = (("Invite link copied!" if res == "copied"
                               else "Sharing works in the web version"), 2.0)
        elif self.clicked(event, self.lb_start):
            if self.me == 0 and len(self.lobby.get("players", [])) >= 2:
                self.net.send({"t": "start"})
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            hit_r = 20 if self.landscape else 24
            for k in range(4):
                cx, cy = self.lobby_swatch(self.me, k)
                if math.hypot(event.pos[0] - cx, event.pos[1] - cy) <= hit_r:
                    self.sfx.play("click")
                    self.net.send({"t": "color", "color": k})

    def ev_game(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if not self.online:
                    self.state = S.MAIN_MENU
            elif event.key == pygame.K_SPACE:
                if self.can_roll():
                    self.start_roll()
                elif self.phase == WON and not self.online:
                    self.reset_game()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.can_roll() and self.roll_btn.collidepoint(event.pos):
                self.sfx.play("click")
                self.start_roll()
            elif self.phase == WON:
                if self.again_btn.collidepoint(event.pos):
                    self.sfx.play("click")
                    if self.online:
                        self.state = ONLINE_LOBBY
                    else:
                        self.reset_game()
                elif self.win_menu_btn.collidepoint(event.pos):
                    self.sfx.play("click")
                    if self.online:
                        self.leave_online()
                    self.state = S.MAIN_MENU

    # ---------- update ----------
    def check_orientation(self, dt):
        self.size_t -= dt
        if self.size_t > 0:
            return
        self.size_t = 0.3
        sz = self.net.window_size()
        if sz and sz[0] > 0 and sz[1] > 0:
            want_landscape = sz[0] > sz[1]
            if want_landscape != self.landscape:
                self.build_layout(want_landscape)

    def update(self, dt):
        self.time += dt
        self.check_orientation(dt)
        self.update_particles(dt)
        if self.copied_t > 0:
            self.copied_t -= dt
        if self.toast[1] > 0:
            self.toast = (self.toast[0], self.toast[1] - dt)
        for m in self.net.update(dt):
            self.handle_net(m)
        if self.state != S.GAME:
            return
        self.fx.update(dt, self.H)
        if self.banner_t > 0:
            self.banner_t -= dt
        if self.flash_t > 0:
            self.flash_t -= dt

        if self.phase == WON:
            self.win_t += dt
            if self.win_t < CONFETTI_TIME:
                self.fx.confetti(self.W, 3)
            return

        if self.online:
            self.process_inbox()

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
                if self.online:
                    if self.current == self.me:
                        self.net.send({"t": "done"})
                    self.phase = WAIT_TURN
                else:
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
        self.screen.blit(a, self.title_pos)
        self.screen.blit(b, (self.title_pos[0] + a.get_width(), self.title_pos[1]))

        p = self.cur()
        txt = f"{self.winner.name} wins!" if self.phase == WON else f"{p.name}'s Turn"
        t = self.head_font.render(txt, True, S.WHITE)
        draw_token(self.screen, self.turn_tok[0], self.turn_tok[1], p.color, p.initial,
                   self.token_font, 14)
        self.screen.blit(t, self.turn_txt)

        self.screen.blit(self.panel, self.panel_pos)
        if self.landscape:
            h = self.head_font.render("PLAYERS", True, S.GOLD)
            self.screen.blit(h, (845, 98))

        for i, pl in enumerate(self.players):
            r = self.player_row(i)
            active = pl is p and self.phase != WON
            fill = (44, 62, 112) if active else (26, 38, 78)
            pygame.draw.rect(self.screen, fill, r, border_radius=14)
            if active:
                glow = 0.5 + 0.5 * math.sin(self.time * 4)
                col = theme.lighten(pl.color, 0.2 * glow)
                pygame.draw.rect(self.screen, col, r, 3, border_radius=14)
            draw_token(self.screen, r.x + 28, r.centery - 2, pl.color, pl.initial, self.token_font, 13)
            suffix = "  (AI)" if pl.is_ai else ""
            if self.online and i == self.me:
                suffix = "  (YOU)"
            nm = self.text_font.render(pl.name + suffix, True, S.WHITE)
            self.screen.blit(nm, nm.get_rect(midleft=(r.x + 56, r.centery)))
            ps = self.text_font.render(f"Pos {pl.position}", True, theme.lighten(pl.color, 0.3))
            self.screen.blit(ps, ps.get_rect(midright=(r.right - 16, r.centery)))

        box = self.dice_box
        pygame.draw.rect(self.screen, (10, 16, 40), box, border_radius=18)
        pygame.draw.rect(self.screen, (70, 92, 150), box, 2, border_radius=18)
        if self.phase in (ROLLING, WAIT_ROLL):
            label = "ROLLING..."
        elif self.phase == IDLE and p.is_ai:
            label = f"{p.name.upper()} IS THINKING..."
        elif self.phase == IDLE and self.online and self.current != self.me:
            label = f"WAITING FOR {p.name.upper()}..."
        elif self.phase == IDLE and self.online:
            label = "YOUR TURN - ROLL!"
        elif self.phase == IDLE and self.dice_shown is None:
            label = "ROLL THE DICE"
        elif self.roller is not None:
            label = f"{self.roller.name.upper()} ROLLED"
        else:
            label = ""
        lf = self.text_font if self.landscape else self.font
        lt = lf.render(label, True, S.WHITE)
        self.screen.blit(lt, lt.get_rect(center=(box.centerx, box.y + (26 if self.landscape else 34))))
        val = str(self.dice_shown) if self.dice_shown else "-"
        col = S.GOLD if self.phase not in (ROLLING, WAIT_ROLL) else S.WHITE
        n = self.big_font.render(val, True, col)
        self.screen.blit(n, n.get_rect(center=(box.centerx, box.y + (92 if self.landscape else 118))))

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
        self.screen.blit(t, t.get_rect(center=self.banner_pos[0]))
        self.screen.blit(s, s.get_rect(center=self.banner_pos[1]))

    def draw_flash(self):
        if self.flash_t <= 0:
            return
        self.flash_surf.fill(self.flash_col)
        self.flash_surf.set_alpha(int(80 * self.flash_t / FLASH_TIME))
        self.screen.blit(self.flash_surf, (0, 0))

    def draw_win(self):
        cx, oy = self.W // 2, self.win_oy
        dim = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        dim.fill((4, 8, 22, 190))
        self.screen.blit(dim, (0, 0))
        w = self.winner
        bob = math.sin(self.time * 3) * 5
        draw_token(self.screen, cx, 200 + oy + bob, w.color, w.initial, self.head_font, 44)
        t = self.banner_font.render("WINNER!", True, S.GOLD)
        self.screen.blit(t, t.get_rect(center=(cx, 300 + oy)))
        n = self.big_font.render(w.name.upper(), True, S.WHITE)
        n = pygame.transform.smoothscale(n, (n.get_width() * 55 // 100, n.get_height() * 55 // 100))
        self.screen.blit(n, n.get_rect(center=(cx, 380 + oy)))
        r = self.text_font.render("Reached the Core!", True, S.WHITE)
        self.screen.blit(r, r.get_rect(center=(cx, 430 + oy)))
        self.draw_button(self.again_btn, "BACK TO LOBBY" if self.online else "PLAY AGAIN",
                         True, S.GOLD)
        self.draw_button(self.win_menu_btn, "MAIN MENU", True, (70, 110, 200))

    # ---------- drawing: menus ----------
    def draw_main_menu(self):
        self.draw_menu_bg()
        cx = self.W // 2
        ly = self.logo_y
        a = self.logo_font.render("SPIRAL", True, S.WHITE)
        b = self.logo_font.render("RACE", True, S.GOLD)
        bob = math.sin(self.time * 2) * 4
        self.screen.blit(a, a.get_rect(center=(cx, ly[0] + bob)))
        self.screen.blit(b, b.get_rect(center=(cx, ly[1] + bob)))
        s = self.head_font.render("Race to the Core", True, (170, 190, 235))
        self.screen.blit(s, s.get_rect(center=(cx, ly[2])))
        m = self.menu_btn
        self.draw_button(m["play"], "PLAY")
        self.draw_button(m["online"], "ONLINE", True, S.GOLD)
        self.draw_button(m["how"], "HOW TO PLAY", True, (70, 110, 200))
        self.draw_button(m["share"], "SHARE", True, (140, 90, 220))
        self.draw_button(m["exit"], "EXIT", True, S.RED)

    def draw_player_count(self):
        self.draw_menu_bg()
        self.draw_title("SELECT NUMBER OF PLAYERS", self.count_title_y)
        for i, r in enumerate(self.count_rects):
            color = PLAYER_COLORS[COLOR_NAMES[i]]
            ui.draw_card(self.screen, r, color, i + 1,
                         "PLAYER" if i == 0 else "PLAYERS",
                         self.big_font, self.text_font)
        sub = self.text_font.render("1 Player = you vs. the computer", True, (170, 190, 235))
        self.screen.blit(sub, sub.get_rect(center=(self.W // 2, self.count_sub_y)))
        self.draw_button(self.back_btn, "BACK", True, (70, 110, 200))

    def draw_setup(self):
        self.draw_menu_bg()
        self.draw_title("PLAYER SETUP", self.setup_title_y)
        k_ = self.sk
        for i, row in enumerate(self.setup):
            r = self.row_rect(i)
            ui.draw_panel(self.screen, r)
            color = PLAYER_COLORS[COLOR_NAMES[row["color"]]]
            shown = row["name"].strip() or ("Computer" if row["ai"] else f"Player {i + 1}")
            if self.n_humans == 1:
                label = "AI OPPONENT" if row["ai"] else "YOUR PLAYER"
            else:
                label = f"PLAYER {i + 1}"
            if self.landscape:
                tok = (r.x + 44, r.centery - 2)
                lab = (r.x + 80, r.centery)
            else:
                tok = (r.x + 44, r.y + 38)
                lab = (r.x + 84, r.y + 38)
            draw_token(self.screen, tok[0], tok[1], color, shown[0].upper(), self.token_font, 18)
            lt = self.text_font.render(label, True, S.WHITE)
            self.screen.blit(lt, lt.get_rect(midleft=lab))

            nr = self.name_rect(i)
            ph = "Computer" if row["ai"] else f"Player {i + 1}"
            self.draw_input(nr, row["name"], ph, self.focus == i)

            for k in range(4):
                c = PLAYER_COLORS[COLOR_NAMES[k]]
                sx, sy = self.swatch_center(i, k)
                if row["color"] == k:
                    pygame.draw.circle(self.screen, S.WHITE, (sx, sy), int(23 * k_))
                pygame.draw.circle(self.screen, theme.darken(c, 0.3), (sx, sy), int(19 * k_))
                pygame.draw.circle(self.screen, c, (sx, sy), int(16 * k_))
                pygame.draw.circle(self.screen, theme.lighten(c, 0.5),
                                   (sx - int(5 * k_), sy - int(5 * k_)), int(4 * k_))
        msg = ("Tap a name box to type your name. Colors can't repeat."
               if self.is_touch() else
               "Click a name box and type. Colors can't repeat. Empty name = default.")
        hint = self.small_font.render(msg, True, (150, 170, 215))
        self.screen.blit(hint, hint.get_rect(center=(self.W // 2, self.setup_hint_y)))
        self.draw_button(self.setup_back, "BACK", True, (70, 110, 200))
        self.draw_button(self.setup_start, "START GAME", True, S.GREEN)

    def draw_online_menu(self):
        self.draw_menu_bg()
        cx = self.W // 2
        self.draw_title("PLAY ONLINE", self.on_title_y)
        lb = self.text_font.render("YOUR NAME", True, (170, 190, 235))
        self.screen.blit(lb, (self.on_name.x, self.on_name.y - 28))
        self.draw_input(self.on_name, self.net_name, "Player", self.net_focus == 0)
        lb2 = self.text_font.render("ROOM CODE (only to join)", True, (170, 190, 235))
        self.screen.blit(lb2, (self.on_code.x, self.on_code.y - 28))
        self.draw_input(self.on_code, self.net_code, "ABCD", self.net_focus == 1)

        busy = self.net.connecting
        self.draw_button(self.on_create, "CREATE ROOM", not busy, S.GREEN)
        self.draw_button(self.on_join, "JOIN ROOM", not busy, (70, 110, 200))

        if busy:
            dots = "." * (int(self.time * 3) % 4)
            msg = f"Connecting{dots} {int(self.net.t)}s"
            sub = "The free server may need up to a minute to wake up."
            c1 = S.GOLD
        else:
            msg = self.net.error or self.net_msg
            sub = ""
            c1 = S.RED if (self.net.error or "left" in msg or "not" in msg
                           or "full" in msg or "Disconnected" in msg) else S.WHITE
        my = self.on_msg_y
        if msg:
            t = self.text_font.render(msg, True, c1)
            if t.get_width() > self.W - 40:
                t = self.font.render(msg, True, c1)
            self.screen.blit(t, t.get_rect(center=(cx, my)))
        if sub:
            t = self.small_font.render(sub, True, (150, 170, 215))
            self.screen.blit(t, t.get_rect(center=(cx, my + 28)))
        self.draw_button(self.on_back, "BACK", True, (70, 110, 200))

    def draw_lobby(self):
        self.draw_menu_bg()
        cx = self.W // 2
        y = self.lb_y
        self.draw_title("ROOM", y["title"])
        code = self.lobby.get("code", "")
        t = self.big_font.render(code, True, S.GOLD)
        t = pygame.transform.smoothscale(t, (t.get_width() * 70 // 100, t.get_height() * 70 // 100))
        self.screen.blit(t, t.get_rect(center=(cx, y["code"])))
        link = self.invite_link().replace("https://", "")
        lt = self.small_font.render("Invite link: " + link, True, (170, 190, 235))
        self.screen.blit(lt, lt.get_rect(center=(cx, y["link"])))
        sh = self.small_font.render("Share the code or the link with your friends (max 4 players)",
                                    True, (150, 170, 215))
        self.screen.blit(sh, sh.get_rect(center=(cx, y["share"])))

        players = self.lobby.get("players", [])
        taken = {int(p["color"]) for p in players}
        for i, pl in enumerate(players):
            r = self.lobby_row(i)
            ui.draw_panel(self.screen, r)
            ci = int(pl["color"]) % 4
            color = PLAYER_COLORS[COLOR_NAMES[ci]]
            nm = pl["name"] or "Player"
            draw_token(self.screen, r.x + 36, r.centery - 2, color, nm[0].upper(),
                       self.token_font, 17)
            tag = ""
            if i == 0:
                tag += "  (HOST)"
            if i == self.me:
                tag += "  (YOU)"
            ns = self.text_font.render(nm + tag, True, S.WHITE)
            self.screen.blit(ns, ns.get_rect(midleft=(r.x + 68, r.centery)))
            if i == self.me:
                for k in range(4):
                    c = PLAYER_COLORS[COLOR_NAMES[k]]
                    sx, sy = self.lobby_swatch(i, k)
                    used_by_other = k in taken and k != ci
                    cc = theme.darken(c, 0.6) if used_by_other else c
                    if k == ci:
                        pygame.draw.circle(self.screen, S.WHITE, (sx, sy), 20)
                    pygame.draw.circle(self.screen, theme.darken(cc, 0.3), (sx, sy), 16)
                    pygame.draw.circle(self.screen, cc, (sx, sy), 13)

        host = self.me == 0
        can_start = host and len(players) >= 2
        self.draw_button(self.lb_copy, "LINK COPIED!" if self.copied_t > 0 else "SHARE INVITE LINK",
                         True, (70, 110, 200))
        self.draw_button(self.lb_start, "START GAME", can_start, S.GREEN)
        if host:
            hint = "Waiting for friends to join..." if len(players) < 2 else "Everyone ready? Press START GAME."
        else:
            hint = "Waiting for the host to start the game..."
        if self.net_msg:
            hint = self.net_msg
        h = self.small_font.render(hint, True, S.GOLD)
        self.screen.blit(h, h.get_rect(center=(cx, y["hint"])))
        self.draw_button(self.lb_back, "LEAVE", True, S.RED)

    def draw_how(self):
        self.draw_menu_bg()
        L = self.landscape
        self.draw_title("HOW TO PLAY", 70 if L else 120)
        items = [
            ("dice", "Roll the dice: 1 to 6"),
            ("path", "Move along the spiral path"),
            ("green", "Green BOOST cells push you forward"),
            ("red", "Red TRAP cells push you backward"),
            ("core", f"Reach the Core ({TOTAL_CELLS}) exactly to win"),
        ]
        navy = (52, 68, 112)
        tx_c, tx_text = (400, 490) if L else (110, 190)
        y0, step = (170, 82) if L else (260, 125)
        for i, (kind, text) in enumerate(items):
            y = y0 + i * step
            cx = tx_c
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
            self.screen.blit(t, t.get_rect(midleft=(tx_text, y)))
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
        elif self.state == ONLINE_MENU:
            self.draw_online_menu()
        elif self.state == ONLINE_LOBBY:
            self.draw_lobby()
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
        self.draw_sound_icon()
        self.draw_toast()
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


if __name__ == "__main__":
    asyncio.run(main())

# particles.py
# Lightweight procedural particles: sparks, rings, confetti
import math
import random
import pygame

CONFETTI_COLORS = [
    (255, 200, 60), (235, 70, 80), (70, 140, 245),
    (70, 205, 120), (250, 205, 60), (255, 255, 255),
]
MAX_ITEMS = 700


class Particles:
    def __init__(self):
        self.items = []

    def clear(self):
        self.items.clear()

    def burst(self, x, y, color, n=26, speed=170, gravity=260,
              size=(2.0, 5.0), life=(0.45, 0.9)):
        for _ in range(n):
            if len(self.items) >= MAX_ITEMS:
                return
            a = random.uniform(0, math.tau)
            s = random.uniform(speed * 0.3, speed)
            lf = random.uniform(*life)
            self.items.append({
                "k": "dot", "x": x, "y": y,
                "vx": math.cos(a) * s, "vy": math.sin(a) * s,
                "g": gravity, "life": lf, "max": lf,
                "c": color, "s": random.uniform(*size),
            })

    def ring(self, x, y, color, max_r=46, life=0.5):
        self.items.append({"k": "ring", "x": x, "y": y, "life": life,
                           "max": life, "c": color, "r": max_r})

    def confetti(self, width, n=4):
        for _ in range(n):
            if len(self.items) >= MAX_ITEMS:
                return
            self.items.append({
                "k": "conf", "x": random.uniform(0, width), "y": -12.0,
                "vx": random.uniform(-40, 40), "vy": random.uniform(110, 240),
                "t": random.uniform(0, 6), "c": random.choice(CONFETTI_COLORS),
                "w": random.randint(6, 11), "h": random.randint(4, 7),
                "life": 99.0, "max": 99.0,
            })

    def update(self, dt, height):
        alive = []
        for p in self.items:
            p["life"] -= dt
            if p["life"] <= 0:
                continue
            if p["k"] == "dot":
                p["vy"] += p["g"] * dt
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
            elif p["k"] == "conf":
                p["t"] += dt * 7
                p["x"] += (p["vx"] + math.sin(p["t"]) * 50) * dt
                p["y"] += p["vy"] * dt
                if p["y"] > height + 20:
                    continue
            alive.append(p)
        self.items = alive

    def draw(self, screen):
        for p in self.items:
            k = p["k"]
            if k == "dot":
                f = p["life"] / p["max"]
                r = max(1, int(p["s"] * (0.4 + 0.6 * f)))
                pygame.draw.circle(screen, p["c"], (int(p["x"]), int(p["y"])), r)
            elif k == "ring":
                f = 1 - p["life"] / p["max"]
                r = max(2, int(p["r"] * f))
                w = max(1, int(4 * (1 - f)))
                pygame.draw.circle(screen, p["c"], (int(p["x"]), int(p["y"])), r, w)
            else:
                w = max(2, int(abs(math.cos(p["t"])) * p["w"]))
                rect = pygame.Rect(int(p["x"]), int(p["y"]), w, p["h"])
                pygame.draw.rect(screen, p["c"], rect)
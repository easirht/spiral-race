# board.py
import math
import random

TOTAL_CELLS = 75
N_BOOST = 8
N_TRAP = 8


class Cell:
    def __init__(self, position, effect, x, y):
        self.position = position
        self.effect = effect
        self.x = x
        self.y = y


class Board:
    def __init__(self, center_x, center_y, r_start=310, r_end=55, turns=3.5):
        self.cx = center_x
        self.cy = center_y
        self.cells = []

        # Spiral from the outside (theta_max) to the inner ring (theta = 0).
        # Cells 1..74 sit on the spiral at equal distances, cell 75 is the core.
        theta_max = turns * 2 * math.pi
        b = (r_start - r_end) / theta_max

        def point(theta):
            r = r_end + b * theta
            angle = -math.pi / 2 - theta
            return (center_x + r * math.cos(angle),
                    center_y + r * math.sin(angle))

        steps = 6000
        samples = []
        cumulative = [0.0]
        for k in range(steps + 1):
            theta = theta_max * (1 - k / steps)
            p = point(theta)
            if samples:
                prev = samples[-1]
                cumulative.append(cumulative[-1] + math.hypot(p[0] - prev[0], p[1] - prev[1]))
            samples.append(p)
        total = cumulative[-1]

        n_path = TOTAL_CELLS - 1  # 74 cells on the spiral
        gap = total / (n_path - 1)
        idx = 0
        for i in range(n_path):
            target = i * gap
            while idx < len(cumulative) - 1 and cumulative[idx] < target:
                idx += 1
            x, y = samples[idx]
            self.cells.append(Cell(i + 1, 0, x, y))

        # Cell 75 = core, exactly at the centre
        self.cells.append(Cell(TOTAL_CELLS, 0, center_x, center_y))

    def randomize(self, seed=None):
        """Place BOOST and TRAP cells randomly. Same seed = same layout."""
        rng = random.Random(seed)
        for c in self.cells:
            c.effect = 0
        n = N_BOOST + N_TRAP
        candidates = list(range(3, TOTAL_CELLS - 1))  # cells 3..74
        rng.shuffle(candidates)
        chosen = []
        for pos in candidates:
            if all(abs(pos - q) >= 2 for q in chosen):  # never side by side
                chosen.append(pos)
            if len(chosen) == n:
                break
        chosen.sort()
        values = [rng.choice([2, 3, 4]) for _ in range(N_BOOST)]
        values += [-rng.choice([2, 3, 4]) for _ in range(N_TRAP)]
        rng.shuffle(values)
        for pos, val in zip(chosen, values):
            self.cells[pos - 1].effect = val

    def get_cell(self, position):
        if position <= 0:
            c = self.cells[0]
            return Cell(0, 0, c.x + 56, c.y)
        return self.cells[position - 1]
# board.py
import math

TOTAL_CELLS = 36

# Special cells: position -> effect
SPECIAL_CELLS = {
    5: 3,
    9: -2,
    13: 4,
    17: -3,
    21: 2,
    25: -4,
    29: 3,
    32: -2,
}


class Cell:
    def __init__(self, position, effect, x, y):
        self.position = position
        self.effect = effect
        self.x = x
        self.y = y


class Board:
    def __init__(self, center_x, center_y, r_start=285, turns=2.5):
        self.cx = center_x
        self.cy = center_y
        self.cells = []

        # Archimedean spiral: radius shrinks to 0 at the core.
        theta_max = turns * 2 * math.pi
        b = r_start / theta_max

        def point(theta):
            r = b * theta
            angle = -math.pi / 2 - theta
            return (center_x + r * math.cos(angle),
                    center_y + r * math.sin(angle))

        # Sample the whole path (outside -> centre) and measure its length.
        steps = 4000
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

        # Place the 36 cells at equal distances along the path.
        gap = total / (TOTAL_CELLS - 1)
        idx = 0
        for i in range(TOTAL_CELLS):
            target = i * gap
            while idx < len(cumulative) - 1 and cumulative[idx] < target:
                idx += 1
            x, y = samples[idx]
            position = i + 1
            effect = SPECIAL_CELLS.get(position, 0)
            self.cells.append(Cell(position, effect, x, y))

        # Cell 36 is exactly at the core
        self.cells[-1].x = center_x
        self.cells[-1].y = center_y

    def get_cell(self, position):
        # position 0 = start (before cell 1), placed to the right of cell 1
        if position <= 0:
            c = self.cells[0]
            return Cell(0, 0, c.x + 50, c.y)
        return self.cells[position - 1]
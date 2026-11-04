# ============================================================
# neighbors.py - Neighbor-finding and event detection layer
#
# Two jobs, both using a spatial grid:
#   find()          - which human each zombie should chase
#   find_contacts() - which humans each zombie is touching (fight events)
#
# Two versions follow the same rules, so the simulation can use either:
#   SerialFinder   - one CPU core does all the work
#   ParallelFinder - the zombies are split across several CPU cores
# ============================================================

import math
import multiprocessing
from simulation import CELL_SIZE, VISION_RADIUS, TOUCH_DISTANCE


# ---------- SPATIAL GRID HELPERS ----------
def build_grid(positions):
    """(column, row) -> list of indexes of the agents in that square."""
    grid = {}
    for i, (x, y) in enumerate(positions):
        key = (int(x // CELL_SIZE), int(y // CELL_SIZE))
        grid.setdefault(key, []).append(i)
    return grid


def nearby(grid, x, y, radius):
    """Every index in the squares within `radius` pixels of (x, y)."""
    r = math.ceil(radius / CELL_SIZE)
    cx, cy = int(x // CELL_SIZE), int(y // CELL_SIZE)
    for gx in range(cx - r, cx + r + 1):
        for gy in range(cy - r, cy + r + 1):
            yield from grid.get((gx, gy), ())


# ---------- THE WORK (runs on one core, or on each worker) ----------
def find_nearest(zombie_positions, human_positions):
    """For each zombie: the index of the nearest human in vision range, or -1."""
    grid = build_grid(human_positions)
    results = []
    for (zx, zy) in zombie_positions:
        best = -1
        best_dist = VISION_RADIUS
        for i in nearby(grid, zx, zy, VISION_RADIUS):
            hx, hy = human_positions[i]
            d = math.hypot(hx - zx, hy - zy)
            if d < best_dist:
                best = i
                best_dist = d
        results.append(best)
    return results


def detect_contacts(zombie_positions, human_positions):
    """For each zombie: a list of the indexes of every human it is touching."""
    grid = build_grid(human_positions)
    results = []
    for (zx, zy) in zombie_positions:
        touching = []
        for i in nearby(grid, zx, zy, TOUCH_DISTANCE):
            hx, hy = human_positions[i]
            if math.hypot(hx - zx, hy - zy) < TOUCH_DISTANCE:
                touching.append(i)
        results.append(touching)
    return results


# ---------- SERIAL VERSION ----------
class SerialFinder:
    """One CPU core handles every zombie."""

    def find(self, zombie_positions, human_positions):
        return find_nearest(zombie_positions, human_positions)

    def find_contacts(self, zombie_positions, human_positions):
        return detect_contacts(zombie_positions, human_positions)

    def close(self):
        pass


# ---------- PARALLEL VERSION ----------
class ParallelFinder:
    """Splits the zombies into chunks, one chunk per CPU core."""

    def __init__(self, workers=4):
        self.workers = workers
        self.pool = multiprocessing.Pool(workers)  # created once, reused every frame

    def _run(self, work, zombie_positions, human_positions):
        # Split the zombies into chunks, run `work` on every chunk at the
        # same time, then put the results back together in the original order
        if not zombie_positions:
            return []
        size = math.ceil(len(zombie_positions) / self.workers)
        chunks = [zombie_positions[i:i + size]
                  for i in range(0, len(zombie_positions), size)]
        parts = self.pool.starmap(work, [(chunk, human_positions) for chunk in chunks])
        return [r for part in parts for r in part]

    def find(self, zombie_positions, human_positions):
        return self._run(find_nearest, zombie_positions, human_positions)

    def find_contacts(self, zombie_positions, human_positions):
        return self._run(detect_contacts, zombie_positions, human_positions)

    def close(self):
        self.pool.close()
        self.pool.join()
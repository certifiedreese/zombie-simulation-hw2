# ============================================================
# neighbors.py - Neighbor-finding layer
#
# Finds which human each zombie should chase. Two versions follow
# the same rules (a find() method), so the simulation can use either:
#   SerialFinder   - one CPU core does all the work
#   ParallelFinder - the zombies are split across several CPU cores
# ============================================================

import math
import multiprocessing
from simulation import CELL_SIZE, VISION_RADIUS


def find_nearest(zombie_positions, human_positions):
    """For each zombie, return the index of the nearest human in
    vision range, or -1 if nobody is in sight. Uses a spatial grid."""
    # Build a grid: (column, row) -> list of human indexes in that square
    grid = {}
    for i, (hx, hy) in enumerate(human_positions):
        key = (int(hx // CELL_SIZE), int(hy // CELL_SIZE))
        grid.setdefault(key, []).append(i)

    r = math.ceil(VISION_RADIUS / CELL_SIZE)  # squares to look out in each direction
    results = []
    for (zx, zy) in zombie_positions:
        cx, cy = int(zx // CELL_SIZE), int(zy // CELL_SIZE)
        best = -1
        best_dist = VISION_RADIUS
        for gx in range(cx - r, cx + r + 1):
            for gy in range(cy - r, cy + r + 1):
                for i in grid.get((gx, gy), ()):
                    hx, hy = human_positions[i]
                    d = math.hypot(hx - zx, hy - zy)
                    if d < best_dist:
                        best = i
                        best_dist = d
        results.append(best)
    return results


class SerialFinder:
    """One CPU core handles every zombie."""

    def find(self, zombie_positions, human_positions):
        return find_nearest(zombie_positions, human_positions)

    def close(self):
        pass  # nothing to shut down


class ParallelFinder:
    """Splits the zombies into chunks, one chunk per CPU core."""

    def __init__(self, workers=4):
        self.workers = workers
        # A pool of worker processes, created once and reused every frame
        self.pool = multiprocessing.Pool(workers)

    def find(self, zombie_positions, human_positions):
        if not zombie_positions:
            return []
        # Split the zombies into one chunk per worker
        size = math.ceil(len(zombie_positions) / self.workers)
        chunks = [zombie_positions[i:i + size]
                  for i in range(0, len(zombie_positions), size)]
        # Every worker searches its own chunk AT THE SAME TIME
        parts = self.pool.starmap(find_nearest,
                                  [(chunk, human_positions) for chunk in chunks])
        # Put the results back together, in the original order
        return [t for part in parts for t in part]

    def close(self):
        self.pool.close()
        self.pool.join()
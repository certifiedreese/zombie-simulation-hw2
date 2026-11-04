# ============================================================
# benchmark.py - Experiments
#
# Runs the simulation with no window and no FPS cap, and measures
# how long each frame takes for different agent counts, storage
# options, and neighbor-finders. Prints a table for results.md.
# ============================================================

import time
import random
import simulation
from simulation import Simulation
from storage import InMemoryStore, SQLiteStore
from neighbors import SerialFinder, ParallelFinder

FRAMES = 50  # frames to run for each test
SIZES = [(1000, 50), (5000, 250), (10000, 500)]  # (humans, zombies)


class TimedFinder:
    """Wraps any finder and measures how long its neighbor-finding takes."""

    def __init__(self, finder):
        self.finder = finder
        self.total = 0.0

    def find(self, zombie_positions, human_positions):
        start = time.perf_counter()
        result = self.finder.find(zombie_positions, human_positions)
        self.total += time.perf_counter() - start
        return result


def run(store, finder, humans, zombies):
    # Set the agent counts for this test
    simulation.NUM_HUMANS = humans
    simulation.NUM_ZOMBIES = zombies

    timed = TimedFinder(finder)
    sim = Simulation(store, timed)
    random.seed(42)  # same random start for every test, so it's fair
    sim.new_game()

    start = time.perf_counter()
    frames = 0
    for _ in range(FRAMES):
        if sim.result() is not None:
            break
        sim.step()
        frames += 1
    total = time.perf_counter() - start

    ms_per_frame = total / frames * 1000
    neighbor_ms = timed.total / frames * 1000
    return ms_per_frame, neighbor_ms


def main():
    serial = SerialFinder()
    parallel = ParallelFinder(workers=4)

    print("| Agents (H/Z) | Storage | Finder | ms per frame | neighbor-finding ms |")
    print("|---|---|---|---|---|")
    for humans, zombies in SIZES:
        for store_name, make_store in [("InMemory", InMemoryStore), ("SQLite", SQLiteStore)]:
            for finder_name, finder in [("Serial", serial), ("Parallel", parallel)]:
                ms, nms = run(make_store(), finder, humans, zombies)
                print(f"| {humans}/{zombies} | {store_name} | {finder_name} | {ms:.1f} | {nms:.1f} |")

    parallel.close()


if __name__ == "__main__":
    main()
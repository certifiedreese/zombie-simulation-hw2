# ============================================================
# benchmark.py - Experiments
#
# Runs the simulation with no window and no FPS cap, and measures
# how long each frame takes for different agent counts, storage
# options, and finders (serial vs parallel). Each test runs several
# times and the times are averaged. Prints a table for results.md.
# ============================================================

import time
import random
import simulation
from simulation import Simulation
from storage import InMemoryStore, SQLiteStore
from neighbors import SerialFinder, ParallelFinder

FRAMES = 50    # frames per run
REPEATS = 3    # runs per test, averaged
SIZES = [(1000, 50), (5000, 250), (10000, 500)]  # (humans, zombies)


class TimedFinder:
    """Wraps any finder and times its two jobs separately."""

    def __init__(self, finder):
        self.finder = finder
        self.neighbor_time = 0.0
        self.event_time = 0.0

    def find(self, zombie_positions, human_positions):
        start = time.perf_counter()
        result = self.finder.find(zombie_positions, human_positions)
        self.neighbor_time += time.perf_counter() - start
        return result

    def find_contacts(self, zombie_positions, human_positions):
        start = time.perf_counter()
        result = self.finder.find_contacts(zombie_positions, human_positions)
        self.event_time += time.perf_counter() - start
        return result


def run_once(make_store, finder, humans, zombies):
    simulation.NUM_HUMANS = humans
    simulation.NUM_ZOMBIES = zombies

    timed = TimedFinder(finder)
    sim = Simulation(make_store(), timed)
    random.seed(42)  # same random start every time, so tests are fair
    sim.new_game()

    start = time.perf_counter()
    frames = 0
    for _ in range(FRAMES):
        if sim.result() is not None:
            break
        sim.step()
        frames += 1
    total = time.perf_counter() - start

    return (total / frames * 1000,                # ms per frame
            timed.neighbor_time / frames * 1000,  # neighbor-finding ms
            timed.event_time / frames * 1000,     # event detection ms
            len(sim.get_humans()))                # humans left at the end


def run(make_store, finder, humans, zombies):
    # Run the test REPEATS times and average the times
    frame_ms = neighbor_ms = event_ms = 0.0
    for _ in range(REPEATS):
        f, n, e, left = run_once(make_store, finder, humans, zombies)
        frame_ms += f
        neighbor_ms += n
        event_ms += e
    return frame_ms / REPEATS, neighbor_ms / REPEATS, event_ms / REPEATS, left


def main():
    serial = SerialFinder()
    parallel = ParallelFinder(workers=4)

    print("| Agents (H/Z) | Storage | Finder | ms per frame | neighbor ms | event ms | humans left |")
    print("|---|---|---|---|---|---|---|")
    for humans, zombies in SIZES:
        for store_name, make_store in [("InMemory", InMemoryStore), ("SQLite", SQLiteStore)]:
            for finder_name, finder in [("Serial", serial), ("Parallel", parallel)]:
                f, n, e, left = run(make_store, finder, humans, zombies)
                print(f"| {humans}/{zombies} | {store_name} | {finder_name} "
                      f"| {f:.1f} | {n:.1f} | {e:.1f} | {left} |")

    parallel.close()


if __name__ == "__main__":
    main()
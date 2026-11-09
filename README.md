# Zombie Simulation – CPS 310 Assignment 2

**Author:** Reese Franklin

## What This Is
A zombie simulation that runs with thousands of agents. It uses a database
to store the agents, and splits the heavy work across several CPU cores so
it runs faster.

## How to Run
1. Install pygame-ce: `pip install pygame-ce`
2. Play the game: `python main.py` (press R to restart)
3. Run the experiments: `python benchmark.py`

To switch options, change one line in `main.py`:
- Storage: `store = SQLiteStore()` or `store = InMemoryStore()`
- Speed mode: `finder = ParallelFinder(workers=4)` or `finder = SerialFinder()`

## The Files
| File | Job |
|---|---|
| `main.py` | Opens the window and draws everything |
| `simulation.py` | The game rules: moving, chasing, fighting |
| `storage.py` | Saves the agents (database or memory) |
| `neighbors.py` | Finds nearby agents, using one core or several |
| `benchmark.py` | Times the simulation for the experiments |
| `results.md` | All experiment results |

## How It Works

### 1. More agents
The simulation runs with 1,000 to 10,000 humans, instead of 20.

### 2. A database
Every human and zombie is saved as a row in a SQLite database table.
The game can also use plain memory instead. Switching is one line,
and the game rules don't change.

### 3. A grid
The map is split into squares. A zombie only looks at humans in the
squares near it, instead of every human on the map. This is much faster.

### 4. Parallel neighbor-finding
Each zombie has to find the closest human to chase. The zombies are
split into 4 groups, and 4 CPU cores each handle one group at the
same time.

### 5. Parallel event processing
Events are the fights when a zombie touches a human. This happens in
two parts:
- **Detect (parallel):** the 4 cores each check their group of zombies
  for touching humans. This is just looking, so it's safe to do at
  the same time.
- **Resolve (one at a time):** the fights are then applied in order.
  This makes sure no human gets bitten twice by two zombies at once.
I used processes instead of threads because Python only lets one
thread run at a time (the GIL). Separate processes can truly run at
the same time.

## Experiments
I timed each frame (lower is faster) at three sizes, with both
storages and both speed modes. Each test ran 3 times and was averaged.
Full tables are in `results.md`.

| Test | One core | Four cores | Result |
|---|---|---|---|
| 1,000 humans, whole frame (InMemory) | 11.1 ms | 13.9 ms | Parallel slightly slower |
| 5,000 humans, whole frame (InMemory) | 169.9 ms | 80.3 ms | About 2x faster |
| 5,000 humans, neighbor-finding (InMemory) | 79.7 ms | 24.3 ms | About 3x faster |
| 10,000 humans, neighbor-finding (SQLite) | 127.3 ms | 52.5 ms | About 2.4x faster |

### What I Learned
- **Same results:** the number of humans left was the same with one core
  or four, so parallel only changed the speed, not the outcome.
- **Small sizes:** parallel was slower, because sending work to the cores
  takes time. With little work, that cost isn't worth it.
- **Big sizes:** parallel was 2 to 3 times faster, because there is
  enough work to split up.
- **Not 4x faster:** some time is always spent sending data to the cores
  and collecting the answers.
- **The database adds time:** saving thousands of rows every frame is
  done one step at a time, so it limits the total speedup.

### Limitations
- The map stays the same size, so big tests are very crowded and the
  zombies take over fast (all humans were gone within 50 frames at 10,000).
- Some results vary between runs because of other things happening
  on the computer.
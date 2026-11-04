# Experimental Results

## Before optimization (1000 humans, 50 zombies)
| Storage  | FPS at start | FPS late in game |
|----------|--------------|------------------|
| InMemory | ~17          | rises sharply    |
| SQLite   | ~7-8         | ~13              |
## After spatial grid (1000 humans, 50 zombies)
| Storage  | FPS at start | Change from before |
|----------|--------------|--------------------|
| InMemory | ~40          | ~17 → ~40          |
| SQLite   | ~15          | ~7-8 → ~15         |

Summary: The grid means each zombie only checks humans in nearby squares
instead of all 1000, which roughly doubled the FPS for both storage options.
## Benchmark: serial vs parallel neighbor-finding
| Agents (H/Z) | Storage | Finder | ms per frame | neighbor-finding ms |
|---|---|---|---|---|
| 1000/50 | InMemory | Serial | 15.9 | 3.8 |
| 1000/50 | InMemory | Parallel | 14.1 | 3.8 |
| 1000/50 | SQLite | Serial | 29.5 | 3.4 |
| 1000/50 | SQLite | Parallel | 28.9 | 4.1 |
| 5000/250 | InMemory | Serial | 72.0 | 33.0 |
| 5000/250 | InMemory | Parallel | 51.4 | 17.0 |
| 5000/250 | SQLite | Serial | 121.2 | 35.7 |
| 5000/250 | SQLite | Parallel | 102.9 | 18.8 |
| 10000/500 | InMemory | Serial | 393.2 | 204.4 |
| 10000/500 | InMemory | Parallel | 281.5 | 71.4 |
| 10000/500 | SQLite | Serial | 331.3 | 128.3 |
| 10000/500 | SQLite | Parallel | 246.9 | 48.8 |
### Summary
- Parallel neighbor-finding (4 workers) gave no gain at 1,000 humans,
  about 1.9x speedup at 5,000, and about 2.9x at 10,000. Parallelism
  pays off when there is enough work to outweigh the overhead of
  sending data to the worker processes.
- The speedup is less than 4x because of fixed overhead: copying
  positions to each worker, each worker building its own grid, and
  collecting results.
- Whole-frame time improved less than neighbor-finding time, because
  movement, fights, and storage still run on one core (Amdahl's law).
- Some variation between runs is measurement noise (for example,
  SQLite vs InMemory at 10,000 for neighbor-finding, which is
  identical work). Repeated runs would give more precise averages.
  ## Final benchmark (averaged over 3 runs) 
| Agents (H/Z) | Storage | Finder | ms per frame | neighbor ms | event ms | humans left |
|---|---|---|---|---|---|---|
| 1000/50 | InMemory | Serial | 11.1 | 2.8 | 1.3 | 629 |
| 1000/50 | InMemory | Parallel | 13.9 | 3.4 | 2.5 | 629 |
| 1000/50 | SQLite | Serial | 29.8 | 3.9 | 1.8 | 629 |
| 1000/50 | SQLite | Parallel | 44.2 | 5.2 | 3.8 | 629 |
| 5000/250 | InMemory | Serial | 169.9 | 79.7 | 33.7 | 13 |
| 5000/250 | InMemory | Parallel | 80.3 | 24.3 | 13.5 | 13 |
| 5000/250 | SQLite | Serial | 269.6 | 85.5 | 36.8 | 13 |
| 5000/250 | SQLite | Parallel | 153.4 | 26.2 | 14.7 | 13 |
| 10000/500 | InMemory | Serial | 563.3 | 304.6 | 127.3 | 0 |
| 10000/500 | InMemory | Parallel | 135.3 | 52.8 | 27.8 | 0 |
| 10000/500 | SQLite | Serial | 322.8 | 127.3 | 53.8 | 0 |
| 10000/500 | SQLite | Parallel | 222.0 | 52.5 | 28.1 | 0 |
### Summary
- Correctness: "humans left" is identical for serial and parallel in every
  test, so parallelism changed the speed but not the simulation's results.
- Small scale (1,000/50): parallel was slower (11.1 vs 13.9 ms per frame),
  because sending data to 4 worker processes costs more than the work saved.
- Medium scale (5,000/250, InMemory): parallel was about 3.3x faster for
  neighbor-finding, 2.5x for event detection, and 2.1x for the whole frame.
- Large scale (10,000/500, SQLite): about 2.4x faster for neighbor-finding
  and 1.9x for event detection. The InMemory serial time at this size
  (304.6 ms) is much higher than SQLite serial (127.3 ms) for identical
  neighbor-finding work, so it is likely affected by overhead outside the
  algorithm, possibly Python garbage collection in the main process.
- Speedups stay below 4x with 4 workers because of fixed overhead (copying
  positions to workers, each worker building its own grid, collecting results).
- The database adds a large serial cost (about 73 ms per frame at 5,000
  with parallel finding), which limits whole-frame speedup (Amdahl's law).
- Limitation: the map size is fixed, so larger tests are much more crowded
  and infection spreads faster (all humans were gone within 50 frames at
  10,000). Scaling the map with the agent count would keep tests comparable.
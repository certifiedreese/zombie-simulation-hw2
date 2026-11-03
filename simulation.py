# ============================================================
# simulation.py - Simulation logic layer
#
# All the game RULES live here: how agents move, chase, and fight.
# This file never keeps state itself. It reads and writes state
# ONLY through a StateStore, so it works with ANY storage option.
# It also doesn't use pygame, so the rules don't depend on drawing.
# ============================================================

import random
import math

# ---------- SETTINGS ----------
WIDTH, HEIGHT = 800, 600
NUM_HUMANS = 1000
NUM_ZOMBIES = 50
FIGHT_CHANCE = 0.4    # chance a human kills the zombie instead of being infected
TIME_LIMIT = 45       # seconds until rescue arrives
FPS = 60
CELL_SIZE = 50        # size of each grid square, in pixels
VISION_RADIUS = 100   # how far a zombie can see a human
TOUCH_DISTANCE = 13   # human radius 6 + zombie radius 7


# ---------- SPATIAL GRID ----------
class SpatialGrid:
    """Splits the map into squares so agents only check nearby squares."""

    def __init__(self, agents, cell_size=CELL_SIZE):
        self.cell_size = cell_size
        self.cells = {}  # (column, row) -> list of agents in that square
        for a in agents:
            self.cells.setdefault(self.key(a.x, a.y), []).append(a)

    def key(self, x, y):
        # Which square a position falls in
        return (int(x // self.cell_size), int(y // self.cell_size))

    def nearby(self, x, y, radius):
        # Return every agent in the squares within `radius` pixels of (x, y)
        r = math.ceil(radius / self.cell_size)  # how many squares out to look
        cx, cy = self.key(x, y)
        found = []
        for gx in range(cx - r, cx + r + 1):
            for gy in range(cy - r, cy + r + 1):
                found.extend(self.cells.get((gx, gy), []))
        return found


# ---------- HUMAN AGENT ----------
class Human:
    def __init__(self):
        self.id = None  # given by the storage when the human is saved
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(0.5, 1.4)
        self.dx = math.cos(angle) * speed
        self.dy = math.sin(angle) * speed

    def to_dict(self):
        return {"id": self.id, "kind": "human",
                "x": self.x, "y": self.y,
                "dx": self.dx, "dy": self.dy, "speed": 0}

    @classmethod
    def from_dict(cls, data):
        h = cls()
        h.id = data["id"]
        h.x, h.y = data["x"], data["y"]
        h.dx, h.dy = data["dx"], data["dy"]
        return h

    def update(self):
        self.x += self.dx
        self.y += self.dy
        if self.x < 0 or self.x > WIDTH:
            self.dx = -self.dx
        if self.y < 0 or self.y > HEIGHT:
            self.dy = -self.dy


# ---------- ZOMBIE AGENT ----------
class Zombie:
    def __init__(self, x=None, y=None):
        self.id = None
        self.x = x if x is not None else random.randint(0, WIDTH)
        self.y = y if y is not None else random.randint(0, HEIGHT)
        self.speed = 1.5
        # Wandering direction, used when no human is in sight
        angle = random.uniform(0, 2 * math.pi)
        self.dx = math.cos(angle)
        self.dy = math.sin(angle)

    def to_dict(self):
        return {"id": self.id, "kind": "zombie",
                "x": self.x, "y": self.y,
                "dx": self.dx, "dy": self.dy, "speed": self.speed}

    @classmethod
    def from_dict(cls, data):
        z = cls(data["x"], data["y"])
        z.id = data["id"]
        z.dx, z.dy = data["dx"], data["dy"]
        z.speed = data["speed"]
        return z

    def update(self, grid):
        # Only look at humans in the nearby grid squares
        closest = None
        closest_dist = VISION_RADIUS  # ignore anyone farther than vision range
        for h in grid.nearby(self.x, self.y, VISION_RADIUS):
            d = math.hypot(h.x - self.x, h.y - self.y)
            if d < closest_dist:
                closest = h
                closest_dist = d

        if closest is not None and closest_dist > 0:
            # Chase the closest human in sight
            dx = closest.x - self.x
            dy = closest.y - self.y
            self.x += dx / closest_dist * self.speed
            self.y += dy / closest_dist * self.speed
        else:
            # Nobody in sight: wander and bounce off walls
            self.x += self.dx
            self.y += self.dy
            if self.x < 0 or self.x > WIDTH:
                self.dx = -self.dx
            if self.y < 0 or self.y > HEIGHT:
                self.dy = -self.dy


# ---------- THE SIMULATION ----------
class Simulation:
    def __init__(self, store):
        # store can be ANY StateStore. The simulation never asks which kind.
        self.store = store

    def new_game(self):
        self.store.clear()
        self.store.set_value("width", WIDTH)
        self.store.set_value("height", HEIGHT)
        self.store.set_value("frames", 0)
        for _ in range(NUM_HUMANS):
            h = Human()
            h.id = self.store.add_agent(h.to_dict())
        for _ in range(NUM_ZOMBIES):
            z = Zombie()
            z.id = self.store.add_agent(z.to_dict())
        self.store.save()

    def get_humans(self):
        return [Human.from_dict(d) for d in self.store.get_agents("human")]

    def get_zombies(self):
        return [Zombie.from_dict(d) for d in self.store.get_agents("zombie")]

    def seconds(self):
        return self.store.get_value("frames", 0) // FPS

    def result(self):
        if len(self.get_zombies()) == 0:
            return "Humans survived!"
        if len(self.get_humans()) == 0:
            return "Zombies took over!"
        if self.seconds() >= TIME_LIMIT:
            return "Rescue arrived!"
        return None

    def step(self):
        if self.result() is not None:
            return  # game over: nothing changes

        # 1) Load the current state from storage
        humans = self.get_humans()
        zombies = self.get_zombies()
        self.store.set_value("frames", self.store.get_value("frames", 0) + 1)

        # 2) Humans move, then we build the grid of where they are now
        for h in humans:
            h.update()
        grid = SpatialGrid(humans)

        # 3) Zombies chase, using the grid to find nearby humans
        for z in zombies:
            z.update(grid)

        # 4) Fights: each zombie only checks humans in its own and neighboring squares
        new_zombies = []
        dead_zombies = []
        infected = set()  # ids of humans bitten this frame
        for z in zombies:
            for h in grid.nearby(z.x, z.y, TOUCH_DISTANCE):
                if h.id in infected:
                    continue  # already bitten by another zombie this frame
                if math.hypot(h.x - z.x, h.y - z.y) < TOUCH_DISTANCE:
                    if random.random() < FIGHT_CHANCE:
                        dead_zombies.append(z)
                        break
                    else:
                        infected.add(h.id)
                        self.store.remove_agent(h.id)
                        new_zombies.append(Zombie(h.x, h.y))
        for z in dead_zombies:
            zombies.remove(z)
            self.store.remove_agent(z.id)
        humans = [h for h in humans if h.id not in infected]

        # 5) Save the new state back to storage
        for h in humans:
            self.store.update_agent(h.to_dict())
        for z in zombies:
            self.store.update_agent(z.to_dict())
        for z in new_zombies:
            z.id = self.store.add_agent(z.to_dict())
        self.store.save()
# ============================================================
# simulation.py - Simulation logic layer
#
# All the game RULES live here: how agents move, chase, and fight.
# State is read and written ONLY through a StateStore, and
# neighbor-finding and event detection are done ONLY through a
# finder object, so the rules work with any storage and any finder.
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


# ---------- HUMAN AGENT ----------
class Human:
    def __init__(self):
        self.id = None
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

    def chase(self, human):
        dx = human.x - self.x
        dy = human.y - self.y
        dist = math.hypot(dx, dy)
        if dist > 0:
            self.x += dx / dist * self.speed
            self.y += dy / dist * self.speed

    def wander(self):
        self.x += self.dx
        self.y += self.dy
        if self.x < 0 or self.x > WIDTH:
            self.dx = -self.dx
        if self.y < 0 or self.y > HEIGHT:
            self.dy = -self.dy


# ---------- THE SIMULATION ----------
class Simulation:
    def __init__(self, store, finder):
        # store:  ANY StateStore (in-memory, SQLite, ...)
        # finder: ANY finder (serial or parallel)
        self.store = store
        self.finder = finder

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

        # 2) Humans move
        for h in humans:
            h.update()
        human_positions = [(h.x, h.y) for h in humans]

        # 3) NEIGHBOR-FINDING: which human each zombie chases (serial or parallel)
        zombie_positions = [(z.x, z.y) for z in zombies]
        targets = self.finder.find(zombie_positions, human_positions)
        for z, t in zip(zombies, targets):
            if t >= 0:
                z.chase(humans[t])
            else:
                z.wander()

        # 4) EVENT PROCESSING
        # 4a) DETECT: which humans each zombie is touching (serial or parallel)
        zombie_positions = [(z.x, z.y) for z in zombies]  # zombies just moved
        contacts = self.finder.find_contacts(zombie_positions, human_positions)

        # 4b) RESOLVE: apply the fights one at a time, in order,
        #     so each human can only be bitten once (no race conditions)
        new_zombies = []
        dead_zombies = []
        infected = set()  # indexes of humans bitten this frame
        for z, touching in zip(zombies, contacts):
            for i in touching:
                if i in infected:
                    continue  # already bitten by another zombie this frame
                if random.random() < FIGHT_CHANCE:
                    dead_zombies.append(z)  # human wins
                    break
                else:
                    infected.add(i)  # zombie wins: human becomes a zombie
                    h = humans[i]
                    self.store.remove_agent(h.id)
                    new_zombies.append(Zombie(h.x, h.y))
        for z in dead_zombies:
            zombies.remove(z)
            self.store.remove_agent(z.id)
        humans = [h for i, h in enumerate(humans) if i not in infected]

        # 5) Save the new state back to storage
        for h in humans:
            self.store.update_agent(h.to_dict())
        for z in zombies:
            self.store.update_agent(z.to_dict())
        for z in new_zombies:
            z.id = self.store.add_agent(z.to_dict())
        self.store.save()
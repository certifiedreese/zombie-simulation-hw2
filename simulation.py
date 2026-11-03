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
NUM_HUMANS = 20
NUM_ZOMBIES = 3
FIGHT_CHANCE = 0.4  # chance a human kills the zombie instead of being infected
TIME_LIMIT = 45     # seconds until rescue arrives
FPS = 60


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
        # Turn this human into plain data so ANY storage can save it
        return {"id": self.id, "kind": "human",
                "x": self.x, "y": self.y,
                "dx": self.dx, "dy": self.dy, "speed": 0}

    @classmethod
    def from_dict(cls, data):
        # Rebuild a human object from stored data
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

    def to_dict(self):
        return {"id": self.id, "kind": "zombie",
                "x": self.x, "y": self.y,
                "dx": 0, "dy": 0, "speed": self.speed}

    @classmethod
    def from_dict(cls, data):
        z = cls(data["x"], data["y"])
        z.id = data["id"]
        z.speed = data["speed"]
        return z

    def update(self, humans):
        closest = None
        closest_dist = float("inf")
        for h in humans:
            d = math.hypot(h.x - self.x, h.y - self.y)
            if d < closest_dist:
                closest = h
                closest_dist = d

        if closest is not None and closest_dist > 0:
            dx = closest.x - self.x
            dy = closest.y - self.y
            self.x += dx / closest_dist * self.speed
            self.y += dy / closest_dist * self.speed


# ---------- THE SIMULATION ----------
class Simulation:
    def __init__(self, store):
        # store can be ANY StateStore. The simulation never asks which kind.
        self.store = store

    def new_game(self):
        self.store.clear()
        # Environment state
        self.store.set_value("width", WIDTH)
        self.store.set_value("height", HEIGHT)
        # Runtime state
        self.store.set_value("frames", 0)
        # Agent state
        for _ in range(NUM_HUMANS):
            h = Human()
            h.id = self.store.add_agent(h.to_dict())
        for _ in range(NUM_ZOMBIES):
            z = Zombie()
            z.id = self.store.add_agent(z.to_dict())

    def get_humans(self):
        return [Human.from_dict(d) for d in self.store.get_agents("human")]

    def get_zombies(self):
        return [Zombie.from_dict(d) for d in self.store.get_agents("zombie")]

    def seconds(self):
        return self.store.get_value("frames", 0) // FPS

    def result(self):
        # Returns the end message, or None if the game is still going
        if len(self.get_zombies()) == 0:
            return "Humans survived!"
        if len(self.get_humans()) == 0:
            return "Zombies took over!"
        if self.seconds() >= TIME_LIMIT:
            return "Rescue arrived!"
        return None

    def step(self):
        # Advance the simulation by one frame
        if self.result() is not None:
            return  # game over: nothing changes

        # 1) Load the current state from storage
        humans = self.get_humans()
        zombies = self.get_zombies()
        self.store.set_value("frames", self.store.get_value("frames", 0) + 1)

        # 2) Apply the rules: movement
        for h in humans:
            h.update()
        for z in zombies:
            z.update(humans)

        # 3) Apply the rules: fights
        new_zombies = []
        dead_zombies = []
        for z in zombies:
            for h in humans[:]:
                if math.hypot(h.x - z.x, h.y - z.y) < 13:
                    if random.random() < FIGHT_CHANCE:
                        dead_zombies.append(z)
                        break
                    else:
                        humans.remove(h)
                        self.store.remove_agent(h.id)
                        new_zombies.append(Zombie(h.x, h.y))
        for z in dead_zombies:
            zombies.remove(z)
            self.store.remove_agent(z.id)

        # 4) Save the new state back to storage
        for h in humans:
            self.store.update_agent(h.to_dict())
        for z in zombies:
            self.store.update_agent(z.to_dict())
        for z in new_zombies:
            z.id = self.store.add_agent(z.to_dict())
        self.store.save()
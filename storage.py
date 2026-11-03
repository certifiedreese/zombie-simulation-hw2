# ============================================================
# storage.py - State storage layer
#
# StateStore is the INTERFACE: the list of rules every storage
# option must follow. The simulation only talks to these methods,
# so it never knows HOW or WHERE the state is actually stored.
# ============================================================

from abc import ABC, abstractmethod
import sqlite3


class StateStore(ABC):
    """Rules every storage option must follow."""

    # ---------- AGENTS ----------
    # Agents are stored as plain dictionaries, for example:
    # {"id": 1, "kind": "human", "x": 100, "y": 200, "dx": 1.0, "dy": -0.5, "speed": 0}

    @abstractmethod
    def add_agent(self, data):
        """Store a new agent and return its new id."""

    @abstractmethod
    def update_agent(self, data):
        """Save an agent's changed data (like a new position)."""

    @abstractmethod
    def remove_agent(self, agent_id):
        """Delete an agent."""

    @abstractmethod
    def get_agents(self, kind):
        """Return a list of all agents of one kind ("human" or "zombie")."""

    # ---------- ENVIRONMENT AND RUNTIME ----------
    # Simple named values, like "frames" or "width".

    @abstractmethod
    def set_value(self, key, value):
        """Save a named value."""

    @abstractmethod
    def get_value(self, key, default=None):
        """Read a named value, or return default if it isn't saved yet."""

    # ---------- RESET AND SAVE ----------

    @abstractmethod
    def clear(self):
        """Delete everything, for starting a new game."""

    @abstractmethod
    def save(self):
        """Make all changes since the last save permanent."""


# ============================================================
# Storage option 1: IN-MEMORY
# Keeps all state in Python dictionaries (in RAM).
# ============================================================
class InMemoryStore(StateStore):

    def __init__(self):
        self.agents = {}   # agent id -> agent dictionary
        self.values = {}   # name -> value (like "frames")
        self.next_id = 1   # the id the next new agent will get

    def add_agent(self, data):
        agent_id = self.next_id
        self.next_id += 1
        data = dict(data)           # make our own copy
        data["id"] = agent_id
        self.agents[agent_id] = data
        return agent_id

    def update_agent(self, data):
        self.agents[data["id"]] = dict(data)

    def remove_agent(self, agent_id):
        self.agents.pop(agent_id, None)  # None = don't crash if it's already gone

    def get_agents(self, kind):
        # Return copies of every agent whose kind matches
        return [dict(a) for a in self.agents.values() if a["kind"] == kind]

    def set_value(self, key, value):
        self.values[key] = value

    def get_value(self, key, default=None):
        return self.values.get(key, default)

    def clear(self):
        self.agents.clear()
        self.values.clear()
        self.next_id = 1

    def save(self):
        pass  # changes in RAM are already "saved", so nothing to do


# ============================================================
# Storage option 2: SQLITE DATABASE
# Keeps all state in SQL tables inside a database file.
# ============================================================
class SQLiteStore(StateStore):

    def __init__(self, filename="zombie_state.db"):
        self.conn = sqlite3.connect(filename)
        # Speed setting: don't wait for the disk on every save (fine for a game)
        self.conn.execute("PRAGMA synchronous = OFF")

        # One row per agent
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id    INTEGER PRIMARY KEY,
                kind  TEXT,
                x     REAL,
                y     REAL,
                dx    REAL,
                dy    REAL,
                speed REAL
            )""")

        # One row per named value (frames, width, height)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS runtime (
                key   TEXT PRIMARY KEY,
                value NUMERIC
            )""")
        self.conn.commit()

    def add_agent(self, data):
        cur = self.conn.execute(
            "INSERT INTO agents (kind, x, y, dx, dy, speed) VALUES (?, ?, ?, ?, ?, ?)",
            (data["kind"], data["x"], data["y"], data["dx"], data["dy"], data["speed"]))
        return cur.lastrowid  # the id the database gave the new row

    def update_agent(self, data):
        self.conn.execute(
            "UPDATE agents SET x = ?, y = ?, dx = ?, dy = ?, speed = ? WHERE id = ?",
            (data["x"], data["y"], data["dx"], data["dy"], data["speed"], data["id"]))

    def remove_agent(self, agent_id):
        self.conn.execute("DELETE FROM agents WHERE id = ?", (agent_id,))

    def get_agents(self, kind):
        rows = self.conn.execute(
            "SELECT id, kind, x, y, dx, dy, speed FROM agents WHERE kind = ?",
            (kind,)).fetchall()
        # Turn each database row back into a plain dictionary
        return [{"id": r[0], "kind": r[1], "x": r[2], "y": r[3],
                 "dx": r[4], "dy": r[5], "speed": r[6]} for r in rows]

    def set_value(self, key, value):
        self.conn.execute(
            "INSERT OR REPLACE INTO runtime (key, value) VALUES (?, ?)", (key, value))

    def get_value(self, key, default=None):
        row = self.conn.execute(
            "SELECT value FROM runtime WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default

    def clear(self):
        self.conn.execute("DELETE FROM agents")
        self.conn.execute("DELETE FROM runtime")

    def save(self):
        self.conn.commit()  # make this frame's changes permanent in the file
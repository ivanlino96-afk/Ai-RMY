"""SQLite-backed store for known people and their face embeddings.

No vector DB: at the scale this runs at (tens of people, a handful of
embeddings each), brute-force cosine similarity over everything in the
table with numpy is microseconds — see AGENTS.md/architecture.md for why
FAISS/Milvus would be overkill here.

Biometric data (this DB, the photos it references) must never be
committed — see .gitignore and AGENTS.md.
"""

import os
import sqlite3
import time
from typing import NamedTuple, Optional

import numpy as np

from vision.config import StorageConfig

_SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    vector BLOB NOT NULL,
    photo_path TEXT,
    created_at REAL NOT NULL
);
"""


class Person(NamedTuple):
    id: int
    name: str
    notes: str
    created_at: float


class Match(NamedTuple):
    person_id: int
    name: str
    score: float


class FaceRepository(object):
    def __init__(self, config=None):
        self.config = config or StorageConfig()
        self._config = self.config
        db_dir = os.path.dirname(self._config.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._conn = sqlite3.connect(self._config.db_path, check_same_thread=False)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self):
        self._conn.close()

    # -- people -----------------------------------------------------------

    def add_person(self, name, notes=""):
        cur = self._conn.execute(
            "INSERT INTO people (name, notes, created_at) VALUES (?, ?, ?)",
            (name, notes, time.time()),
        )
        self._conn.commit()
        return cur.lastrowid

    def get_person(self, person_id):
        row = self._conn.execute(
            "SELECT id, name, notes, created_at FROM people WHERE id = ?",
            (person_id,),
        ).fetchone()
        return Person(*row) if row else None

    def list_people(self):
        rows = self._conn.execute(
            "SELECT id, name, notes, created_at FROM people ORDER BY name"
        ).fetchall()
        return [Person(*row) for row in rows]

    def update_person(self, person_id, name=None, notes=None):
        current = self.get_person(person_id)
        if current is None:
            return False
        new_name = name if name is not None else current.name
        new_notes = notes if notes is not None else current.notes
        self._conn.execute(
            "UPDATE people SET name = ?, notes = ? WHERE id = ?",
            (new_name, new_notes, person_id),
        )
        self._conn.commit()
        return True

    def delete_person(self, person_id):
        cur = self._conn.execute("DELETE FROM people WHERE id = ?", (person_id,))
        self._conn.commit()
        return cur.rowcount > 0

    # -- embeddings ---------------------------------------------------------

    def add_embedding(self, person_id, vector, photo_path=None):
        vector = np.asarray(vector, dtype=np.float32)
        self._conn.execute(
            "INSERT INTO embeddings (person_id, vector, photo_path, created_at) "
            "VALUES (?, ?, ?, ?)",
            (person_id, vector.tobytes(), photo_path, time.time()),
        )
        self._conn.commit()

    def list_embeddings(self, person_id=None):
        if person_id is None:
            rows = self._conn.execute(
                "SELECT person_id, vector FROM embeddings"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT person_id, vector FROM embeddings WHERE person_id = ?",
                (person_id,),
            ).fetchall()
        return [
            (pid, np.frombuffer(blob, dtype=np.float32)) for pid, blob in rows
        ]

    def latest_photo_path(self, person_id):
        row = self._conn.execute(
            "SELECT photo_path FROM embeddings "
            "WHERE person_id = ? AND photo_path IS NOT NULL "
            "ORDER BY created_at DESC LIMIT 1",
            (person_id,),
        ).fetchone()
        return row[0] if row else None

    # -- matching -----------------------------------------------------------

    def find_best_match(self, vector, threshold):
        """Brute-force cosine similarity against every stored embedding.

        Returns the best Match if its score clears `threshold`, else None
        (caller should report "Unknown" rather than a low-confidence name).
        """
        query = np.asarray(vector, dtype=np.float32)
        query_norm = np.linalg.norm(query)
        if query_norm == 0:
            return None

        rows = self._conn.execute(
            "SELECT person_id, vector FROM embeddings"
        ).fetchall()
        if not rows:
            return None

        best_person_id = None
        best_score = -1.0
        for person_id, blob in rows:
            candidate = np.frombuffer(blob, dtype=np.float32)
            candidate_norm = np.linalg.norm(candidate)
            if candidate_norm == 0:
                continue
            score = float(np.dot(query, candidate) / (query_norm * candidate_norm))
            if score > best_score:
                best_score = score
                best_person_id = person_id

        if best_person_id is None or best_score < threshold:
            return None

        person = self.get_person(best_person_id)
        name = person.name if person else "Unknown"
        return Match(person_id=best_person_id, name=name, score=best_score)

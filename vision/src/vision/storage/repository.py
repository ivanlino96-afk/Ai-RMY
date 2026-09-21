"""SQLite-backed store for known people and their face embeddings.

No vector DB: at the scale this runs at (tens of people, a handful of
embeddings each), brute-force cosine similarity over everything in the
table with numpy is microseconds — see AGENTS.md/architecture.md for why
FAISS/Milvus would be overkill here.

Biometric data (this DB, the photos it references) must never be
committed — see .gitignore and AGENTS.md.
"""

import os
import shutil
import sqlite3
import time
from typing import List, NamedTuple, Optional

import numpy as np

from vision.config import StorageConfig
from vision.recognition.similarity import cosine_similarity

_SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    vector BLOB NOT NULL,
    photo_path TEXT,
    pose TEXT,
    created_at REAL NOT NULL
);
"""


class Person(NamedTuple):
    id: int
    name: str
    age: int
    email: str
    phone: str
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

    def add_person(self, name, age, email, phone, notes=""):
        cur = self._conn.execute(
            "INSERT INTO people (name, age, email, phone, notes, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, age, email, phone, notes, time.time()),
        )
        self._conn.commit()
        return cur.lastrowid

    def get_person(self, person_id):
        row = self._conn.execute(
            "SELECT id, name, age, email, phone, notes, created_at FROM people "
            "WHERE id = ?",
            (person_id,),
        ).fetchone()
        return Person(*row) if row else None

    def list_people(self):
        rows = self._conn.execute(
            "SELECT id, name, age, email, phone, notes, created_at FROM people "
            "ORDER BY name"
        ).fetchall()
        return [Person(*row) for row in rows]

    def update_person(self, person_id, name=None, age=None, email=None, phone=None, notes=None):
        current = self.get_person(person_id)
        if current is None:
            return False
        new_name = name if name is not None else current.name
        new_age = age if age is not None else current.age
        new_email = email if email is not None else current.email
        new_phone = phone if phone is not None else current.phone
        new_notes = notes if notes is not None else current.notes
        self._conn.execute(
            "UPDATE people SET name = ?, age = ?, email = ?, phone = ?, notes = ? "
            "WHERE id = ?",
            (new_name, new_age, new_email, new_phone, new_notes, person_id),
        )
        self._conn.commit()
        return True

    def existe_duplicado(self, name, phone):
        """RF-7: a new enrollment must be rejected if its name or phone
        matches an already-registered (non-deleted) person. Deletion in
        this repository is a hard delete, so "non-deleted" is simply
        "still present in the table" — no soft-delete bookkeeping needed.
        """
        normalized_name = name.strip().lower()
        rows = self._conn.execute("SELECT name, phone FROM people").fetchall()
        for existing_name, existing_phone in rows:
            if existing_name.strip().lower() == normalized_name:
                return True
            if existing_phone == phone:
                return True
        return False

    def clear_embeddings(self, person_id):
        """Removes all embeddings/photos for a person without deleting the
        person row itself (RF-8: re-capturing photos on an existing person).
        """
        self._conn.execute("DELETE FROM embeddings WHERE person_id = ?", (person_id,))
        self._conn.commit()
        photos_dir = os.path.join(self._config.photos_dir, str(person_id))
        if os.path.isdir(photos_dir):
            shutil.rmtree(photos_dir)

    def delete_person(self, person_id):
        photos_dir = os.path.join(self._config.photos_dir, str(person_id))
        cur = self._conn.execute("DELETE FROM people WHERE id = ?", (person_id,))
        self._conn.commit()
        deleted = cur.rowcount > 0
        if deleted and os.path.isdir(photos_dir):
            shutil.rmtree(photos_dir)
        return deleted

    # -- embeddings ---------------------------------------------------------

    def add_embedding(self, person_id, vector, photo_path=None, pose=None):
        vector = np.asarray(vector, dtype=np.float32)
        self._conn.execute(
            "INSERT INTO embeddings (person_id, vector, photo_path, pose, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (person_id, vector.tobytes(), photo_path, pose, time.time()),
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
        matches = self.find_all_matches(vector, threshold)
        return matches[0] if matches else None

    def find_all_matches(self, vector, threshold):
        """All people whose best embedding scores >= threshold for `vector`,
        sorted by score descending (RF-18: on a tie/multiple match, the
        caller picks matches[0], the highest-confidence one).
        """
        query = np.asarray(vector, dtype=np.float32)
        if np.linalg.norm(query) == 0:
            return []

        rows = self._conn.execute("SELECT person_id, vector FROM embeddings").fetchall()

        best_score_by_person = {}
        for person_id, blob in rows:
            candidate = np.frombuffer(blob, dtype=np.float32)
            score = cosine_similarity(query, candidate)
            if score > best_score_by_person.get(person_id, -1.0):
                best_score_by_person[person_id] = score

        matches = []  # type: List[Match]
        for person_id, score in best_score_by_person.items():
            if score < threshold:
                continue
            person = self.get_person(person_id)
            name = person.name if person else "Unknown"
            matches.append(Match(person_id=person_id, name=name, score=score))

        matches.sort(key=lambda m: m.score, reverse=True)
        return matches

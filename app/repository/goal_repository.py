# app/repository/goal_repository.py
import sqlite3
from contextlib import contextmanager
from typing import List, Iterator, Optional

from app.core.models import Goal

class GoalRepository:
    """
    Handles all database operations for financial goals.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def create_table(self):
        """Creates the 'goals' table in the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    target_amount REAL NOT NULL,
                    current_amount REAL NOT NULL DEFAULT 0
                )
            """)
            conn.commit()

    def add_goal(self, name: str, target_amount: float) -> bool:
        """Adds a new goal."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO goals (name, target_amount) VALUES (?, ?)",
                    (name, target_amount)
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False # Goal name is likely not unique

    def get_all_goals(self) -> List[Goal]:
        """Retrieves all goals from the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, target_amount, current_amount FROM goals ORDER BY name ASC")
            return [Goal(**row) for row in cursor.fetchall()]

    def update_goal_progress(self, goal_id: int, amount_to_add: float) -> Optional[Goal]:
        """
        Adds a certain amount to the goal's current progress.
        Returns the updated goal object or None if not found.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # First, update the value
            cursor.execute(
                "UPDATE goals SET current_amount = current_amount + ? WHERE id = ?",
                (amount_to_add, goal_id)
            )
            conn.commit()

            # Then, fetch the updated goal to return it
            cursor.execute("SELECT * FROM goals WHERE id = ?", (goal_id,))
            row = cursor.fetchone()
            if row:
                return Goal(**row)
            return None

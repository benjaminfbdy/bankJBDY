# app/repository/budget_repository.py
import sqlite3
from contextlib import contextmanager
from typing import Dict, Iterator

class BudgetRepository:
    """
    Handles all database operations for monthly budgets.
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
        """
        Creates the 'budgets' table in the database.
        It links to the 'categories' table.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS budgets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER NOT NULL,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    FOREIGN KEY (category_id) REFERENCES categories (id),
                    UNIQUE(category_id, year, month)
                )
            """)
            conn.commit()

    def set_budget(self, category_id: int, year: int, month: int, amount: float):
        """
        Sets or updates the budget for a given category, month, and year.
        Uses INSERT OR REPLACE (UPSERT) to handle existing entries.
        """
        query = """
            INSERT INTO budgets (category_id, year, month, amount)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(category_id, year, month) DO UPDATE SET
            amount = excluded.amount;
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (category_id, year, month, amount))
            conn.commit()

    def get_budgets_for_month(self, year: int, month: int) -> Dict[int, float]:
        """
        Retrieves all budgets for a given month and year.

        Returns:
            A dictionary mapping category_id to the budget amount.
        """
        query = "SELECT category_id, amount FROM budgets WHERE year = ? AND month = ?"
        budgets = {}
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (year, month))
            for row in cursor.fetchall():
                budgets[row['category_id']] = row['amount']
        return budgets

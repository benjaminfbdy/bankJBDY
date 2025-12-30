# app/repository/transaction_repository.py
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from datetime import date, datetime
from typing import List, Iterator

from app.core.models import Transaction

class TransactionRepository:
    """
    Handles all database operations for transactions.
    """

    def __init__(self, db_path: str):
        """
        Initializes the repository with the path to the SQLite database.

        Args:
            db_path (str): The path to the database file.
        """
        self.db_path = db_path

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        """
        Provides a managed database connection.

        Yields:
            sqlite3.Connection: An active SQLite connection object.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def create_table(self):
        """
        Creates the 'transactions' table in the database if it doesn't already exist.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    hash TEXT PRIMARY KEY,
                    account_type TEXT NOT NULL,
                    date_compte TEXT,
                    libelle_simple TEXT,
                    libelle_op TEXT,
                    reference TEXT,
                    info_complementaires TEXT,
                    type_op TEXT,
                    categorie TEXT,
                    sous_categorie TEXT,
                    debit REAL,
                    credit REAL,
                    montant REAL,
                    date_op TEXT,
                    date_valeur TEXT,
                    pointage_op INTEGER,
                    type_budget TEXT
                )
            """)
            conn.commit()

    def add_many(self, transactions: List[Transaction]) -> int:
        """
        Adds a list of Transaction objects to the database, ignoring duplicates.

        Args:
            transactions (List[Transaction]): A list of transaction objects to add.

        Returns:
            int: The number of new rows inserted.
        """
        if not transactions:
            return 0

        records_to_insert = []
        for t in transactions:
            record = asdict(t)
            for key, value in record.items():
                if isinstance(value, (date, datetime)):
                    record[key] = value.isoformat() if value else None
            records_to_insert.append(record)

        insert_query = """
            INSERT OR IGNORE INTO transactions (
                hash, account_type, date_compte, libelle_simple, libelle_op, reference,
                info_complementaires, type_op, categorie, sous_categorie, debit, credit,
                montant, date_op, date_valeur, pointage_op, type_budget
            ) VALUES (
                :hash, :account_type, :date_compte, :libelle_simple, :libelle_op, :reference,
                :info_complementaires, :type_op, :categorie, :sous_categorie, :debit, :credit,
                :montant, :date_op, :date_valeur, :pointage_op, :type_budget
            )
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(insert_query, records_to_insert)
            inserted_rows = cursor.rowcount
            conn.commit()
            return inserted_rows

    def get_all(self) -> List[Transaction]:
        """
        Retrieves all transactions from the database.

        Returns:
            List[Transaction]: A list of all transactions as Transaction objects.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM transactions")
            rows = cursor.fetchall()
            # Convert rows back to Transaction objects
            return [Transaction(**row) for row in rows]

    def update_category(self, transaction_hash: str, category: str, sub_category: str):
        """
        Updates the category and sub-category of a specific transaction.

        Args:
            transaction_hash (str): The hash of the transaction to update.
            category (str): The new category.
            sub_category (str): The new sub-category.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE transactions SET categorie = ?, sous_categorie = ? WHERE hash = ?",
                (category, sub_category, transaction_hash)
            )
            conn.commit()

    def update_budget_type(self, transaction_hash: str, budget_type: str):
        """
        Updates the budget type of a specific transaction.

        Args:
            transaction_hash (str): The hash of the transaction to update.
            budget_type (str): The new budget type ('Ponctuel' or 'Récurrente').
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE transactions SET type_budget = ? WHERE hash = ?",
                (budget_type, transaction_hash)
            )
            conn.commit()

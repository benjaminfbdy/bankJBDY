# app/repository/net_worth_repository.py
import sqlite3
from contextlib import contextmanager
from typing import List, Iterator, Dict, Any
import pandas as pd

from app.core.models import Asset, Liability

class NetWorthRepository:
    """
    Handles all database operations for assets and liabilities.
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

    def create_tables(self):
        """Creates the 'assets' and 'liabilities' tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    value REAL NOT NULL DEFAULT 0
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS liabilities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    value REAL NOT NULL DEFAULT 0
                )
            """)
            conn.commit()

    def get_all_assets(self) -> List[Asset]:
        """Retrieves all assets from the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, value FROM assets ORDER BY name ASC")
            return [Asset(**row) for row in cursor.fetchall()]

    def get_all_liabilities(self) -> List[Liability]:
        """Retrieves all liabilities from the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, value FROM liabilities ORDER BY name ASC")
            return [Liability(**row) for row in cursor.fetchall()]

    def sync_items(self, table_name: str, df: pd.DataFrame):
        """
        Synchronizes a table (assets or liabilities) with a DataFrame from st.data_editor.
        This handles additions, updates, and deletions.
        """
        if table_name not in ['assets', 'liabilities']:
            raise ValueError("Invalid table name for sync")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get existing items from DB
            cursor.execute(f"SELECT id, name, value FROM {table_name}")
            db_items = {row['id']: dict(row) for row in cursor.fetchall()}
            
            # Get items from the DataFrame (from the UI)
            # st.data_editor adds NaNs for new rows
            df_items = df.dropna(subset=['name']).to_dict('records')
            
            db_ids = set(db_items.keys())
            df_ids = set(item['id'] for item in df_items if item.get('id'))

            # --- Deletions ---
            ids_to_delete = db_ids - df_ids
            if ids_to_delete:
                cursor.executemany(f"DELETE FROM {table_name} WHERE id = ?", [(id,) for id in ids_to_delete])

            # --- Inserts and Updates ---
            for item in df_items:
                item_id = item.get('id')
                # New item (no ID yet)
                if not item_id:
                    cursor.execute(f"INSERT INTO {table_name} (name, value) VALUES (?, ?)", (item['name'], item.get('value', 0)))
                # Existing item
                else:
                    # Check if it has changed before updating
                    if item['name'] != db_items[item_id]['name'] or item['value'] != db_items[item_id]['value']:
                        cursor.execute(f"UPDATE {table_name} SET name = ?, value = ? WHERE id = ?", (item['name'], item.get('value', 0), item_id))
            
            conn.commit()

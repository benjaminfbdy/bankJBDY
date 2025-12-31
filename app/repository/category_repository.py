# app/repository/category_repository.py
import sqlite3
from contextlib import contextmanager
from typing import List, Dict, Iterator, Tuple

class CategoryRepository:
    """
    Handles all database operations for categories and their rules.
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
        """
        Creates the 'categories' and 'categorization_rules' tables.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Create categories table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                )
            """)
            # Create rules table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categorization_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER NOT NULL,
                    keyword TEXT NOT NULL UNIQUE,
                    FOREIGN KEY (category_id) REFERENCES categories (id)
                )
            """)
            # Create sub_categories table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sub_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category_id INTEGER NOT NULL,
                    FOREIGN KEY (category_id) REFERENCES categories (id),
                    UNIQUE(name, category_id)
                )
            """)
            conn.commit()

    def add_category(self, name: str) -> bool:
        """Adds a new category. Returns False if it already exists."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO categories (name) VALUES (?)", (name,))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # Category name is likely not unique
                return False

    def add_sub_category(self, name: str, parent_category_name: str) -> bool:
        """Adds a new sub-category to a parent category."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT id FROM categories WHERE name = ?", (parent_category_name,))
                result = cursor.fetchone()
                if not result:
                    return False  # Parent category does not exist
                
                parent_category_id = result['id']
                cursor.execute(
                    "INSERT INTO sub_categories (name, category_id) VALUES (?, ?)",
                    (name, parent_category_id)
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # Combination of sub-category and parent probably exists
                return False

    def get_all_categories(self) -> List[str]:
        """Returns a list of all category names."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM categories ORDER BY name ASC")
            return [row['name'] for row in cursor.fetchall()]

    def get_category_id_map(self) -> Dict[str, int]:
        """Returns a dictionary mapping category names to their IDs."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM categories")
            return {row['name']: row['id'] for row in cursor.fetchall()}

    def get_all_sub_categories_as_map(self) -> Dict[str, List[str]]:
        """
        Returns a dictionary mapping parent categories to a list of their sub-categories.
        """
        query = """
            SELECT c.name as parent_category, sc.name as sub_category
            FROM categories c
            LEFT JOIN sub_categories sc ON c.id = sc.category_id
            ORDER BY c.name, sc.name
        """
        category_map = {}
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            for row in cursor.fetchall():
                parent = row['parent_category']
                sub = row['sub_category']
                if parent not in category_map:
                    category_map[parent] = []
                if sub:
                    category_map[parent].append(sub)
        return category_map

    def add_rule(self, category_name: str, keyword: str) -> bool:
        """Adds a new keyword rule for a given category."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                # Get category_id from name
                cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
                result = cursor.fetchone()
                if not result:
                    return False # Category does not exist
                
                category_id = result['id']
                cursor.execute("INSERT INTO categorization_rules (category_id, keyword) VALUES (?, ?)", (category_id, keyword))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # Keyword likely not unique
                return False

    def get_rules(self) -> Dict[str, List[str]]:
        """
        Retrieves all rules and formats them into a dictionary
        like the original CATEGORIZATION_RULES config.
        """
        query = """
            SELECT c.name, cr.keyword
            FROM categories c
            JOIN categorization_rules cr ON c.id = cr.category_id
        """
        rules = {}
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            for row in cursor.fetchall():
                category = row['name']
                keyword = row['keyword']
                if category not in rules:
                    rules[category] = []
                rules[category].append(keyword)
        return rules

    def seed_data(self, initial_rules: Dict[str, List[str]]):
        """
        Seeds the database with initial categories and rules from the config.
        This is intended to be run once on a fresh database.
        """
        # First, check if categories are already present
        if self.get_all_categories():
            return # Data is already seeded

        for category, keywords in initial_rules.items():
            self.add_category(category)
            for keyword in keywords:
                self.add_rule(category, keyword)

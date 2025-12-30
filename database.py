import sqlite3
import pandas as pd
import hashlib

DB_NAME = "finances.db"

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database and creates the transactions table if it doesn't exist."""
    conn = get_db_connection()
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
    conn.close()

def _calculate_hash(row, account_type):
    """Calculates a SHA-256 hash for a transaction row to prevent duplicates."""
    # Using a tuple of strings for consistent hashing
    base_string = (
        str(row.get('Date operation', '')),
        str(row.get('Libelle operation', '')),
        str(row.get('montant', '')),
        str(account_type)
    )
    return hashlib.sha256("".join(base_string).encode('utf-8')).hexdigest()

def insert_transactions(df, account_type):
    """
    Inserts a DataFrame of transactions into the database, avoiding duplicates.
    Assumes the DataFrame has been preprocessed.

    Args:
        df (pd.DataFrame): The preprocessed DataFrame containing transactions.
        account_type (str): The type of account ('Perso' or 'Commun').
    """
    if df.empty:
        return 0

    conn = get_db_connection()
    cursor = conn.cursor()

    df_insert = df.copy()

    # Add account_type and calculate hash (using original column names + montant)
    df_insert['account_type'] = account_type
    df_insert['hash'] = df_insert.apply(lambda row: _calculate_hash(row, account_type), axis=1)

    # Add 'type_budget' if it doesn't exist (it should from logic.py, but as a fallback)
    if 'type_budget' not in df_insert.columns:
        df_insert['type_budget'] = 'Ponctuel'

    # Convert datetime columns to strings for SQLite compatibility
    for col in ['Date de comptabilisation', 'Date operation', 'Date de valeur']:
        if col in df_insert.columns and pd.api.types.is_datetime64_any_dtype(df_insert[col]):
            df_insert[col] = df_insert[col].dt.strftime('%Y-%m-%d')

    # Rename columns for DB schema
    df_insert.rename(columns={
        'Date de comptabilisation': 'date_compte',
        'Libelle simplifie': 'libelle_simple',
        'Libelle operation': 'libelle_op',
        'Reference': 'reference',
        'Informations complementaires': 'info_complementaires',
        'Type operation': 'type_op',
        'Categorie': 'categorie',
        'Sous categorie': 'sous_categorie',
        'Debit': 'debit',
        'Credit': 'credit',
        'Date operation': 'date_op',
        'Date de valeur': 'date_valeur',
        'Pointage operation': 'pointage_op'
    }, inplace=True)

    # Convert to list of dicts for insertion
    records = df_insert.to_dict('records')
    
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
    
    cursor.executemany(insert_query, records)
    
    inserted_rows = cursor.rowcount
    conn.commit()
    conn.close()
    
    return inserted_rows

def get_all_transactions():
    """Fetches all transactions from the database and returns them as a DataFrame."""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM transactions", conn)
    conn.close()
    return df

def update_transaction_category(hash_id, category, sub_category):
    """Updates the category and sub-category of a specific transaction."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE transactions SET categorie = ?, sous_categorie = ? WHERE hash = ?",
        (category, sub_category, hash_id)
    )
    conn.commit()
    conn.close()

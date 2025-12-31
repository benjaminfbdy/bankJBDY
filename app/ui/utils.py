# app/ui/utils.py
import streamlit as st
import pandas as pd
from dataclasses import asdict

from app.core.config import DB_NAME, CATEGORIZATION_RULES
from app.repository.transaction_repository import TransactionRepository
from app.repository.category_repository import CategoryRepository

def ensure_data_loaded() -> pd.DataFrame:
    """
    Initializes repositories and loads transaction data into session state.
    Returns a DataFrame representation of the transactions.
    """
    if 'category_repo' not in st.session_state:
        st.session_state.category_repo = CategoryRepository(db_path=DB_NAME)
        st.session_state.category_repo.create_tables()
        st.session_state.category_repo.seed_data(CATEGORIZATION_RULES)

    if 'repo' not in st.session_state:
        st.session_state.repo = TransactionRepository(db_path=DB_NAME)
        st.session_state.repo.create_table()

    if 'transactions' not in st.session_state:
        st.session_state.transactions = st.session_state.repo.get_all()
    
    # Return a dataframe for display purposes
    return pd.DataFrame([asdict(t) for t in st.session_state.transactions])

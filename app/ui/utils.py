# app/ui/utils.py
import streamlit as st
import pandas as pd
from dataclasses import asdict

from app.core.config import DB_NAME
from app.repository.transaction_repository import TransactionRepository

def ensure_data_loaded() -> pd.DataFrame:
    """
    Initializes repository and loads transaction data into session state.
    Returns a DataFrame representation of the transactions.
    """
    if 'repo' not in st.session_state:
        st.session_state.repo = TransactionRepository(db_path=DB_NAME)
        # Create table on first run of the session
        st.session_state.repo.create_table()

    if 'transactions' not in st.session_state:
        st.session_state.transactions = st.session_state.repo.get_all()
    
    # Return a dataframe for display purposes
    return pd.DataFrame([asdict(t) for t in st.session_state.transactions])

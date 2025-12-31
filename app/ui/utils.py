# app/ui/utils.py
import streamlit as st
import pandas as pd
from dataclasses import asdict

from app.core.config import DB_NAME, CATEGORIZATION_RULES
from app.repository.transaction_repository import TransactionRepository
from app.repository.category_repository import CategoryRepository
from app.repository.budget_repository import BudgetRepository
from app.repository.goal_repository import GoalRepository
from app.repository.net_worth_repository import NetWorthRepository

def ensure_data_loaded() -> pd.DataFrame:
    """
    Initializes repositories and loads transaction data into session state.
    Returns a DataFrame representation of the transactions.
    """
    # Order is important: create category tables before seeding
    if 'category_repo' not in st.session_state:
        st.session_state.category_repo = CategoryRepository(db_path=DB_NAME)
        st.session_state.category_repo.create_tables()
        st.session_state.category_repo.seed_data(CATEGORIZATION_RULES)

    if 'budget_repo' not in st.session_state:
        st.session_state.budget_repo = BudgetRepository(db_path=DB_NAME)
        st.session_state.budget_repo.create_table()

    if 'goal_repo' not in st.session_state:
        st.session_state.goal_repo = GoalRepository(db_path=DB_NAME)
        st.session_state.goal_repo.create_table()

    if 'net_worth_repo' not in st.session_state:
        st.session_state.net_worth_repo = NetWorthRepository(db_path=DB_NAME)
        st.session_state.net_worth_repo.create_tables()

    if 'repo' not in st.session_state:
        st.session_state.repo = TransactionRepository(db_path=DB_NAME)
        st.session_state.repo.create_table()



    if 'transactions' not in st.session_state:
        st.session_state.transactions = st.session_state.repo.get_all()
    
    # Return a dataframe for display purposes
    return pd.DataFrame([asdict(t) for t in st.session_state.transactions])

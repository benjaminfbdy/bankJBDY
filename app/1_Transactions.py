# app/1_Transactions.py
import streamlit as st
import pandas as pd
from dataclasses import asdict
import io

from app.services.finance_service import FinanceService
from app.ui.utils import ensure_data_loaded
from app.ui.transaction_grid import display_transaction_grid

st.set_page_config(layout="wide", page_title="Gestion Financière")

def main():
    """Main function to run the Streamlit app."""
    st.title("💰 Suivi des Transactions")

    # --- Initialization and Data Loading ---
    transactions_df = ensure_data_loaded()
    repo = st.session_state.repo
    category_repo = st.session_state.category_repo
    service = FinanceService(category_repo=category_repo)

    # --- Sidebar for Uploads ---
    st.sidebar.header("📥 Importation de Données")
    uploaded_file = st.sidebar.file_uploader("Choisissez un fichier CSV", type="csv")
    account_type = st.sidebar.selectbox("Type de compte", ["Perso", "Commun"])

    if st.sidebar.button("🚀 Importer et Traiter"):
        if uploaded_file is not None:
            try:
                uploaded_file.seek(0)
                string_data = uploaded_file.getvalue().decode('latin1')
                string_io = io.StringIO(string_data)
                raw_df = pd.read_csv(string_io, sep=';')

                if raw_df.empty:
                    st.error("Le fichier CSV est vide ou illisible.")
                    st.stop()

                with st.spinner("Traitement des transactions..."):
                    new_transactions = service.process_transactions_from_df(raw_df, account_type)
                with st.spinner("Insertion dans la base de données..."):
                    repo.add_many(new_transactions)
                
                st.sidebar.success("Importation réussie !")
                del st.session_state.transactions # Force reload
                st.rerun()
            
            except pd.errors.EmptyDataError:
                st.error("Erreur: Le fichier est vide ou le séparateur n'est pas correct. Veuillez utiliser un point-virgule ';'.")
            except Exception as e:
                st.error(f"Erreur lors de l'import: {e}")
        else:
            st.sidebar.warning("Veuillez sélectionner un fichier CSV.")

    # --- Main Page Display ---
    if transactions_df.empty:
        st.info("Aucune transaction trouvée. Veuillez en importer une via la barre latérale.")
        return

    st.header("Filtres et Affichage")
    filter_account = st.radio(
        "Filtrer par compte",
        ["Tous", "Perso", "Commun"],
        horizontal=True,
        key="account_filter",
    )

    if filter_account != "Tous":
        display_df = transactions_df[transactions_df["account_type"] == filter_account].copy()
    else:
        display_df = transactions_df.copy()

    # --- Display the reusable grid component ---
    st.header("Transactions")
    display_transaction_grid(display_df, key="main_transactions_grid")

if __name__ == "__main__":
    main()
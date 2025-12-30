import streamlit as st
import pandas as pd
import database
import logic
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

st.set_page_config(layout="wide", page_title="Gestion Financière Personnelle")

def load_data():
    """Load all transactions from the database."""
    return database.get_all_transactions()

def main():
    """Main function to run the Streamlit app."""
    st.title("📊 Application de Gestion Financière")

    # --- Initialize Database and Session State ---
    database.init_db()
    if 'df' not in st.session_state:
        st.session_state.df = load_data()

    # --- Sidebar for Uploads ---
    st.sidebar.header("📥 Importation de Données")
    uploaded_file = st.sidebar.file_uploader(
        "Choisissez un fichier CSV", type="csv"
    )
    account_type = st.sidebar.selectbox(
        "Type de compte", ["Perso", "Commun"], key="account_type_selector"
    )

    if st.sidebar.button("🚀 Importer et Traiter"):
        if uploaded_file is not None:
            try:
                # Read CSV with correct separator and encoding
                new_df = pd.read_csv(uploaded_file, sep=';', encoding='latin1')
                
                with st.spinner("Prétraitement des données..."):
                    new_df = logic.preprocess_data(new_df)

                with st.spinner("Catégorisation automatique..."):
                    new_df = logic.categorize_transactions(new_df)
                
                with st.spinner("Détection des récurrences..."):
                    new_df = logic.detect_recurrences(new_df)

                with st.spinner("Insertion dans la base de données..."):
                    inserted_count = database.insert_transactions(new_df, account_type)
                
                st.sidebar.success(f"{inserted_count} nouvelle(s) transaction(s) importée(s) !")
                st.session_state.df = load_data() # Refresh data
                st.rerun()

            except Exception as e:
                st.sidebar.error(f"Erreur lors de l'import: {e}")
        else:
            st.sidebar.warning("Veuillez sélectionner un fichier CSV.")

    # --- Main Page Display ---
    st.header("Transactions")

    if st.session_state.df.empty:
        st.info("Aucune transaction trouvée. Veuillez en importer via la barre latérale.")
        return

    # --- Filtering and Account Selection ---
    st.subheader("Filtres et Affichage")
    
    filter_account = st.radio(
        "Filtrer par compte",
        ["Tous", "Perso", "Commun"],
        horizontal=True,
        key="account_filter",
    )
    if filter_account != "Tous":
        display_df = st.session_state.df[st.session_state.df["account_type"] == filter_account].copy()
    else:
        display_df = st.session_state.df.copy()

    # --- Metric for uncategorized transactions ---
    st.subheader("Qualité des Données")
    if not display_df.empty:
        uncategorized = display_df[display_df['categorie'].isnull() | (display_df['categorie'] == '')]
        uncategorized_percent = (len(uncategorized) / len(display_df)) * 100
        st.metric(
            label="% Opérations non catégorisées",
            value=f"{uncategorized_percent:.2f}%",
            delta=f"{len(uncategorized)} transactions",
            delta_color="inverse"
        )
        st.progress(1 - (uncategorized_percent / 100))
    else:
        st.info("Aucune transaction à analyser. Modifiez vos filtres ou importez un fichier.")

    # --- AgGrid Table Display ---
    st.subheader("Transactions (avec tri et filtres intégrés)")
    
    if display_df.empty:
        return

    gb = GridOptionsBuilder.from_dataframe(display_df)
    
    # Configure columns to be editable
    gb.configure_column("categorie", editable=True)
    gb.configure_column("sous_categorie", editable=True)
    
    # Hide the hash column from the UI
    gb.configure_column("hash", hide=True)

    # Enable sorting, filtering, and resizing on all columns
    gb.configure_default_column(
        resizable=True,
        sortable=True,
        filter=True,
        groupable=True,
    )
    
    grid_options = gb.build()

    grid_response = AgGrid(
        display_df,
        gridOptions=grid_options,
        data_return_mode=DataReturnMode.AS_INPUT,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        fit_columns_on_grid_load=False,
        allow_unsafe_jscode=True, # Set to True to allow jsfunction to be injected
        height=500,
        width='100%',
        reload_data=True,
        key='transactions_grid'
    )

    edited_df = grid_response['data']

    # --- Save Changes Logic for AgGrid ---
    # Create dictionaries from dataframes, indexed by hash, for easy comparison
    original_dict = display_df.set_index('hash').to_dict('index')
    edited_dict = edited_df.set_index('hash').to_dict('index')

    changes_detected = False
    for hash_id, edited_row in edited_dict.items():
        if hash_id in original_dict:
            original_row = original_dict[hash_id]
            if edited_row['categorie'] != original_row['categorie'] or \
               edited_row['sous_categorie'] != original_row['sous_categorie']:
                changes_detected = True
                break
    
    if changes_detected:
        st.info("Des modifications ont été détectées. Cliquez sur 'Sauvegarder' pour les appliquer.")
        if st.button("💾 Sauvegarder les modifications"):
            with st.spinner("Sauvegarde en cours..."):
                for hash_id, edited_row in edited_dict.items():
                    if hash_id in original_dict:
                        original_row = original_dict[hash_id]
                        if edited_row['categorie'] != original_row['categorie'] or \
                           edited_row['sous_categorie'] != original_row['sous_categorie']:
                            database.update_transaction_category(
                                hash_id,
                                edited_row['categorie'],
                                edited_row['sous_categorie']
                            )
            st.success("Modifications sauvegardées !")
            st.session_state.df = load_data()
            st.rerun()


if __name__ == "__main__":
    main()


# app/main.py
import streamlit as st
import pandas as pd
from dataclasses import asdict

from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode

from app.services.finance_service import FinanceService
from app.ui.utils import ensure_data_loaded

st.set_page_config(layout="wide", page_title="Gestion Financière Personnelle")

def main():
    """Main function to run the Streamlit app."""
    st.title("📊 Application de Gestion Financière (Clean Architecture)")

    # --- Initialization and Data Loading ---
    ensure_data_loaded()
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
                raw_df = pd.read_csv(uploaded_file, sep=';', encoding='latin1')
                
                with st.spinner("Traitement des transactions..."):
                    new_transactions = service.process_transactions_from_df(raw_df, account_type)
                
                with st.spinner("Insertion dans la base de données..."):
                    inserted_count = repo.add_many(new_transactions)
                
                st.sidebar.success(f"{inserted_count} nouvelle(s) transaction(s) importée(s) !")
                st.session_state.transactions = repo.get_all() # Refresh data
                st.rerun()

            except Exception as e:
                st.sidebar.error(f"Erreur lors de l'import: {e}")
        else:
            st.sidebar.warning("Veuillez sélectionner un fichier CSV.")

    # --- Main Page Display ---
    st.header("Transactions")
    
    transactions_df = pd.DataFrame([asdict(t) for t in st.session_state.transactions])

    if transactions_df.empty:
        st.info("Aucune transaction trouvée. Veuillez en importer via la barre latérale.")
        return

    st.subheader("Filtres et Affichage")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        filter_account = st.radio(
            "Filtrer par compte",
            ["Tous", "Perso", "Commun"],
            horizontal=True,
            key="account_filter",
        )
    
    # --- Column Selector ---
    all_columns = transactions_df.columns.tolist()
    if 'hash' in all_columns:
        all_columns.remove('hash') # Hide hash from selection

    if 'selected_columns' not in st.session_state:
        st.session_state.selected_columns = ['date_op', 'libelle_simple', 'montant', 'categorie', 'sous_categorie', 'type_budget']

    with st.expander("Gérer les colonnes visibles"):
         st.session_state.selected_columns = st.multiselect(
            "Choisir les colonnes à afficher",
            all_columns,
            default=st.session_state.selected_columns,
        )

    # --- Data Filtering ---
    if filter_account != "Tous":
        display_df = transactions_df[transactions_df["account_type"] == filter_account].copy()
    else:
        display_df = transactions_df.copy()

    # --- Metric for uncategorized transactions ---
    st.subheader("Qualité des Données")
    if not display_df.empty:
        uncategorized = display_df[display_df['categorie'].isnull() | (display_df['categorie'] == '')]
        percent_uncategorized = (len(uncategorized) / len(display_df)) * 100
        st.metric(label="% Opérations non catégorisées", value=f"{percent_uncategorized:.2f}%", delta=f"{len(uncategorized)} transactions", delta_color="inverse")
        st.progress(1 - (percent_uncategorized / 100))

    # --- AgGrid Table Display ---
    st.subheader("Transactions")
    if display_df.empty:
        st.warning("Aucune transaction à afficher avec les filtres actuels.")
        return

    # Ensure selected columns exist in the dataframe before displaying
    cols_to_display = [col for col in st.session_state.selected_columns if col in display_df.columns]
    grid_df = display_df[['hash'] + cols_to_display]

    gb = GridOptionsBuilder.from_dataframe(grid_df)
    
    # --- Dependent Dropdown Logic ---
    all_categories = category_repo.get_all_categories()
    sub_category_map = category_repo.get_all_sub_categories_as_map()

    cell_editor_selector_js = JsCode(f"""
        function(params) {{
            const category = params.data.categorie;
            const subCategoryMap = {sub_category_map};
            
            // Check if category exists and has a non-empty list of sub-categories
            if (category && subCategoryMap[category] && subCategoryMap[category].length > 0) {{
                return {{
                    component: 'agSelectCellEditor',
                    params: {{ values: subCategoryMap[category] }},
                    popup: true
                }};
            }} else {{
                // If no sub-categories, allow free text entry.
                return {{
                    component: 'agTextCellEditor',
                    popup: true
                }};
            }}
        }}
    """)
    
    gb.configure_column(
        "categorie", 
        editable=True,
        cellEditor='agSelectCellEditor',
        cellEditorParams={'values': all_categories}
    )
    
    gb.configure_column(
        "sous_categorie", 
        editable=True,
        cellEditorSelector=cell_editor_selector_js
    )

    gb.configure_column(
        "type_budget", 
        editable=True,
        cellEditor='agSelectCellEditor',
        cellEditorParams={'values': ['Ponctuel', 'Récurrente']}
    )

    gb.configure_column("hash", hide=True)
    gb.configure_default_column(resizable=True, sortable=True, filter=True)
    grid_options = gb.build()

    grid_response = AgGrid(
        grid_df,
        gridOptions=grid_options,
        data_return_mode=DataReturnMode.AS_INPUT,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        fit_columns_on_grid_load=False,
        height=500,
        width='100%',
        key='transactions_grid',
        allow_unsafe_jscode=True
    )

    edited_df = grid_response['data']
    original_dict = grid_df.set_index('hash').to_dict('index')
    edited_dict = edited_df.set_index('hash').to_dict('index')

    # --- Save Changes Logic ---
    changes_detected = any(
        original_dict.get(hash_id, {}).get(col) != edited_row.get(col)
        for hash_id, edited_row in edited_dict.items()
        for col in ['categorie', 'sous_categorie', 'type_budget']
    )

    if changes_detected:
        if st.button("💾 Sauvegarder les modifications"):
            with st.spinner("Sauvegarde en cours..."):
                for hash_id, edited_row in edited_dict.items():
                    original_row = original_dict.get(hash_id, {})
                    if original_row:
                        # Check and update category/sub-category
                        if original_row.get('categorie') != edited_row.get('categorie') or original_row.get('sous_categorie') != edited_row.get('sous_categorie'):
                            repo.update_category(hash_id, edited_row.get('categorie'), edited_row.get('sous_categorie'))
                        
                        # Check and update budget type
                        if original_row.get('type_budget') != edited_row.get('type_budget'):
                            repo.update_budget_type(hash_id, edited_row.get('type_budget'))
            
            st.success("Modifications sauvegardées !")
            # Force a full reload of data from DB
            del st.session_state.transactions
            st.rerun()

if __name__ == "__main__":
    main()
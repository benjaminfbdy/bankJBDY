# app/ui/transaction_grid.py
import streamlit as st
import pandas as pd

from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode

def display_transaction_grid(df: pd.DataFrame, key: str = "transactions_grid"):
    """
    Displays a DataFrame of transactions in a fully featured, editable AgGrid.

    This component includes:
    - Dynamic column selection (persisted in session state).
    - Dependent dropdowns for category/sub-category.
    - Editing for budget type.
    - Logic to save any edits back to the database.

    Args:
        df (pd.DataFrame): The DataFrame of transactions to display.
        key (str): A unique key for the AgGrid component.
    """
    if df.empty:
        st.info("Aucune transaction à afficher.")
        return

    # --- Get Repositories from Session State ---
    if 'repo' not in st.session_state or 'category_repo' not in st.session_state:
        st.error("Repositories not found in session state. Please reload the app.")
        return
    repo = st.session_state.repo
    category_repo = st.session_state.category_repo

    # --- Column Selector ---
    all_columns = df.columns.tolist()
    if 'hash' in all_columns:
        all_columns.remove('hash')

    # Initialize session state for selected columns if not present
    if 'selected_columns' not in st.session_state:
        st.session_state.selected_columns = ['date_op', 'libelle_simple', 'montant', 'categorie', 'sous_categorie', 'type_budget']

    with st.expander("Gérer les colonnes visibles"):
        st.session_state.selected_columns = st.multiselect(
            "Choisir les colonnes à afficher",
            all_columns,
            default=[col for col in st.session_state.selected_columns if col in all_columns],
            key=f"{key}_multiselect"
        )
    
    # Ensure selected columns exist and always include 'hash' for internal logic
    cols_to_display = [col for col in st.session_state.selected_columns if col in df.columns]
    grid_df = df[['hash'] + cols_to_display]

    # --- Grid Configuration ---
    gb = GridOptionsBuilder.from_dataframe(grid_df)
    
    all_categories = category_repo.get_all_categories()
    sub_category_map = category_repo.get_all_sub_categories_as_map()

    cell_editor_selector_js = JsCode(f"""
        function(params) {{
            const category = params.data.categorie;
            const subCategoryMap = {sub_category_map};
            if (category && subCategoryMap[category] && subCategoryMap[category].length > 0) {{
                return {{ component: 'agSelectCellEditor', params: {{ values: subCategoryMap[category] }}, popup: true }};
            }} else {{
                return {{ component: 'agTextCellEditor', popup: true }};
            }}
        }}
    """)
    
    gb.configure_column("categorie", editable=True, cellEditor='agSelectCellEditor', cellEditorParams={'values': all_categories})
    gb.configure_column("sous_categorie", editable=True, cellEditorSelector=cell_editor_selector_js)
    gb.configure_column("type_budget", editable=True, cellEditor='agSelectCellEditor', cellEditorParams={'values': ['Ponctuel', 'Récurrente']})
    gb.configure_column("hash", hide=True)
    gb.configure_default_column(resizable=True, sortable=True, filter=True)
    grid_options = gb.build()

    # --- Display Grid ---
    grid_response = AgGrid(
        grid_df,
        gridOptions=grid_options,
        data_return_mode=DataReturnMode.AS_INPUT,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        fit_columns_on_grid_load=False,
        height=500,
        width='100%',
        key=key,
        allow_unsafe_jscode=True
    )

    # --- Save Changes Logic ---
    edited_df = grid_response['data']
    original_dict = grid_df.set_index('hash').to_dict('index')
    edited_dict = edited_df.set_index('hash').to_dict('index')

    changes_detected = any(
        original_dict.get(hash_id, {}).get(col) != edited_row.get(col)
        for hash_id, edited_row in edited_dict.items()
        for col in ['categorie', 'sous_categorie', 'type_budget']
    )

    if changes_detected:
        if st.button(f"💾 Sauvegarder les modifications", key=f"{key}_save_button"):
            with st.spinner("Sauvegarde..."):
                for hash_id, edited_row in edited_dict.items():
                    original_row = original_dict.get(hash_id, {})
                    if original_row:
                        if original_row.get('categorie') != edited_row.get('categorie') or original_row.get('sous_categorie') != edited_row.get('sous_categorie'):
                            repo.update_category(hash_id, edited_row.get('categorie'), edited_row.get('sous_categorie'))
                        if original_row.get('type_budget') != edited_row.get('type_budget'):
                            repo.update_budget_type(hash_id, edited_row.get('type_budget'))
            
            st.success("Modifications sauvegardées !")
            if 'transactions' in st.session_state:
                del st.session_state.transactions
            st.rerun()
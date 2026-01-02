# app/pages/4_💰_Budget.py
import streamlit as st
import pandas as pd
from datetime import datetime

from app.ui.utils import ensure_data_loaded

st.set_page_config(
    page_title="Gestion du Budget",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Gestion du Budget Mensuel")

# --- Load data and repos ---
transactions_df = ensure_data_loaded()
category_repo = st.session_state.category_repo
budget_repo = st.session_state.budget_repo

# --- Date Selection ---
st.header("1. Sélectionner une période")
today = datetime.today()
col1, col2 = st.columns(2)
with col1:
    selected_year = st.selectbox("Année", options=range(today.year - 1, today.year + 2), index=1)
with col2:
    selected_month = st.selectbox("Mois", options=range(1, 13), index=today.month - 1, format_func=lambda m: datetime(2000, m, 1).strftime('%B'))

# --- Budget Management ---
st.header("2. Définir les budgets par catégorie")

all_categories = category_repo.get_all_categories()
category_id_map = category_repo.get_category_id_map()
# Flip the map for later use
id_category_map = {v: k for k, v in category_id_map.items()}

# Fetch existing budgets for the selected month
existing_budgets = budget_repo.get_budgets_for_month(selected_year, selected_month)

with st.form("budget_form"):
    budget_inputs = {}
    for cat_name in all_categories:
        cat_id = category_id_map.get(cat_name)
        if cat_id is not None:
            # Get existing budget amount if it exists, otherwise default to 0.0
            default_amount = existing_budgets.get(cat_id, 0.0)
            budget_inputs[cat_name] = st.number_input(
                f"Budget pour '{cat_name}'", 
                min_value=0.0, 
                value=default_amount,
                step=10.0,
                key=f"budget_{cat_id}"
            )

    submitted = st.form_submit_button("Sauvegarder les Budgets")
    if submitted:
        for cat_name, budget_amount in budget_inputs.items():
            cat_id = category_id_map.get(cat_name)
            if cat_id is not None:
                budget_repo.set_budget(cat_id, selected_year, selected_month, budget_amount)
        st.success(f"Budgets pour {selected_month}/{selected_year} sauvegardés !")
        # We might need a way to refresh the existing_budgets dict after save
        existing_budgets = budget_repo.get_budgets_for_month(selected_year, selected_month)

# --- Budget Tracking ---
st.header("3. Suivi du Budget vs. Dépenses Réelles")

# Filter transactions for the selected month and year
monthly_transactions = transactions_df[
    (pd.to_datetime(transactions_df['date_op']).dt.year == selected_year) &
    (pd.to_datetime(transactions_df['date_op']).dt.month == selected_month)
]

if monthly_transactions.empty:
    st.info("Aucune transaction pour la période sélectionnée.")
else:
    # Calculate actual spending per category
    expenses_df = monthly_transactions[monthly_transactions['montant'] < 0].copy()
    expenses_df['depenses'] = expenses_df['montant'].abs()
    actual_spending = expenses_df.groupby('categorie')['depenses'].sum().to_dict()

    # Prepare data for the tracking table
    tracking_data = []
    for cat_id, budget_amount in existing_budgets.items():
        if budget_amount > 0: # Only show categories with a set budget
            cat_name = id_category_map.get(cat_id, "Inconnue")
            actual = actual_spending.get(cat_name, 0.0)
            difference = budget_amount - actual
            percent_used = (actual / budget_amount) * 100 if budget_amount > 0 else 0
            
            tracking_data.append({
                "Catégorie": cat_name,
                "Budgété": budget_amount,
                "Dépensé": actual,
                "Restant": difference,
                "% Utilisé": min(percent_used, 100) # Cap at 100 for progress bar
            })

    if not tracking_data:
        st.warning("Aucun budget défini pour ce mois. Veuillez en définir dans la section 2.")
    else:
        tracking_df = pd.DataFrame(tracking_data)

        # Display the table with progress bars
        st.dataframe(
            tracking_df.style
                .format({
                    "Budgété": "{:,.2f} €",
                    "Dépensé": "{:,.2f} €",
                    "Restant": "{:,.2f} €",
                })
                .bar(subset=['% Utilisé'], color='#86B049', vmin=0, vmax=100),
            use_container_width=True
        )

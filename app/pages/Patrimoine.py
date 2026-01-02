# app/pages/6_🏛️_Patrimoine.py
import streamlit as st
import pandas as pd
import plotly.express as px
from dataclasses import asdict

from app.ui.utils import ensure_data_loaded

st.set_page_config(
    page_title="Patrimoine Net",
    page_icon="🏛️",
    layout="wide"
)

st.title("🏛️ Suivi du Patrimoine Net")

# --- Load data and repos ---
ensure_data_loaded()
net_worth_repo = st.session_state.net_worth_repo

# --- Load Assets and Liabilities ---
assets = net_worth_repo.get_all_assets()
liabilities = net_worth_repo.get_all_liabilities()

# Ensure DataFrame has columns even if empty, preventing the KeyError
assets_df = pd.DataFrame([asdict(a) for a in assets], columns=['id', 'name', 'value'])
liabilities_df = pd.DataFrame([asdict(l) for l in liabilities], columns=['id', 'name', 'value'])

# --- Calculate and Display KPIs ---
total_assets = assets_df['value'].sum() if not assets_df.empty else 0
total_liabilities = liabilities_df['value'].sum() if not liabilities_df.empty else 0
net_worth = total_assets - total_liabilities

st.header("Vue d'ensemble")
col1, col2, col3 = st.columns(3)
col1.metric("💰 Actifs Totaux", f"{total_assets:,.2f} €")
col2.metric("💸 Passifs Totaux", f"{total_liabilities:,.2f} €")
col3.metric("🏛️ Patrimoine Net Actuel", f"{net_worth:,.2f} €", delta=f"{net_worth:,.2f} €")

# --- Data Management UI ---
st.header("Gérer vos actifs et passifs")
st.info("Utilisez les tableaux ci-dessous pour lister tout ce que vous possédez (actifs) et tout ce que vous devez (passifs). Double-cliquez sur une cellule pour la modifier. Utilisez les boutons `+` et `-` en bas du tableau pour ajouter ou supprimer des lignes.", icon="💡")

col_assets, col_liabilities = st.columns(2)

column_config = {
    "id": None, # Hide the ID column
    "name": st.column_config.TextColumn("Nom", required=True),
    "value": st.column_config.NumberColumn(
        "Valeur (€)",
        required=True,
        min_value=0,
        format="%.2f €"
    )
}

with col_assets:
    st.subheader("Actifs")
    edited_assets_df = st.data_editor(
        assets_df,
        num_rows="dynamic",
        use_container_width=True,
        key="assets_editor",
        hide_index=True,
        column_config=column_config
    )

with col_liabilities:
    st.subheader("Passifs")
    edited_liabilities_df = st.data_editor(
        liabilities_df,
        num_rows="dynamic",
        use_container_width=True,
        key="liabilities_editor",
        hide_index=True,
        column_config=column_config
    )

# --- Smart Save Button ---
# Check if any changes have been made before showing the button
has_asset_changes = not assets_df.equals(edited_assets_df)
has_liability_changes = not liabilities_df.equals(edited_liabilities_df)

if has_asset_changes or has_liability_changes:
    if st.button("💾 Sauvegarder les modifications du patrimoine"):
        with st.spinner("Sauvegarde..."):
            net_worth_repo.sync_items('assets', edited_assets_df)
            net_worth_repo.sync_items('liabilities', edited_liabilities_df)
        st.success("Patrimoine mis à jour !")
        st.rerun()

st.markdown("---")

# --- Visualization ---
st.header("Composition du Patrimoine")

if not edited_assets_df.empty or not edited_liabilities_df.empty:
    assets_vis = edited_assets_df.copy().dropna(subset=['name'])
    assets_vis['type'] = 'Actif'
    liabilities_vis = edited_liabilities_df.copy().dropna(subset=['name'])
    liabilities_vis['type'] = 'Passif'

    combined_df = pd.concat([assets_vis, liabilities_vis])

    if not combined_df.empty:
        fig = px.bar(
            combined_df,
            x='value',
            y='type',
            color='name',
            orientation='h',
            title="Répartition des Actifs et des Passifs",
            labels={'value': 'Valeur (€)', 'type': ''}
        )
        fig.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Ajoutez des actifs et des passifs pour visualiser leur répartition.")
else:
    st.info("Ajoutez des actifs et des passifs pour visualiser leur répartition.")

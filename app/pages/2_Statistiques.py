# app/pages/2_📊_Statistiques.py
import streamlit as st
import pandas as pd
import plotly.express as px
from dataclasses import asdict
from datetime import date

from app.ui.utils import ensure_data_loaded

st.set_page_config(layout="wide", page_title="Statistiques Financières")

st.title("📊 Statistiques et Analyses")

transactions_df = ensure_data_loaded()

if transactions_df.empty:
    st.warning("Aucune transaction à analyser. Veuillez d'abord importer un fichier depuis la page d'accueil.")
    st.stop()

# --- Convert date columns ---
transactions_df['date_op'] = pd.to_datetime(transactions_df['date_op'])

# --- Filtering ---
st.header("Filtres")
col1, col2, col3 = st.columns(3)

with col1:
    account = st.selectbox(
        "Filtrer par compte",
        ["Tous", "Perso", "Commun"],
        key="stats_account_filter",
    )

today = date.today()
last_year = today.replace(year=today.year - 1)

with col2:
    start_date = st.date_input("Date de début", last_year, key="stats_start_date")
with col3:
    end_date = st.date_input("Date de fin", today, key="stats_end_date")

# Apply filters
if account != "Tous":
    filtered_df = transactions_df[transactions_df["account_type"] == account].copy()
else:
    filtered_df = transactions_df.copy()

filtered_df = filtered_df[(filtered_df['date_op'].dt.date >= start_date) & (filtered_df['date_op'].dt.date <= end_date)]

# --- Main Metrics ---
st.header("Vue d'ensemble de la période")

if filtered_df.empty:
    st.warning("Aucune donnée disponible pour la période et les filtres sélectionnés.")
else:
    total_income = filtered_df[filtered_df['montant'] > 0]['montant'].sum()
    total_expenses = filtered_df[filtered_df['montant'] < 0]['montant'].abs().sum()
    net_balance = total_income - total_expenses

    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Revenu Total", f"{total_income:,.2f} €")
    kpi2.metric("Dépenses Totales", f"{total_expenses:,.2f} €")
    kpi3.metric("Solde Net", f"{net_balance:,.2f} €", delta=f"{net_balance:,.2f} €")

    # --- Visualizations ---
    st.header("Visualisations")

    expenses_df = filtered_df[filtered_df['montant'] < 0].copy()
    expenses_df['depenses'] = expenses_df['montant'].abs()

    # Sunburst Chart for hierarchical data
    st.subheader("Répartition des Dépenses")
    
    # Data prep for sunburst
    sunburst_df = expenses_df.groupby(['categorie', 'sous_categorie']).sum(numeric_only=True).reset_index()

    if not sunburst_df.empty:
        fig_sunburst = px.sunburst(
            sunburst_df,
            path=['categorie', 'sous_categorie'],
            values='depenses',
            title="Cliquez sur une catégorie pour explorer les sous-catégories",
            maxdepth=2
        )
        fig_sunburst.update_traces(textinfo='label+percent parent')
        st.plotly_chart(fig_sunburst, use_container_width=True)
    else:
        st.info("Aucune dépense à visualiser pour la période sélectionnée.")


    # Income vs Expenses over time
    st.subheader("Évolution Temporelle")
    monthly_summary = filtered_df.set_index('date_op').resample('M').agg(
        revenus=('montant', lambda x: x[x > 0].sum()),
        depenses=('montant', lambda x: abs(x[x < 0].sum()))
    ).reset_index()
    monthly_summary['date_op'] = monthly_summary['date_op'].dt.strftime('%Y-%m')

    fig_monthly = px.bar(
        monthly_summary,
        x='date_op',
        y=['revenus', 'depenses'],
        title="Évolution Mensuelle des Revenus et Dépenses",
        barmode='group',
        labels={'value': 'Montant (€)', 'date_op': 'Mois'}
    )
    st.plotly_chart(fig_monthly, use_container_width=True)

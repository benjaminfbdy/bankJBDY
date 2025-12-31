# app/pages/7_💡_Insights.py
import streamlit as st
import pandas as pd
from datetime import date, datetime

from app.ui.utils import ensure_data_loaded
from app.services.insights_service import InsightsService
from app.ui.transaction_grid import display_transaction_grid

st.set_page_config(layout="wide", page_title="Insights Financiers")

st.title("💡 Insights & Analyses Automatiques")

def format_date(t):
    """Safely format date/datetime objects, returning empty string for others."""
    if isinstance(t, (datetime, date)):
        return t.strftime('%d/%m/%Y')
    return ''

# --- Load data and instantiate service ---
transactions_df = ensure_data_loaded()
insights_service = InsightsService()

if transactions_df.empty:
    st.warning("Aucune transaction à analyser. Veuillez d'abord importer un fichier.")
    st.stop()

# --- Run Analyses ---
subscriptions = insights_service.find_recurring_subscriptions(transactions_df)
large_purchases = insights_service.find_large_purchases(transactions_df)
bank_fees = insights_service.find_bank_fees(transactions_df)


# --- Display Insights ---

# 1. Subscriptions Card
st.header("Abonnements Récurrents Détectés")
if not subscriptions.empty:
    st.dataframe(
        subscriptions.style.format({
            "montant_moyen": "{:,.2f} €",
            "derniere_date": format_date
        }),
        use_container_width=True
    )
else:
    st.info("Aucun abonnement mensuel récurrent n'a été détecté automatiquement.")

st.markdown("---")

# 2. Large Purchases Card
st.header("Dépenses Inhabituellement Élevées")
if not large_purchases.empty:
    st.warning("Les dépenses suivantes sont significativement plus élevées que la moyenne de leur catégorie.", icon="⚠️")
    with st.expander("Afficher et modifier les transactions concernées"):
        # We need to pass the original transactions that were flagged, not the summary
        flagged_hashes = large_purchases['hash'].tolist()
        display_df = transactions_df[transactions_df['hash'].isin(flagged_hashes)]
        display_transaction_grid(display_df, key="large_purchases_grid")
else:
    st.info("Aucune dépense anormalement élevée détectée. Bravo pour votre régularité !")

st.markdown("---")

# 3. Bank Fees Card
st.header("Frais Bancaires")
if not bank_fees.empty:
    total_fees = bank_fees['montant'].abs().sum()
    st.metric("Total des frais bancaires sur la période", f"{total_fees:,.2f} €")
    with st.expander("Afficher et modifier les transactions de frais"):
        display_transaction_grid(bank_fees, key="bank_fees_grid")
else:
    st.info("Aucun frais bancaire détecté dans vos transactions. Excellent !")

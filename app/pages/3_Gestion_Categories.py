# app/pages/3_Gestion_Categories.py
import streamlit as st
from app.ui.utils import ensure_data_loaded

st.set_page_config(layout="wide", page_title="Gestion des Catégories")

st.title("⚙️ Gestion des Catégories et des Règles")

# Ensure repos are loaded and seeded
ensure_data_loaded()
category_repo = st.session_state.category_repo

# --- Add New Category ---
st.header("1. Créer une nouvelle catégorie")
with st.form("new_category_form", clear_on_submit=True):
    new_category_name = st.text_input("Nom de la nouvelle catégorie")
    submitted = st.form_submit_button("Ajouter la Catégorie")
    if submitted and new_category_name:
        if category_repo.add_category(new_category_name):
            st.success(f"La catégorie '{new_category_name}' a été ajoutée avec succès !")
        else:
            st.error(f"La catégorie '{new_category_name}' existe déjà.")

# --- Manage Rules for Existing Categories ---
st.header("2. Gérer les règles d'automatisation")

all_categories = category_repo.get_all_categories()

if not all_categories:
    st.warning("Aucune catégorie n'a été créée. Veuillez en ajouter une ci-dessus.")
else:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Ajouter une règle")
        with st.form("new_rule_form", clear_on_submit=True):
            selected_category = st.selectbox("Choisir une catégorie", all_categories)
            new_keyword = st.text_input("Nouveau mot-clé à associer (ex: 'AMAZON')")
            
            rule_submitted = st.form_submit_button("Ajouter la Règle")
            if rule_submitted and selected_category and new_keyword:
                if category_repo.add_rule(selected_category, new_keyword):
                    st.success(f"Le mot-clé '{new_keyword}' a été ajouté à la catégorie '{selected_category}'.")
                else:
                    st.error(f"Le mot-clé '{new_keyword}' existe déjà ou la catégorie est invalide.")
    
    with col2:
        st.subheader("Voir les règles existantes")
        rules = category_repo.get_rules()
        if not rules:
            st.info("Aucune règle d'automatisation n'a encore été créée.")
        else:
            with st.expander("Afficher toutes les règles", expanded=False):
                st.json(rules)

st.markdown("---")

# --- Manage Sub-Categories ---
st.header("3. Gérer les sous-catégories")
with st.form("new_sub_category_form", clear_on_submit=True):
    parent_category = st.selectbox("Choisir une catégorie parente", all_categories)
    new_sub_category_name = st.text_input("Nom de la nouvelle sous-catégorie")
    sub_submitted = st.form_submit_button("Ajouter la Sous-Catégorie")
    if sub_submitted and parent_category and new_sub_category_name:
        if category_repo.add_sub_category(new_sub_category_name, parent_category):
            st.success(f"La sous-catégorie '{new_sub_category_name}' a été ajoutée à '{parent_category}'.")
        else:
            st.error("Cette sous-catégorie existe déjà pour cette catégorie parente.")

with st.expander("Voir l'arborescence des catégories et sous-catégories"):
    st.json(category_repo.get_all_sub_categories_as_map())


st.markdown("---")

# --- Re-categorize all existing transactions ---
st.header("4. Mettre à jour les transactions existantes")
st.warning("Cette action va appliquer l'ensemble de vos règles à tout votre historique. L'ancienne catégorie sera écrasée si une nouvelle règle s'applique.", icon="⚠️")

if st.button("🚀 Appliquer les règles à toutes les transactions"):
    with st.spinner("Re-catégorisation de toutes les transactions en cours..."):
        # We need to instantiate the service here
        from app.services.finance_service import FinanceService
        
        repo = st.session_state.repo
        category_repo = st.session_state.category_repo
        service = FinanceService(category_repo=category_repo)

        transactions_to_update = service.recategorize_all(st.session_state.transactions)
        
        if not transactions_to_update:
            st.success("Aucune mise à jour de catégorie nécessaire. Tout est déjà à jour !")
        else:
            for transaction_hash, new_category in transactions_to_update:
                # When re-categorizing, we reset the sub-category
                repo.update_category(transaction_hash, new_category, '')
            
            # Clear the session state to force a reload on all pages
            del st.session_state.transactions
            st.success(f"{len(transactions_to_update)} transactions ont été mises à jour avec succès !")
            st.info("Les changements seront visibles au prochain rechargement des pages 'Transactions' ou 'Statistiques'.")

st.info("Les nouvelles règles de catégorisation seront appliquées automatiquement lors du prochain import de fichier CSV.", icon="ℹ️")

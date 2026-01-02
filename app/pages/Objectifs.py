# app/pages/5_🎯_Objectifs.py
import streamlit as st
from app.ui.utils import ensure_data_loaded

st.set_page_config(
    page_title="Objectifs d'Épargne",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 Objectifs d'Épargne")

# --- Load data and repos ---
ensure_data_loaded()
goal_repo = st.session_state.goal_repo

# --- Create a new goal ---
st.header("1. Créer un nouvel objectif")
with st.form("new_goal_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        goal_name = st.text_input("Nom de l'objectif (ex: 'Fonds d'urgence')")
    with col2:
        target_amount = st.number_input("Montant cible (€)", min_value=0.01, step=100.0)
    
    submitted = st.form_submit_button("Créer l'Objectif")
    if submitted and goal_name and target_amount:
        if goal_repo.add_goal(goal_name, target_amount):
            st.success(f"Objectif '{goal_name}' créé !")
            # No need to manually refresh, Streamlit's execution flow handles it
        else:
            st.error(f"Un objectif nommé '{goal_name}' existe déjà.")

st.markdown("---")

# --- Display existing goals ---
st.header("2. Suivi des objectifs")
all_goals = goal_repo.get_all_goals()

if not all_goals:
    st.info("Vous n'avez pas encore créé d'objectif. Utilisez le formulaire ci-dessus pour commencer.")
else:
    # Create a grid of cards for the goals
    cols = st.columns(3)
    for i, goal in enumerate(all_goals):
        with cols[i % 3]:
            with st.container():
                st.subheader(goal.name)
                
                # Progress calculation
                progress = (goal.current_amount / goal.target_amount) if goal.target_amount > 0 else 0
                st.progress(min(progress, 1.0))
                st.metric(
                    label="Progression",
                    value=f"{goal.current_amount:,.2f} €",
                    delta=f"/ {goal.target_amount:,.2f} €"
                )

                # Form to add funds
                with st.form(f"add_funds_form_{goal.id}", clear_on_submit=True):
                    amount_to_add = st.number_input("Ajouter des fonds", min_value=0.01, step=10.0, key=f"add_fund_{goal.id}")
                    if st.form_submit_button("Contribuer"):
                        goal_repo.update_goal_progress(goal.id, amount_to_add)
                        st.success(f"{amount_to_add:,.2f} € ajoutés à l'objectif '{goal.name}' !")
                        st.rerun() # Rerun to update the progress bars immediately

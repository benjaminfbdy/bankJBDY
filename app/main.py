# app/main.py
import streamlit as st

st.set_page_config(
    page_title="Accueil - Gestion Financière",
    page_icon="🏠",
    layout="wide"
)

st.title("Bienvenue sur votre Application de Gestion Financière")

st.header("Comment utiliser cette application :")
st.markdown("""
1.  **Importer des Données** : Utilisez la barre latérale pour téléverser vos fichiers CSV de transactions.
2.  **Transactions** : Naviguez vers la page `💰 Transactions` pour voir, filtrer et modifier votre historique.
3.  **Statistiques** : Explorez la page `📊 Statistiques` pour visualiser la répartition de vos dépenses et l'évolution de vos finances.
4.  **Gestion des Catégories** : Personnalisez vos catégories et les règles d'automatisation sur la page `⚙️ Gestion Catégories`.
5.  **Budget** : Définissez et suivez vos budgets mensuels sur la page `💰 Budget`.
6.  **Objectifs** : Créez et suivez vos objectifs d'épargne sur la page `🎯 Objectifs`.
7.  **Patrimoine** : Suivez votre patrimoine net en listant vos actifs et passifs sur la page `🏛️ Patrimoine`.
8.  **Insights** : Laissez l'application analyser vos données pour vous sur la page `💡 Insights`.
""")

st.info("Utilisez le menu de navigation dans la barre latérale à gauche pour accéder à toutes les fonctionnalités.")

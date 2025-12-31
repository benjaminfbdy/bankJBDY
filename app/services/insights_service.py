# app/services/insights_service.py
import pandas as pd
from typing import List, Dict, Any

class InsightsService:
    """
    Provides methods to analyze transaction data and find actionable insights.
    """

    def find_recurring_subscriptions(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Identifies recurring monthly expenses that look like subscriptions.

        Args:
            df (pd.DataFrame): The DataFrame of all transactions.

        Returns:
            pd.DataFrame: A summary DataFrame of detected subscriptions.
        """
        if df.empty:
            return pd.DataFrame()

        # We consider expenses that are marked as 'Récurrente'
        recurrent_expenses = df[(df['type_budget'] == 'Récurrente') & (df['montant'] < 0)].copy()

        if recurrent_expenses.empty:
            return pd.DataFrame()

        # Group them and calculate average cost
        subscription_summary = recurrent_expenses.groupby('libelle_simple').agg(
            montant_moyen=('montant', 'mean'),
            nombre_de_paiements=('montant', 'count'),
            derniere_date=('date_op', 'max')
        ).reset_index()

        subscription_summary['montant_moyen'] = subscription_summary['montant_moyen'].abs()
        
        return subscription_summary.sort_values('montant_moyen', ascending=False)

    def find_large_purchases(self, df: pd.DataFrame, std_dev_threshold: float = 2.0) -> pd.DataFrame:
        """
        Finds expenses that are significantly larger than the average for their category.

        Args:
            df (pd.DataFrame): The DataFrame of all transactions.
            std_dev_threshold (float): The number of standard deviations above the mean
                                       to consider a purchase as 'large'.

        Returns:
            pd.DataFrame: A DataFrame of transactions flagged as large purchases.
        """
        if df.empty:
            return pd.DataFrame()

        expenses_df = df[df['montant'] < 0].copy()
        expenses_df['depense'] = expenses_df['montant'].abs()

        if expenses_df.empty:
            return pd.DataFrame()

        # Calculate mean and std deviation for each category
        category_stats = expenses_df.groupby('categorie')['depense'].agg(['mean', 'std']).reset_index()
        category_stats.fillna(0, inplace=True) # Fill std for categories with 1 transaction

        # Merge stats back into the expenses df
        expenses_with_stats = pd.merge(expenses_df, category_stats, on='categorie')

        # Identify large purchases
        # A purchase is large if it's > mean + (threshold * std)
        # We also add a condition to avoid flagging small amounts (e.g. > 20€)
        is_large = expenses_with_stats['depense'] > (expenses_with_stats['mean'] + (std_dev_threshold * expenses_with_stats['std']))
        is_significant = expenses_with_stats['depense'] > 20 

        large_purchases_df = expenses_with_stats[is_large & is_significant]

        return large_purchases_df[['hash', 'date_op', 'libelle_simple', 'categorie', 'depense', 'mean']]

    def find_bank_fees(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Isolates all transactions categorized as 'Frais Bancaires'.
        
        Returns:
            pd.DataFrame: A DataFrame containing only bank fee transactions.
        """
        if df.empty or 'categorie' not in df.columns:
            return pd.DataFrame()
            
        bank_fees_df = df[df['categorie'].str.contains('Frais Bancaires', na=False)].copy()
        
        return bank_fees_df[['hash', 'date_op', 'libelle_simple', 'montant']]

# app/services/finance_service.py
import hashlib
import pandas as pd
from typing import List, Tuple
from dataclasses import asdict

from app.core.models import Transaction
from app.repository.category_repository import CategoryRepository

class FinanceService:
    """
    Handles all business logic for financial data processing.
    """
    def __init__(self, category_repo: CategoryRepository):
        self.category_repo = category_repo

    def _calculate_hash(self, row: pd.Series, account_type: str) -> str:
        """Calculates a SHA-256 hash for a transaction row to prevent duplicates."""
        base_string = (
            str(row.get('date_operation', '')),
            str(row.get('libelle_operation', '')),
            str(row.get('montant', '')),
            str(account_type)
        )
        return hashlib.sha256("".join(base_string).encode('utf-8')).hexdigest()

    def _preprocess_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Preprocesses the raw DataFrame from a CSV file."""
        df_processed = df.copy()
        
        # Standardize column names for processing
        df_processed.columns = [col.replace(' ', '_').lower() for col in df_processed.columns]

        # Handle Debit/Credit columns
        if 'debit' in df_processed.columns:
            debit_col = df_processed['debit'].astype(str).str.replace(',', '.', regex=False)
            df_processed['debit'] = pd.to_numeric(debit_col, errors='coerce').fillna(0)
        else:
            df_processed['debit'] = 0

        if 'credit' in df_processed.columns:
            credit_col = df_processed['credit'].astype(str).str.replace(',', '.', regex=False).str.replace('+', '', regex=False)
            df_processed['credit'] = pd.to_numeric(credit_col, errors='coerce').fillna(0)
        else:
            df_processed['credit'] = 0

        df_processed['montant'] = df_processed['credit'] + df_processed['debit']
        
        # Handle date columns
        for date_col in ['date_operation', 'date_de_comptabilisation', 'date_de_valeur']:
            if date_col in df_processed.columns:
                df_processed[date_col] = pd.to_datetime(df_processed[date_col], format='%d/%m/%Y', errors='coerce')

        return df_processed

    def _categorize_transactions(self, df: pd.DataFrame, force: bool = False) -> pd.DataFrame:
        """
        Automatically categorizes transactions based on dynamic rules from the database.

        Args:
            df (pd.DataFrame): The DataFrame to categorize.
            force (bool): If True, re-categorize all transactions, overwriting existing categories.
                          If False, only categorize transactions with an empty category.
        """
        rules = self.category_repo.get_rules()
        
        if 'categorie' not in df.columns:
            df['categorie'] = ''
        df['categorie'] = df['categorie'].fillna('')

        # Determine which rows to apply categorization to.
        if force:
            # On force mode, all rows are candidates.
            categorization_mask = pd.Series(True, index=df.index)
        else:
            # By default, only apply rules where category is not already set.
            categorization_mask = (df['categorie'] == '')

        for category, keywords in rules.items():
            for keyword in keywords:
                keyword_mask = df['libelle_operation'].str.contains(keyword, case=False, na=False)
                # Apply rules only to rows that are marked as candidates
                df.loc[categorization_mask & keyword_mask, 'categorie'] = category
        return df

    def _detect_recurrences(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detects recurrent transactions."""
        df['type_budget'] = 'Ponctuel'
        if 'date_operation' not in df.columns or 'libelle_simplifie' not in df.columns:
            return df
        
        df.sort_values('date_operation', inplace=True)
        grouped = df.groupby('libelle_simplifie')

        for _, group in grouped:
            if len(group) < 3:
                continue

            mean_amount = group['montant'].mean()
            if mean_amount == 0: continue
            
            amount_variation = (group['montant'] - mean_amount).abs() / abs(mean_amount)
            if not (amount_variation <= 0.05).all():
                continue

            time_diffs = group['date_operation'].diff().dt.days.dropna()
            is_monthly = all(28 <= diff <= 32 for diff in time_diffs)

            if is_monthly:
                df.loc[group.index, 'type_budget'] = 'Récurrente'
        return df

    def recategorize_all(self, all_transactions: List[Transaction]) -> List[Tuple[str, str]]:
        """
        Compares all transactions against the current rules and finds which ones need updating.
        
        Args:
            all_transactions (List[Transaction]): The full list of transactions to process.

        Returns:
            List[Tuple[str, str]]: A list of tuples, where each is (hash, new_category)
                                    for transactions whose category should change.
        """
        if not all_transactions:
            return []

        df = pd.DataFrame([asdict(t) for t in all_transactions])
        # The service layer uses standardized names internally
        df.rename(columns={'libelle_op': 'libelle_operation'}, inplace=True)

        old_categories = df.set_index('hash')['categorie']

        # This method returns a dataframe with a 'categorie' column
        df = self._categorize_transactions(df, force=True)
        new_categories = df.set_index('hash')['categorie']

        # Compare the two series to find differences
        changed = new_categories[new_categories != old_categories]

        if changed.empty:
            return []
        
        # Return a list of (hash, new_category) tuples
        return list(changed.to_dict().items())

    def process_transactions_from_df(self, df: pd.DataFrame, account_type: str) -> List[Transaction]:
        """
        Takes a raw DataFrame from a CSV, processes it fully, and returns a list of Transaction objects.
        """
        processed_df = self._preprocess_dataframe(df)
        categorized_df = self._categorize_transactions(processed_df)
        final_df = self._detect_recurrences(categorized_df)

        # Add hash after all processing is done
        final_df['hash'] = final_df.apply(lambda row: self._calculate_hash(row, account_type), axis=1)
        final_df['account_type'] = account_type

        # Rename columns to match dataclass fields before converting
        final_df.rename(columns={
            'date_de_comptabilisation': 'date_compte',
            'libelle_simplifie': 'libelle_simple',
            'libelle_operation': 'libelle_op',
            'informations_complementaires': 'info_complementaires',
            'type_operation': 'type_op',
            'sous_categorie': 'sous_categorie',
            'date_operation': 'date_op',
            'date_de_valeur': 'date_valeur',
            'pointage_operation': 'pointage_op'
        }, inplace=True)

        # Convert DataFrame to list of Transaction objects
        transactions: List[Transaction] = []
        for _, row in final_df.iterrows():
            # Filter row to only include keys that are in the Transaction dataclass
            transaction_data = {k: v for k, v in row.items() if k in Transaction.__annotations__}
            # Handle NaT dates from coercion
            for date_key in ['date_compte', 'date_op', 'date_valeur']:
                if date_key in transaction_data and pd.isna(transaction_data[date_key]):
                    transaction_data[date_key] = None
            
            transactions.append(Transaction(**transaction_data))
            
        return transactions


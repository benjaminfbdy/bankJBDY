# app/services/finance_service.py
import hashlib
import pandas as pd
from typing import List

from app.core.config import CATEGORIZATION_RULES, UNCATEGORIZED_KEYWORDS
from app.core.models import Transaction

class FinanceService:
    """
    Handles all business logic for financial data processing.
    """

    def _calculate_hash(self, row: pd.Series, account_type: str) -> str:
        """Calculates a SHA-256 hash for a transaction row to prevent duplicates."""
        base_string = (
            str(row.get('Date operation', '')),
            str(row.get('Libelle operation', '')),
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

    def _categorize_transactions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Automatically categorizes transactions based on keywords."""
        if 'categorie' not in df.columns:
            df['categorie'] = ''
        
        # Fill NaN to work with string operations
        df['categorie'] = df['categorie'].fillna('')

        # Identify rows that need categorization
        uncategorized_mask = (df['categorie'] == '') | \
                             (df['categorie'].str.contains('|'.join(UNCATEGORIZED_KEYWORDS), case=False, na=False))

        for category, keywords in CATEGORIZATION_RULES.items():
            for keyword in keywords:
                # Apply rules only to rows that are marked as uncategorized
                keyword_mask = df['libelle_operation'].str.contains(keyword, case=False, na=False)
                df.loc[uncategorized_mask & keyword_mask, 'categorie'] = category
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


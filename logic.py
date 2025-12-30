import pandas as pd
import numpy as np

# Heuristics for categorization
CATEGORIZATION_RULES = {
    'Salaire': ['VIREMENT SALAIRE', 'SALAIRE'],
    'Loyer': ['LOYER'],
    'Courses': ['CARREFOUR', 'AUCHAN', 'LIDL', 'SUPER U', 'INTERMARCHE', 'MONOPRIX'],
    'Transport': ['SNCF', 'RATP', 'ESSENCE', 'TOTAL', 'SHELL'],
    'Factures': ['EDF', 'ENGIE', 'FREE', 'ORANGE', 'BOUYGUES', 'SFR', 'VEOLIA'],
    'Santé': ['PHARMACIE', 'DOCTEUR', 'MUTUELLE'],
    'Loisirs': ['CINEMA', 'NETFLIX', 'SPOTIFY', 'RESTAURANT'],
    'Shopping': ['AMAZON', 'FNAC', 'ZALANDO', 'H&M'],
    'Retrait': ['RETRAIT DAB'],
}

def preprocess_data(df):
    """
    Preprocesses the raw DataFrame from CSV.
    - Handles Debit/Credit columns: converts to numeric, handles commas, and '+' signs.
    - Creates 'montant' column.
    """
    df_processed = df.copy()
    
    # Handle Debit
    if 'Debit' in df_processed.columns:
        debit_col = df_processed['Debit'].astype(str).str.replace(',', '.', regex=False)
        df_processed['Debit'] = pd.to_numeric(debit_col, errors='coerce').fillna(0)
    else:
        df_processed['Debit'] = 0

    # Handle Credit
    if 'Credit' in df_processed.columns:
        credit_col = df_processed['Credit'].astype(str).str.replace(',', '.', regex=False).str.replace('+', '', regex=False)
        df_processed['Credit'] = pd.to_numeric(credit_col, errors='coerce').fillna(0)
    else:
        df_processed['Credit'] = 0

    df_processed['montant'] = df_processed['Credit'] - df_processed['Debit']
    
    return df_processed

def categorize_transactions(df):
    """
    Automatically categorizes transactions based on keywords in 'Libelle operation'.
    It only fills the category if it's currently empty or NaN.
    """
    df['Categorie'] = df.get('Categorie', pd.Series(index=df.index, dtype=str))

    for category, keywords in CATEGORIZATION_RULES.items():
        for keyword in keywords:
            # Apply category only where 'Categorie' is not already set
            mask = (df['Libelle operation'].str.contains(keyword, case=False, na=False)) & (df['Categorie'].isnull() | df['Categorie'] == '')
            df.loc[mask, 'Categorie'] = category
            
    return df

def detect_recurrences(df):
    """
    Detects recurrent transactions and marks them in a 'Type Budget' column.
    
    A transaction is considered recurrent if it appears at least 3 times with:
    - The same 'Libelle simplifie'.
    - A similar amount (+/- 5% of the mean).
    - A regular interval (monthly, checked as 28-32 days).
    """
    if 'Date operation' not in df.columns or 'Libelle simplifie' not in df.columns:
        df['Type Budget'] = 'Ponctuel'
        return df

    # Ensure date column is in the right format
    df['Date operation'] = pd.to_datetime(df['Date operation'], errors='coerce')
    df.sort_values('Date operation', inplace=True)

    df['Type Budget'] = 'Ponctuel' # Default value
    
    grouped = df.groupby('Libelle simplifie')

    for name, group in grouped:
        if len(group) < 3:
            continue

        # Check amount consistency
        mean_amount = group['montant'].mean()
        if mean_amount == 0: continue # Avoid division by zero
        
        # Check if all amounts are within the tolerance
        amount_variation = (group['montant'] - mean_amount).abs() / abs(mean_amount)
        if not (amount_variation <= 0.05).all():
            continue

        # Check for regular intervals (monthly)
        time_diffs = group['Date operation'].diff().dt.days.dropna()
        
        # Check if all intervals are within a monthly range (28-32 days)
        is_monthly = all(28 <= diff <= 32 for diff in time_diffs)

        if is_monthly:
            # Mark these transactions as 'Récurrente'
            df.loc[group.index, 'Type Budget'] = 'Récurrente'

    return df

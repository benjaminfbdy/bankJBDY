# app/core/models.py
from dataclasses import dataclass, field
from typing import Optional
from datetime import date

@dataclass
class Transaction:
    """Represents a single financial transaction."""
    hash: str
    account_type: str
    montant: float
    date_op: date
    libelle_op: str
    
    # Optional fields
    date_compte: Optional[date] = None
    libelle_simple: Optional[str] = None
    reference: Optional[str] = None
    info_complementaires: Optional[str] = None
    type_op: Optional[str] = None
    categorie: Optional[str] = None
    sous_categorie: Optional[str] = None
    debit: Optional[float] = None
    credit: Optional[float] = None
    date_valeur: Optional[date] = None
    pointage_op: Optional[int] = 0
    type_budget: str = field(default='Ponctuel')

@dataclass
class Goal:
    """Represents a financial savings goal."""
    id: int
    name: str
    target_amount: float
    current_amount: float

# app/core/config.py

DB_NAME = "finances.db"

CATEGORIZATION_RULES = {
    'Salaire': ['VIREMENT SALAIRE', 'SALAIRE'],
    'Loyer': ['LOYER'],
    'Courses': ['CARREFOUR', 'AUCHAN', 'LIDL', 'SUPER U', 'INTERMARCHE', 'MONOPRIX', 'GRAND FRAIS', 'E.LECLERC'],
    'Transport': ['SNCF', 'RATP', 'ESSENCE', 'TOTAL', 'SHELL', 'PARKING'],
    'Factures': ['EDF', 'ENGIE', 'FREE', 'ORANGE', 'BOUYGUES', 'SFR', 'VEOLIA', 'SYNELVA'],
    'Santé': ['PHARMACIE', 'DOCTEUR', 'MUTUELLE', 'BPCE MUTUELLE'],
    'Loisirs': ['CINEMA', 'NETFLIX', 'SPOTIFY', 'RESTAURANT', 'ZOO', 'CITE DE LA VOILE'],
    'Shopping': ['AMAZON', 'FNAC', 'ZALANDO', 'H&M', 'KIABI', 'Vinted', 'LA HALLE'],
    'Retrait': ['RETRAIT DAB', 'RETRAIT D\'ESPECES'],
    'Maison': ['LEROY MERLIN', 'BUT', 'CONFORAMA', 'JARDILAND', 'ACTION', 'IKEA'],
    'Frais Bancaires': ['COTISATIONS BANCAIRES', 'FRAIS BANCAIRES'],
}


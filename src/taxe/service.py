

import sqlite3
from typing import List
from unittest import result
from ..taxe.model import AppliedTaxInput, AppliedTaxResponse, TaxeResponse
from database.sync_data import get_db_file

def get_regime_taxe(customer_code: str) -> TaxeResponse:
    """Fetch tax regime from the database."""
    # Simulated database fetch
    db_path = ""
    db_path = get_db_file()
    sqlite_conn = sqlite3.connect(db_path) # type: ignore
    cursor = sqlite_conn.cursor() 
    cursor.execute("""
        SELECT
            VACBPR_0
        FROM
            BPCUSTOMER
        WHERE
            BPCNUM_0 = ?
                   """, (customer_code,))
    code = cursor.fetchone()[0]
    cursor.close()
    sqlite_conn.close()
    return TaxeResponse(code=code)

def get_niveau_taxe_article(item_code: str) -> str:
    """Fetch tax level from the database."""
    # Simulated database fetch
    db_path = ""
    db_path = get_db_file()
    sqlite3_conn = sqlite3.connect(db_path) # type: ignore
    cursor = sqlite3_conn.cursor() 
    cursor.execute("""
        SELECT
            VACITM_0
        FROM
            ITMMASTER
        WHERE
            ITMREF_0 = ?
                   """, (item_code,))
    niveau = cursor.fetchone()[0]
    cursor.close()
    sqlite3_conn.close()
    return niveau

def get_legislation(regime_taxe_tiers: str) -> str:
    """Fetch legislation from the database."""
    # Simulated database fetch
    db_path = ""
    db_path = get_db_file()
    sqlite3_conn = sqlite3.connect(db_path) # type: ignore
    cursor = sqlite3_conn.cursor() 
    cursor.execute("""
        SELECT
            LEG_0
        FROM
            TABVACBPR
        WHERE
            VACBPR_0 = ?
                   """, (regime_taxe_tiers,))
    legislation = cursor.fetchone()[0]
    cursor.close()
    sqlite3_conn.close()
    return legislation

def get_applied_tax(criterias: List[AppliedTaxInput]) -> List[AppliedTaxResponse]:
    """Determine the applicable tax based on criteria."""
    from .components import DeterminationTaxe

    results = []

    db_path = ""
    db_path = get_db_file()
    sqlite3_conn = sqlite3.connect(db_path) # type: ignore
    cursor = sqlite3_conn.cursor()
    determinateur = DeterminationTaxe(cursor)
    for criteria in criterias:
        niveau_taxe_article = get_niveau_taxe_article(criteria.item_code)
        legislation = get_legislation(criteria.regime_taxe_tiers)
        code_taxe = determinateur.determiner_code_taxe({
            'regime_taxe_tiers':  criteria.regime_taxe_tiers,
            'niveau_taxe_article': niveau_taxe_article,
            'legislation': legislation,
            'groupe_societe': criteria.groupe_societe
        })
        if not code_taxe:
            raise Exception("Aucun code taxe trouvé pour ces critères")
        results.append(
            AppliedTaxResponse(
                item_code=criteria.item_code,
        code_taxe=code_taxe.get('code_taxe', ''),
        taux= code_taxe.get('taux', 0.0) if code_taxe.get('taux', 0.0) else 0.0, # type: ignore
    )
        )

    # details_taxe = determinateur._recuperer_details_taxe(code_taxe)
    cursor.close()
    sqlite3_conn.close()


    return results